import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal
from unittest.mock import patch, MagicMock
import stripe # For mocking

from events.models import Event, Venue, Category
from bookings.models import Booking
from payments.models import Payment
from core.models import Role

User = get_user_model()

@pytest.mark.django_db
class TestFullBookingFlow:

    @pytest.fixture
    def api_client(self):
        return APIClient()

    @pytest.fixture
    def roles(self):
        # Using get_or_create to avoid issues if roles already exist from other tests/migrations
        customer_role, _ = Role.objects.get_or_create(name=Role.CUSTOMER)
        organizer_role, _ = Role.objects.get_or_create(name=Role.EVENT_ORGANIZER)
        venue_manager_role, _ = Role.objects.get_or_create(name=Role.VENUE_MANAGER)
        admin_role, _ = Role.objects.get_or_create(name=Role.ADMIN)
        return {
            'customer': customer_role,
            'organizer': organizer_role,
            'manager': venue_manager_role,
            'admin': admin_role,
        }

    @pytest.fixture
    def regular_user(self, roles):
        user = User.objects.create_user(username='testcustomer', email='customer@flow.com', password='password123')
        user.roles.add(roles['customer'])
        return user

    @pytest.fixture
    def event_organizer(self, roles):
        user = User.objects.create_user(username='eventorganizer', email='organizer@flow.com', password='password123')
        user.roles.add(roles['organizer'])
        return user

    @pytest.fixture
    def venue_manager(self, roles): # Not used in this specific flow but good for setup
        user = User.objects.create_user(username='venuemanager', email='manager@flow.com', password='password123')
        user.roles.add(roles['manager'])
        return user

    @pytest.fixture
    def venue(self, venue_manager): # Let venue_manager own the venue
        return Venue.objects.create(name='Test Flow Venue', address='123 Flow St', capacity=100, owner=venue_manager)

    @pytest.fixture
    def category(self):
        return Category.objects.create(name='Integration Test Category')

    @pytest.fixture
    def paid_event(self, venue, event_organizer, category):
        event = Event.objects.create(
            name='Full Flow Paid Event',
            description='Event for testing full booking flow.',
            start_time='2028-12-01T10:00:00Z',
            end_time='2028-12-01T12:00:00Z',
            venue=venue,
            organizer=event_organizer,
            ticket_price=Decimal('50.00'),
            currency='USD',
            max_capacity=50
        )
        event.categories.add(category)
        return event

    @patch('core.email_utils.send_booking_related_email') # Mock email sending
    @patch('stripe.PaymentIntent') # Mock Stripe SDK
    def test_successful_paid_booking_flow(self, mock_stripe_payment_intent, mock_send_email, api_client, regular_user, paid_event):
        # 1. User Login (implicit via api_client.force_authenticate)
        api_client.force_authenticate(user=regular_user)

        # 2. Event and Venue creation is done by fixtures.

        # 3. User books the event
        booking_url = reverse('booking-list')
        booking_data = {
            'event': paid_event.pk,
            'number_of_tickets': 2
        }
        response = api_client.post(booking_url, booking_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        booking_id = response.data['id']
        booking = Booking.objects.get(pk=booking_id)
        assert booking.status == Booking.BookingStatus.PENDING_PAYMENT
        assert booking.user == regular_user
        assert booking.total_price == paid_event.ticket_price * 2
        assert booking.payment_intent_id is None # Should be None initially

        # Check that a Payment object was created
        payment_obj = Payment.objects.get(booking=booking)
        assert payment_obj.status == 'pending'
        assert payment_obj.amount == booking.total_price

        # Check that "booking pending" email was triggered
        # Email for booking PENDING_PAYMENT is sent from BookingViewSet.perform_create
        mock_send_email.assert_called_once()
        call_args_list = mock_send_email.call_args_list
        assert call_args_list[0][1]['booking'] == booking
        assert 'booking_pending_subject.txt' in call_args_list[0][1]['subject_template_name']
        mock_send_email.reset_mock() # Reset for next email check

        # 4. User initiates payment (simulating frontend call to CreatePaymentIntentView)
        create_pi_url = reverse('payments:create-payment-intent')

        # Mock Stripe PaymentIntent.create and .retrieve
        mock_intent_instance = MagicMock(spec=stripe.PaymentIntent)
        mock_intent_instance.id = 'pi_integration_test_123'
        mock_intent_instance.client_secret = 'pi_integration_test_123_secret'

        # Based on payments/views.py, CreatePaymentIntentView tries retrieve first if payment.stripe_payment_intent_id exists.
        # Since it's a new booking, it won't exist, so it will call create.
        mock_stripe_payment_intent.create.return_value = mock_intent_instance

        pi_data = {'booking_id': str(booking_id)}
        response = api_client.post(create_pi_url, pi_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['client_secret'] == 'pi_integration_test_123_secret'

        booking.refresh_from_db()
        payment_obj.refresh_from_db()
        assert booking.payment_intent_id == 'pi_integration_test_123'
        assert payment_obj.stripe_payment_intent_id == 'pi_integration_test_123'

        # 5. Simulate Stripe webhook for payment_intent.succeeded
        webhook_url = reverse('payments:stripe-webhook')

        # Prepare webhook payload
        webhook_payload = {
            'id': 'evt_test_webhook_success',
            'type': 'payment_intent.succeeded',
            'data': {
                'object': {
                    'id': 'pi_integration_test_123', # Must match the PI ID set on booking
                    'amount': int(booking.total_price * 100),
                    'currency': 'usd',
                    'metadata': { # payments/views.py uses this
                        'booking_id': str(booking_id),
                        'user_id': str(regular_user.id),
                        'payment_db_id': str(payment_obj.id)
                    }
                }
            }
        }

        # Mock stripe.Webhook.construct_event
        # The actual webhook view uses stripe.Webhook.construct_event directly.
        # So, we need to patch it where it's used in payments.views
        with patch('event_booking_platform_backend.payments.views.stripe.Webhook.construct_event') as mock_construct_event:
            mock_event_obj = MagicMock(spec=stripe.Event)
            mock_event_obj.type = 'payment_intent.succeeded'
            mock_event_obj.data = webhook_payload['data'] # Pass the data part of payload
            mock_construct_event.return_value = mock_event_obj

            # Make the webhook call (no auth needed for webhook)
            api_client.force_authenticate(user=None)
            response = api_client.post(webhook_url, webhook_payload, format='json', HTTP_STRIPE_SIGNATURE='wh_test_sig')
            assert response.status_code == status.HTTP_200_OK

        booking.refresh_from_db()
        payment_obj.refresh_from_db()
        assert booking.status == Booking.BookingStatus.CONFIRMED
        assert payment_obj.status == 'succeeded'

        # Verify confirmation email is triggered
        # This email is sent from StripeWebhookView.handle_payment_success
        mock_send_email.assert_called_once()
        call_args_list = mock_send_email.call_args_list
        assert call_args_list[0][1]['booking'] == booking
        assert 'booking_confirmation_subject.txt' in call_args_list[0][1]['subject_template_name']

    @patch('core.email_utils.send_booking_related_email') # Mock email sending
    @patch('stripe.PaymentIntent') # Mock Stripe SDK
    def test_failed_payment_flow(self, mock_stripe_payment_intent, mock_send_email, api_client, regular_user, paid_event):
        # 1. User Login & Booking (same as above, simplified)
        api_client.force_authenticate(user=regular_user)
        booking_url = reverse('booking-list')
        booking_data = {'event': paid_event.pk, 'number_of_tickets': 1}
        response = api_client.post(booking_url, booking_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        booking_id = response.data['id']
        booking = Booking.objects.get(pk=booking_id)
        payment_obj = Payment.objects.get(booking=booking)
        mock_send_email.reset_mock() # Reset from booking pending email

        # 2. User initiates payment (same as above, simplified)
        create_pi_url = reverse('payments:create-payment-intent')
        mock_intent_instance = MagicMock(spec=stripe.PaymentIntent)
        mock_intent_instance.id = 'pi_integration_failure_456'
        mock_intent_instance.client_secret = 'pi_integration_failure_456_secret'
        mock_stripe_payment_intent.create.return_value = mock_intent_instance
        pi_data = {'booking_id': str(booking_id)}
        response = api_client.post(create_pi_url, pi_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        booking.refresh_from_db()
        payment_obj.refresh_from_db()
        assert booking.payment_intent_id == 'pi_integration_failure_456'
        assert payment_obj.stripe_payment_intent_id == 'pi_integration_failure_456'

        # 3. Simulate Stripe webhook for payment_intent.payment_failed
        webhook_url = reverse('payments:stripe-webhook')
        webhook_payload_failed = {
            'id': 'evt_test_webhook_fail',
            'type': 'payment_intent.payment_failed',
            'data': {
                'object': {
                    'id': 'pi_integration_failure_456',
                    'amount': int(booking.total_price * 100),
                    'currency': 'usd',
                    'metadata': {
                        'booking_id': str(booking_id),
                        'user_id': str(regular_user.id),
                        'payment_db_id': str(payment_obj.id)
                    },
                    'last_payment_error': {'message': 'Your card was declined.'}
                }
            }
        }

        with patch('event_booking_platform_backend.payments.views.stripe.Webhook.construct_event') as mock_construct_event:
            mock_event_obj_failed = MagicMock(spec=stripe.Event)
            mock_event_obj_failed.type = 'payment_intent.payment_failed'
            mock_event_obj_failed.data = webhook_payload_failed['data']
            mock_construct_event.return_value = mock_event_obj_failed

            api_client.force_authenticate(user=None)
            response = api_client.post(webhook_url, webhook_payload_failed, format='json', HTTP_STRIPE_SIGNATURE='wh_test_sig_fail')
            assert response.status_code == status.HTTP_200_OK

        booking.refresh_from_db()
        payment_obj.refresh_from_db()

        # Verify Booking status remains PENDING_PAYMENT or could be FAILED depending on exact requirements.
        # The current StripeWebhookView.handle_payment_failure does NOT change booking status.
        # It updates Payment status to 'failed'.
        assert booking.status == Booking.BookingStatus.PENDING_PAYMENT
        assert payment_obj.status == 'failed'

        # Verify failure email is triggered
        mock_send_email.assert_called_once()
        call_args_list = mock_send_email.call_args_list
        assert call_args_list[0][1]['booking'] == booking
        assert 'payment_failed_subject.txt' in call_args_list[0][1]['subject_template_name']

# Pytest will discover this file and class if named correctly (test_*.py or *_test.py)
# and placed in a discoverable location.
# The `tests` directory at the root of the Django app `event_booking_platform_backend`
# might need to be a Python package (with __init__.py) and configured in pytest settings if not default.
# For simplicity, placing it inside an app like `event_booking_platform_backend/core/tests/integration/test_full_booking_flow.py`
# might be easier for discovery if `core.tests` is already a known test location.
# I will assume `event_booking_platform_backend/tests/integration/` is discoverable.
# Adding __init__.py to `event_booking_platform_backend/tests/` and `event_booking_platform_backend/tests/integration/`
# might be necessary.
# (This file is created at `event_booking_platform_backend/tests/integration/test_full_booking_flow.py`)
# An __init__.py in event_booking_platform_backend/tests/ and event_booking_platform_backend/tests/integration/ would be good practice.

# Note for Stripe Webhook testing:
# The actual stripe.Webhook.construct_event takes (payload_body, sig_header, secret).
# The mock `patch('event_booking_platform_backend.payments.views.stripe.Webhook.construct_event')`
# bypasses the actual signature verification, which is usually fine for testing the handler logic.
# If signature verification itself needs testing, it's more complex and might involve Stripe's CLI or test webhook signing secrets.
# The provided code correctly mocks at the `construct_event` level.
# The `HTTP_STRIPE_SIGNATURE` header is passed but its value doesn't matter when `construct_event` is mocked.
# If `settings.STRIPE_WEBHOOK_SECRET` is not set, the view should error out earlier; this can be another test case.
# (Current webhook view checks for this secret).

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
        # This setup ensures that the roles required for the test are available.
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
        # User Registration part of the setup
        user = User.objects.create_user(username='testcustomer', email='customer@flow.com', password='password123')
        user.roles.add(roles['customer'])
        return user

    @pytest.fixture
    def event_organizer(self, roles):
        # User with event organizer role
        user = User.objects.create_user(username='eventorganizer', email='organizer@flow.com', password='password123')
        user.roles.add(roles['organizer'])
        return user

    @pytest.fixture
    def venue_manager(self, roles):
        # User with venue manager role
        user = User.objects.create_user(username='venuemanager', email='manager@flow.com', password='password123')
        user.roles.add(roles['manager'])
        return user

    @pytest.fixture
    def venue(self, venue_manager, event_organizer): # Ensure event_organizer can also be an owner if needed, or a separate admin
        # Venue Creation by appropriate role (venue_manager or could be admin/organizer based on rules)
        # For this test, venue_manager owns the venue.
        return Venue.objects.create(
            name='Test Flow Venue',
            address='123 Flow St',
            capacity=100,
            owner=venue_manager # Managed by venue_manager
        )

    @pytest.fixture
    def category(self):
        return Category.objects.create(name='Integration Test Category')

    @pytest.fixture
    def paid_event(self, venue, event_organizer, category):
        # Event Creation by appropriate role (event_organizer)
        event = Event.objects.create(
            name='Full Flow Paid Event',
            description='Event for testing full booking flow.',
            start_time='2028-12-01T10:00:00Z', # Ensure future date for active booking
            end_time='2028-12-01T12:00:00Z',
            venue=venue,
            organizer=event_organizer, # Managed by event_organizer
            ticket_price=Decimal('50.00'),
            currency='USD',
            max_capacity=50,
            status=Event.EventStatus.UPCOMING # Ensure event is bookable
        )
        event.categories.add(category)
        return event

    @patch('core.email_utils.send_booking_related_email') # Mock email sending utility
    @patch('stripe.PaymentIntent') # Mock Stripe SDK's PaymentIntent class
    def test_successful_paid_booking_flow(self, mock_stripe_payment_intent_class, mock_send_email, api_client, regular_user, paid_event):
        # 1. User Login (achieved by force_authenticate)
        # For a stricter test of login endpoint, separate API calls would be needed here.
        # However, for focusing on booking flow, force_authenticate is efficient.
        api_client.force_authenticate(user=regular_user)

        # 2. Event and Venue creation is handled by fixtures, ensuring roles are used.

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

        assert booking.user == regular_user
        assert booking.number_of_tickets == 2
        # Verify price_per_ticket_at_booking and total_price
        assert booking.price_per_ticket_at_booking == paid_event.ticket_price
        assert booking.total_price == paid_event.ticket_price * booking.number_of_tickets
        # Verify booking status is initially PENDING_PAYMENT
        assert booking.status == Booking.BookingStatus.PENDING_PAYMENT
        assert booking.payment_intent_id is None # Should be None until payment intent is created

        # Check that a Payment object was created associated with the booking
        payment_obj = Payment.objects.get(booking=booking)
        assert payment_obj.status == Payment.PaymentStatus.PENDING
        assert payment_obj.amount == booking.total_price
        assert payment_obj.currency.upper() == paid_event.currency.upper()

        # Verify "booking pending" email was triggered (sent from BookingViewSet.perform_create)
        mock_send_email.assert_called_once()
        (call_args, call_kwargs) = mock_send_email.call_args_list[0]
        assert call_kwargs['booking'] == booking
        assert 'booking_pending_subject.txt' in call_kwargs['subject_template_name']
        mock_send_email.reset_mock() # Reset for the next email check

        # 4. Mocked Payment Intent creation
        create_pi_url = reverse('payments:create-payment-intent')

        # Setup mock for Stripe PaymentIntent.create() and .retrieve()
        # .create() is called when no existing PI ID on payment or retrieve fails
        # .retrieve() is called if payment.stripe_payment_intent_id exists.
        mock_intent_instance = MagicMock(spec=stripe.PaymentIntent)
        mock_intent_instance.id = 'pi_integration_success_123'
        mock_intent_instance.client_secret = 'pi_integration_success_123_secret'
        mock_intent_instance.status = 'requires_payment_method' # Typical status after creation

        # Based on payments/views.py, CreatePaymentIntentView might try retrieve first if payment.stripe_payment_intent_id was set by a previous flaky attempt.
        # For a clean booking, it will call create.
        mock_stripe_payment_intent_class.create.return_value = mock_intent_instance
        mock_stripe_payment_intent_class.retrieve.return_value = mock_intent_instance # If retrieve was ever called

        pi_data = {'booking_id': str(booking_id)}
        response = api_client.post(create_pi_url, pi_data, format='json')

        assert response.status_code == status.HTTP_201_CREATED # 201 for new PI
        # Verify the response includes a client_secret
        assert response.data['client_secret'] == 'pi_integration_success_123_secret'
        assert response.data['payment_id'] == payment_obj.id


        booking.refresh_from_db()
        payment_obj.refresh_from_db()
        assert booking.payment_intent_id == 'pi_integration_success_123'
        # Verify the associated Payment object is updated with PI ID and status remains PENDING (or as per Stripe's initial response)
        assert payment_obj.stripe_payment_intent_id == 'pi_integration_success_123'
        assert payment_obj.status == Payment.PaymentStatus.PENDING # Status updated by PI creation logic

        # 5. Mocked Stripe Webhook for payment_intent.succeeded
        webhook_url = reverse('payments:stripe-webhook')
        webhook_payload_success = {
            'id': 'evt_test_webhook_success',
            'type': 'payment_intent.succeeded',
            'data': {
                'object': { # This is a mock Stripe PaymentIntent object
                    'id': 'pi_integration_success_123', # Must match the PI ID
                    'amount': int(booking.total_price * 100), # Stripe works in cents
                    'currency': paid_event.currency.lower(),
                    'metadata': { # Metadata as set during PI creation
                        'booking_id': str(booking_id),
                        'user_id': str(regular_user.id),
                        'payment_db_id': str(payment_obj.id)
                    },
                    'status': 'succeeded'
                }
            }
        }

        # Patch stripe.Webhook.construct_event within the context of payments.views
        with patch('event_booking_platform_backend.payments.views.stripe.Webhook.construct_event') as mock_construct_event:
            mock_stripe_event_obj = MagicMock(spec=stripe.Event)
            mock_stripe_event_obj.type = webhook_payload_success['type']
            mock_stripe_event_obj.data = webhook_payload_success['data']
            mock_construct_event.return_value = mock_stripe_event_obj

            # Webhook calls are unauthenticated
            api_client.force_authenticate(user=None)
            response = api_client.post(webhook_url, webhook_payload_success, format='json', HTTP_STRIPE_SIGNATURE='wh_test_success_sig')
            assert response.status_code == status.HTTP_200_OK

        booking.refresh_from_db()
        payment_obj.refresh_from_db()
        # Verify Booking status changes to CONFIRMED
        assert booking.status == Booking.BookingStatus.CONFIRMED
        # Verify Payment status changes to SUCCEEDED
        assert payment_obj.status == Payment.PaymentStatus.SUCCEEDED

        # Verify booking confirmation email was queued/sent
        # This email is sent from StripeWebhookView.handle_payment_success
        mock_send_email.assert_called_once()
        (call_args, call_kwargs) = mock_send_email.call_args_list[0]
        assert call_kwargs['booking'] == booking
        assert call_kwargs['payment'] == payment_obj
        assert 'booking_confirmation_subject.txt' in call_kwargs['subject_template_name']
        assert 'booking_confirmation_body.html' in call_kwargs['body_html_template_name']
        assert 'booking_confirmation_body.txt' in call_kwargs['body_text_template_name']

    @patch('core.email_utils.send_booking_related_email')
    @patch('stripe.PaymentIntent')
    def test_failed_payment_flow(self, mock_stripe_payment_intent_class, mock_send_email, api_client, regular_user, paid_event):
        # 1. User Login & Initial Booking
        api_client.force_authenticate(user=regular_user)
        booking_url = reverse('booking-list')
        booking_data = {'event': paid_event.pk, 'number_of_tickets': 1}
        response = api_client.post(booking_url, booking_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        booking_id = response.data['id']
        booking = Booking.objects.get(pk=booking_id)
        payment_obj = Payment.objects.get(booking=booking)

        # Reset email mock called for booking pending
        mock_send_email.reset_mock()

        # 2. Create Payment Intent
        create_pi_url = reverse('payments:create-payment-intent')
        mock_intent_instance_fail = MagicMock(spec=stripe.PaymentIntent)
        mock_intent_instance_fail.id = 'pi_integration_failure_456'
        mock_intent_instance_fail.client_secret = 'pi_integration_failure_456_secret'
        mock_stripe_payment_intent_class.create.return_value = mock_intent_instance_fail
        mock_stripe_payment_intent_class.retrieve.return_value = mock_intent_instance_fail


        pi_data = {'booking_id': str(booking_id)}
        api_client.post(create_pi_url, pi_data, format='json') # Response checked in success test
        booking.refresh_from_db()
        payment_obj.refresh_from_db()
        assert booking.payment_intent_id == 'pi_integration_failure_456'
        assert payment_obj.stripe_payment_intent_id == 'pi_integration_failure_456'


        # 3. Mocked Stripe Webhook for payment_intent.payment_failed
        webhook_url = reverse('payments:stripe-webhook')
        webhook_payload_failed = {
            'id': 'evt_test_webhook_fail',
            'type': 'payment_intent.payment_failed',
            'data': {
                'object': { # Mock Stripe PaymentIntent object for failure
                    'id': 'pi_integration_failure_456', # Must match PI ID
                    'amount': int(booking.total_price * 100),
                    'currency': paid_event.currency.lower(),
                    'metadata': {
                        'booking_id': str(booking_id),
                        'user_id': str(regular_user.id),
                        'payment_db_id': str(payment_obj.id)
                    },
                    'status': 'failed', # Or 'requires_payment_method' with a last_payment_error
                    'last_payment_error': {
                        'message': 'Your card was declined.'
                    }
                }
            }
        }

        with patch('event_booking_platform_backend.payments.views.stripe.Webhook.construct_event') as mock_construct_event_fail:
            mock_stripe_event_obj_failed = MagicMock(spec=stripe.Event)
            mock_stripe_event_obj_failed.type = webhook_payload_failed['type']
            mock_stripe_event_obj_failed.data = webhook_payload_failed['data']
            mock_construct_event_fail.return_value = mock_stripe_event_obj_failed

            api_client.force_authenticate(user=None)
            response = api_client.post(webhook_url, webhook_payload_failed, format='json', HTTP_STRIPE_SIGNATURE='wh_test_fail_sig')
            assert response.status_code == status.HTTP_200_OK

        booking.refresh_from_db()
        payment_obj.refresh_from_db()

        # Verify Booking status (e.g., PENDING_PAYMENT or FAILED based on current business logic)
        # Current logic in StripeWebhookView.handle_payment_failure does NOT change booking status.
        assert booking.status == Booking.BookingStatus.PENDING_PAYMENT
        # Verify Payment status changes to FAILED
        assert payment_obj.status == Payment.PaymentStatus.FAILED

        # Verify payment failure email was queued/sent
        mock_send_email.assert_called_once()
        (call_args, call_kwargs) = mock_send_email.call_args_list[0]
        assert call_kwargs['booking'] == booking
        assert call_kwargs['payment'] == payment_obj
        assert 'payment_failed_subject.txt' in call_kwargs['subject_template_name']
        assert 'payment_failed_body.html' in call_kwargs['body_html_template_name']
        assert 'payment_failed_body.txt' in call_kwargs['body_text_template_name']

# To ensure pytest discovery, ensure:
# 1. Filename is `test_*.py` or `*_test.py`.
# 2. The `tests` directory and `tests/integration` directory have `__init__.py`.
# 3. Pytest is configured to look into this directory (usually default if part of an app).
# This class TestFullBookingFlow and its methods are already correctly named.
# (This file is located at `event_booking_platform_backend/tests/integration/test_full_booking_flow.py`)
# (The __init__.py files will be added in separate steps if they don't exist)

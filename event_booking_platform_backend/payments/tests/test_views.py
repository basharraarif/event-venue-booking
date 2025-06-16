import json
import stripe # Import stripe directly for mocking its objects
from unittest.mock import patch, MagicMock # For mocking Stripe API calls and email sending
from decimal import Decimal

from django.urls import reverse
from django.contrib.auth import get_user_model
from django.conf import settings # To access STRIPE_WEBHOOK_SECRET for test signature

from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from events.models import Event, Category # Venue removed
from venues.models import Venue # Venue added
from bookings.models import Booking
from payments.models import Payment

User = get_user_model()

class PaymentViewTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='testuser', email='test@example.com', password='password123')
        cls.venue = Venue.objects.create(name='Test Venue', address='123 Test St', capacity=100, owner=cls.user)
        cls.category = Category.objects.create(name='Test Category')

        cls.paid_event = Event.objects.create(
            name='Paid Test Event',
            description='A test event that costs money.',
            start_time='2024-12-01T10:00:00Z',
            end_time='2024-12-01T12:00:00Z',
            venue=cls.venue,
            organizer=cls.user,
            ticket_price=Decimal('100.00'),
            currency='USD'
        )
        cls.free_event = Event.objects.create(
            name='Free Test Event',
            description='A test event that is free.',
            start_time='2024-12-02T10:00:00Z',
            end_time='2024-12-02T12:00:00Z',
            venue=cls.venue,
            organizer=cls.user,
            ticket_price=Decimal('0.00'),
            currency='USD'
        )

        # Booking for a paid event, payment pending
        cls.paid_booking = Booking.objects.create(
            event=cls.paid_event, user=cls.user, number_of_tickets=1
        )
        # Logic from BookingViewSet.perform_create to set initial status
        cls.paid_booking.total_price = cls.paid_event.ticket_price * cls.paid_booking.number_of_tickets
        # cls.paid_booking.payment_status = 'pending' # Field removed
        cls.paid_booking.status = Booking.BookingStatus.PENDING_PAYMENT
        cls.paid_booking.save()
        cls.payment_for_paid_booking = Payment.objects.create(
            booking=cls.paid_booking,
            amount=cls.paid_booking.total_price,
            currency=cls.paid_event.currency,
            status='pending'
        )

        # Booking for a free event
        cls.free_booking = Booking.objects.create(
            event=cls.free_event, user=cls.user, number_of_tickets=1
        )
        cls.free_booking.total_price = cls.free_event.ticket_price * cls.free_booking.number_of_tickets
        # cls.free_booking.payment_status = 'not_required' # Field removed
        cls.free_booking.status = Booking.BookingStatus.CONFIRMED
        cls.free_booking.save()

        # Booking that is already paid
        cls.already_paid_booking = Booking.objects.create(
            event=cls.paid_event, user=cls.user, number_of_tickets=1
        )
        cls.already_paid_booking.total_price = cls.paid_event.ticket_price * cls.already_paid_booking.number_of_tickets
        # cls.already_paid_booking.payment_status = 'paid' # Field removed
        cls.already_paid_booking.status = Booking.BookingStatus.CONFIRMED
        # Set payment_intent_id for already paid booking for consistency if webhook logic were to re-verify
        cls.already_paid_booking.payment_intent_id = 'pi_already_paid_test'
        cls.already_paid_booking.save()
        Payment.objects.create(
            booking=cls.already_paid_booking,
            amount=cls.already_paid_booking.total_price,
            currency=cls.paid_event.currency,
            status='succeeded',
            stripe_payment_intent_id='pi_already_paid_test'
        )

        cls.client = APIClient()
        cls.create_payment_intent_url = reverse('payments:create-payment-intent')
        cls.stripe_webhook_url = reverse('payments:stripe-webhook')

    def setUp(self):
        # Authenticate client for tests that require it
        self.client.force_authenticate(user=self.user)

    # --- CreatePaymentIntentView Tests ---

    @patch('stripe.PaymentIntent.create')
    def test_create_payment_intent_success(self, mock_stripe_pi_create):
        # Mock Stripe's PaymentIntent.create response
        mock_intent_response = MagicMock(spec=stripe.PaymentIntent)
        mock_intent_response.id = 'pi_test_success123'
        mock_intent_response.client_secret = 'pi_test_success123_secret_test'
        mock_stripe_pi_create.return_value = mock_intent_response

        data = {'booking_id': str(self.paid_booking.id)}
        response = self.client.post(self.create_payment_intent_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('client_secret', response.data)
        self.assertEqual(response.data['client_secret'], mock_intent_response.client_secret)
        self.assertIn('payment_id', response.data)

        # Verify Payment object was updated
        payment = Payment.objects.get(booking=self.paid_booking)
        self.assertEqual(payment.stripe_payment_intent_id, mock_intent_response.id)
        self.assertEqual(payment.status, 'pending') # Should remain pending until webhook confirmation

        # Verify booking payment_intent_id is updated
        self.paid_booking.refresh_from_db()
        self.assertEqual(self.paid_booking.payment_intent_id, mock_intent_response.id)
        # Verify booking.status remains PENDING_PAYMENT (or as per logic)
        self.assertEqual(self.paid_booking.status, Booking.BookingStatus.PENDING_PAYMENT)


        mock_stripe_pi_create.assert_called_once()
        called_args, called_kwargs = mock_stripe_pi_create.call_args
        self.assertEqual(called_kwargs['amount'], int(self.paid_booking.total_price * 100))
        self.assertEqual(called_kwargs['currency'], self.paid_event.currency.lower())
        self.assertEqual(called_kwargs['metadata']['booking_id'], str(self.paid_booking.id))
        self.assertEqual(called_kwargs['metadata']['payment_db_id'], str(payment.id))


    def test_create_payment_intent_booking_not_found(self):
        invalid_uuid = '00000000-0000-0000-0000-000000000000'
        data = {'booking_id': invalid_uuid}
        response = self.client.post(self.create_payment_intent_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST) # Serializer validation
        self.assertIn('booking_id', response.data)

    def test_create_payment_intent_for_free_booking(self):
        data = {'booking_id': str(self.free_booking.id)}
        response = self.client.post(self.create_payment_intent_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # The serializer's validate_booking_id should catch this
        self.assertIn("Booking does not require payment", response.data['booking_id'][0])


    def test_create_payment_intent_for_already_paid_booking(self):
        # This test logic might need adjustment based on how "already paid" is determined now.
        # If it's based on Booking.status == CONFIRMED and an existing Payment.status == 'succeeded'
        # for that booking's payment_intent_id (or related payment), the behavior might differ.
        # The existing CreatePaymentIntentView checks payment.status == 'succeeded'.
        data = {'booking_id': str(self.already_paid_booking.id)}
        response = self.client.post(self.create_payment_intent_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # The error message comes from the view logic now, not serializer if payment_status is not a direct field
        self.assertIn('This booking has already been paid.', response.data['error'])


    @patch('stripe.PaymentIntent.create', side_effect=stripe.error.StripeError("Stripe API Error"))
    def test_create_payment_intent_stripe_api_error(self, mock_stripe_pi_create_error):
        data = {'booking_id': str(self.paid_booking.id)}
        response = self.client.post(self.create_payment_intent_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn('error', response.data)
        self.assertIn("Stripe API Error", response.data['error'])

        payment = Payment.objects.get(booking=self.paid_booking)
        self.assertEqual(payment.status, 'failed') # Should be marked failed
        # self.paid_booking.refresh_from_db() # No direct 'payment_status' field on booking
        # self.assertEqual(self.paid_booking.payment_status, 'failed') # Field removed


    @patch('stripe.PaymentIntent.retrieve')
    @patch('stripe.PaymentIntent.create')
    def test_create_payment_intent_existing_pending_intent(self, mock_stripe_pi_create, mock_stripe_pi_retrieve):
        # Setup: booking has a payment with a stripe_payment_intent_id already
        existing_pi_id = 'pi_existing_test123'
        existing_client_secret = 'pi_existing_test123_secret_test'
        self.payment_for_paid_booking.stripe_payment_intent_id = existing_pi_id
        self.payment_for_paid_booking.status = 'pending' # Ensure it's pending
        self.payment_for_paid_booking.save()

        mock_retrieved_intent = MagicMock(spec=stripe.PaymentIntent)
        mock_retrieved_intent.id = existing_pi_id
        mock_retrieved_intent.client_secret = existing_client_secret
        mock_stripe_pi_retrieve.return_value = mock_retrieved_intent

        data = {'booking_id': str(self.paid_booking.id)}
        response = self.client.post(self.create_payment_intent_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['client_secret'], existing_client_secret)
        self.assertEqual(response.data['payment_id'], str(self.payment_for_paid_booking.id))

        mock_stripe_pi_retrieve.assert_called_once_with(existing_pi_id)
        mock_stripe_pi_create.assert_not_called() # Should not create a new one


    # --- StripeWebhookView Tests ---

    def _generate_stripe_signature(self, payload_body, secret):
        # This is a simplified version. Real signature generation is more complex.
        # For robust testing, you'd use Stripe's provided libraries or examples.
        # stripe-python's stripe.Webhook.construct_event itself handles verification
        # if the secret is correct. We need to pass a signature that *would* be valid.
        # The actual value of the signature doesn't matter as much as stripe.Webhook.construct_event
        # being able to verify it using the provided secret.
        # For testing the view's handling of construct_event's success/failure,
        # we can mock construct_event directly.
        # However, if we want to test the signature check more end-to-end, we would
        # use stripe.webhook.WebhookSignature.sign(...) if available, or a fixed example.
        # For now, we'll rely on mocking stripe.Webhook.construct_event for different scenarios.
        return "dummy_signature_for_testing_construct_event_mocking"


    @patch('stripe.Webhook.construct_event')
    @patch('event_booking_platform_backend.payments.views.send_booking_related_email')
    def test_stripe_webhook_payment_intent_succeeded(self, mock_send_email, mock_construct_event):
        # Prepare a mock Stripe Event object for payment_intent.succeeded
        mock_event_data_object = {
            'id': 'pi_test_webhook_succeeded',
            'amount': int(self.paid_booking.total_price * 100),
            'currency': self.paid_event.currency.lower(),
            'metadata': {
                'booking_id': str(self.paid_booking.id),
                'user_id': str(self.user.id),
                'payment_db_id': str(self.payment_for_paid_booking.id)
            }
        }
        mock_stripe_event = MagicMock(spec=stripe.Event)
        mock_stripe_event.type = 'payment_intent.succeeded'
        mock_stripe_event.data = MagicMock()
        mock_stripe_event.data.object = mock_event_data_object
        mock_construct_event.return_value = mock_stripe_event

        # Ensure the payment initially has the PI ID and is pending
        # AND the booking has the payment_intent_id for the new webhook logic
        stripe_pi_id_for_test = 'pi_test_webhook_succeeded'
        self.paid_booking.payment_intent_id = stripe_pi_id_for_test
        self.paid_booking.status = Booking.BookingStatus.PENDING_PAYMENT # Ensure it's pending
        self.paid_booking.save()

        self.payment_for_paid_booking.stripe_payment_intent_id = stripe_pi_id_for_test
        self.payment_for_paid_booking.status = 'pending'
        self.payment_for_paid_booking.save()
        # self.paid_booking.payment_status = 'pending' # Field removed
        # self.paid_booking.save() # Already saved above

        payload = json.dumps({'type': 'payment_intent.succeeded', 'data': {'object': mock_event_data_object}})
        headers = {'HTTP_STRIPE_SIGNATURE': 'wh_sig_test'} # Signature verification is mocked by construct_event

        # Unauthenticate client for webhook (webhooks are public)
        self.client.force_authenticate(user=None)
        response = self.client.post(self.stripe_webhook_url, data=payload, content_type='application/json', **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_construct_event.assert_called_once() # Check it was called

        self.payment_for_paid_booking.refresh_from_db()
        self.assertEqual(self.payment_for_paid_booking.status, 'succeeded')

        self.paid_booking.refresh_from_db()
        # self.assertEqual(self.paid_booking.payment_status, 'paid') # Field removed
        self.assertEqual(self.paid_booking.status, Booking.BookingStatus.CONFIRMED)
        # Ensure booking.payment_intent_id is still correctly set (or was set if webhook had to fix it)
        self.assertEqual(self.paid_booking.payment_intent_id, stripe_pi_id_for_test)


        mock_send_email.assert_called_once()
        # Example check for email arguments (very basic)
        self.assertEqual(mock_send_email.call_args[1]['booking'], self.paid_booking)
        self.assertIn('payment_confirmation', mock_send_email.call_args[1]['subject_template_name'])


    @patch('stripe.Webhook.construct_event')
    @patch('event_booking_platform_backend.payments.views.send_booking_related_email')
    def test_stripe_webhook_payment_intent_failed(self, mock_send_email, mock_construct_event):
        mock_event_data_object = {
            'id': 'pi_test_webhook_failed',
            'amount': int(self.paid_booking.total_price * 100),
            'currency': self.paid_event.currency.lower(),
            'metadata': {
                'booking_id': str(self.paid_booking.id),
                'user_id': str(self.user.id),
                'payment_db_id': str(self.payment_for_paid_booking.id)
            },
            'last_payment_error': {'message': 'Card declined.'}
        }
        mock_stripe_event = MagicMock(spec=stripe.Event)
        mock_stripe_event.type = 'payment_intent.payment_failed'
        mock_stripe_event.data = MagicMock()
        mock_stripe_event.data.object = mock_event_data_object
        mock_construct_event.return_value = mock_stripe_event

        stripe_pi_id_for_test = 'pi_test_webhook_failed'
        self.paid_booking.payment_intent_id = stripe_pi_id_for_test
        self.paid_booking.status = Booking.BookingStatus.PENDING_PAYMENT # Ensure it's pending
        self.paid_booking.save()

        self.payment_for_paid_booking.stripe_payment_intent_id = stripe_pi_id_for_test
        self.payment_for_paid_booking.status = 'pending'
        self.payment_for_paid_booking.save()
        # self.paid_booking.payment_status = 'pending' # Field removed
        # self.paid_booking.save() # Already saved

        payload = json.dumps({'type': 'payment_intent.payment_failed', 'data': {'object': mock_event_data_object}})
        headers = {'HTTP_STRIPE_SIGNATURE': 'wh_sig_test_fail'}

        self.client.force_authenticate(user=None)
        response = self.client.post(self.stripe_webhook_url, data=payload, content_type='application/json', **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.payment_for_paid_booking.refresh_from_db()
        self.assertEqual(self.payment_for_paid_booking.status, 'failed')

        self.paid_booking.refresh_from_db()
        # self.assertEqual(self.paid_booking.payment_status, 'failed') # Field removed
        # Booking status should remain PENDING_PAYMENT as per current webhook logic for failure
        self.assertEqual(self.paid_booking.status, Booking.BookingStatus.PENDING_PAYMENT)
        self.assertEqual(self.paid_booking.payment_intent_id, stripe_pi_id_for_test)

        mock_send_email.assert_called_once()
        self.assertEqual(mock_send_email.call_args[1]['booking'], self.paid_booking)
        self.assertIn('payment_failed', mock_send_email.call_args[1]['subject_template_name'])

    @patch('stripe.Webhook.construct_event', side_effect=stripe.error.SignatureVerificationError("Invalid signature", "sig_header"))
    def test_stripe_webhook_invalid_signature(self, mock_construct_event_sig_error):
        payload = json.dumps({'type': 'payment_intent.succeeded', 'data': {}})
        headers = {'HTTP_STRIPE_SIGNATURE': 'invalid_signature_value'}

        self.client.force_authenticate(user=None)
        response = self.client.post(self.stripe_webhook_url, data=payload, content_type='application/json', **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Invalid signature', response.data['error'])

    @patch('stripe.Webhook.construct_event', side_effect=ValueError("Invalid payload"))
    def test_stripe_webhook_invalid_payload(self, mock_construct_event_val_error):
        payload = "this is not valid json"
        headers = {'HTTP_STRIPE_SIGNATURE': 'wh_sig_test_invalid_payload'}

        self.client.force_authenticate(user=None)
        response = self.client.post(self.stripe_webhook_url, data=payload, content_type='application/json', **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Invalid payload', response.data['error'])

    # More tests to consider:
    # - Webhook: Payment object not found by PI ID or metadata ID.
    # - Webhook: Unhandled event type.
    # - CreatePaymentIntentView: User not authenticated.
    # - CreatePaymentIntentView: Booking belongs to another user.
    # - CreatePaymentIntentView: Test logic for updating existing PI if amount changes (more complex).
    # - Test email sending failure handling (e.g., logs error but main process succeeds).
    # - Test what happens if STRIPE_WEBHOOK_SECRET is not set (should return 500).

    def test_create_payment_intent_unauthenticated(self):
        self.client.force_authenticate(user=None) # Unauthenticate
        data = {'booking_id': str(self.paid_booking.id)}
        response = self.client.post(self.create_payment_intent_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_payment_intent_booking_other_user(self):
        other_user = User.objects.create_user(username='otheruser', email='other@example.com', password='password123')
        # Authenticate as self.user
        self.client.force_authenticate(user=self.user)

        # Create a booking for other_user
        other_booking = Booking.objects.create(
            event=self.paid_event, user=other_user, number_of_tickets=1
        )
        other_booking.total_price = self.paid_event.ticket_price * other_booking.number_of_tickets
        # other_booking.payment_status = 'pending' # Field removed
        other_booking.status = Booking.BookingStatus.PENDING_PAYMENT
        other_booking.save()
        Payment.objects.create(
            booking=other_booking,
            amount=other_booking.total_price,
            currency=self.paid_event.currency,
            status='pending'
        )

        data = {'booking_id': str(other_booking.id)}
        response = self.client.post(self.create_payment_intent_url, data, format='json')
        # The view's query `Booking.objects.get(id=booking_id, user=user)` should prevent this
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        # Serializer would pass, but view logic catches it.
        self.assertIn("Booking not found or you do not have permission", response.data['error'])

    @patch('stripe.Webhook.construct_event')
    def test_stripe_webhook_booking_not_found_by_pi_id(self, mock_construct_event):
        # Simulate a webhook event for a PI that doesn't match any Booking.payment_intent_id
        non_existent_stripe_pi_id = "pi_this_booking_pi_id_does_not_exist"

        mock_event_data_object = {
            'id': non_existent_stripe_pi_id, # This PI ID is not on any Booking
            'amount': 1000, # Some amount
            'currency': 'usd',
            'metadata': { # Metadata might be there but Booking lookup by PI ID is primary
                'booking_id': str(self.paid_booking.id),
                'user_id': str(self.user.id),
                'payment_db_id': str(self.payment_for_paid_booking.id)
            }
        }
        mock_stripe_event = MagicMock(spec=stripe.Event)
        mock_stripe_event.type = 'payment_intent.succeeded'
        mock_stripe_event.data = MagicMock()
        mock_stripe_event.data.object = mock_event_data_object
        mock_construct_event.return_value = mock_stripe_event

        payload = json.dumps({'type': 'payment_intent.succeeded', 'data': {'object': mock_event_data_object}})
        headers = {'HTTP_STRIPE_SIGNATURE': 'wh_sig_test_payment_not_found'}

        self.client.force_authenticate(user=None)
        response = self.client.post(self.stripe_webhook_url, data=payload, content_type='application/json', **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK) # Webhook itself is ack'd
        # Check logs for "Booking not found for Stripe PaymentIntent ID..."
        # No email should be sent, no booking status changed for self.paid_booking
        original_booking_status = self.paid_booking.status
        original_payment_status = self.payment_for_paid_booking.status
        self.paid_booking.refresh_from_db()
        self.payment_for_paid_booking.refresh_from_db()
        self.assertEqual(self.paid_booking.status, original_booking_status)
        self.assertEqual(self.payment_for_paid_booking.status, original_payment_status)


    @patch('stripe.Webhook.construct_event')
    def test_stripe_webhook_unhandled_event_type(self, mock_construct_event):
        mock_stripe_event = MagicMock(spec=stripe.Event)
        mock_stripe_event.type = 'customer.subscription.created' # An unhandled type
        mock_stripe_event.data = MagicMock()
        mock_stripe_event.data.object = {} # Empty object for simplicity
        mock_construct_event.return_value = mock_stripe_event

        payload = json.dumps({'type': 'customer.subscription.created', 'data': {}})
        headers = {'HTTP_STRIPE_SIGNATURE': 'wh_sig_test_unhandled'}

        self.client.force_authenticate(user=None)
        response = self.client.post(self.stripe_webhook_url, data=payload, content_type='application/json', **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check logs for "Received unhandled Stripe event type"
        # No state change should occur for payment/booking.
        original_booking_status = self.paid_booking.status
        original_payment_status = self.payment_for_paid_booking.status
        self.paid_booking.refresh_from_db()
        self.payment_for_paid_booking.refresh_from_db()
        self.assertEqual(self.paid_booking.status, original_booking_status)
        self.assertEqual(self.payment_for_paid_booking.status, original_payment_status)

# To run these tests:
# python manage.py test payments.tests.test_views
# or if this file is named test_views.py inside payments/tests/
# python manage.py test payments

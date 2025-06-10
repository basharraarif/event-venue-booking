from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.conf import settings
from decimal import Decimal
from unittest.mock import patch, MagicMock
import uuid

from bookings.models import Booking, Event
from venues.models import Venue
from .models import Payment
from .serializers import PaymentIntentResponseSerializer

User = get_user_model()

class PaymentModelTests(TestCase): # Keep existing model tests

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', email='test@example.com', password='password123')
        self.venue = Venue.objects.create(name="Test Venue", address="123 Test St", capacity=100, owner=self.user)
        self.event = Event.objects.create(
            name="Test Event",
            description="A test event",
            venue=self.venue,
            start_time="2024-01-01T10:00:00Z",
            end_time="2024-01-01T12:00:00Z",
            ticket_price=Decimal("25.00"),
            currency_code="USD", # Ensure currency_code is set
            organizer=self.user
        )
        self.booking = Booking.objects.create(
            user=self.user,
            event=self.event,
            number_of_tickets=2,
            total_price=Decimal("50.00"),
            status='pending'
        )

    def test_create_payment(self):
        payment = Payment.objects.create(
            booking=self.booking,
            amount=self.booking.total_price,
            currency="USD",
            status="pending",
            stripe_payment_intent_id="pi_test12345"
        )
        self.assertIsNotNone(payment.id)
        self.assertEqual(payment.booking, self.booking)
        self.assertEqual(payment.amount, Decimal("50.00"))
        self.assertEqual(payment.status, "pending")
        self.assertEqual(payment.stripe_payment_intent_id, "pi_test12345")
        self.assertEqual(str(payment), f"Payment {payment.id} for Booking {self.booking.id} - pending")

    def test_payment_status_choices(self):
        payment = Payment.objects.create(booking=self.booking, amount=Decimal("10.00"))
        self.assertEqual(payment.status, 'pending')
        payment.status = 'succeeded'; payment.save()
        self.assertEqual(payment.status, 'succeeded')


class PaymentAPIViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='apiuser', email='api@example.com', password='password123')
        self.venue = Venue.objects.create(name="API Venue", address="456 API St", capacity=50, owner=self.user)
        self.event = Event.objects.create(
            name="API Test Event",
            description="An API test event",
            venue=self.venue,
            start_time="2025-01-01T10:00:00Z",
            end_time="2025-01-01T12:00:00Z",
            ticket_price=Decimal("10.00"),
            currency_code="USD",
            organizer=self.user
        )
        self.booking = Booking.objects.create(
            user=self.user,
            event=self.event,
            number_of_tickets=1,
            total_price=Decimal("10.00"),
            status='pending'
        )
        self.client.force_login(self.user) # Authenticate the test client

    @patch('stripe.PaymentIntent.create')
    def test_create_payment_intent_success(self, mock_stripe_intent_create):
        # Mock Stripe API response
        mock_stripe_intent_create.return_value = MagicMock(
            id='pi_mockedpaymentintent123',
            client_secret='mocked_client_secret_123',
            status='requires_payment_method' # or any initial status
        )

        url = reverse('payments:create_payment_intent')
        data = {'booking_id': str(self.booking.id)}

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, 200) # HTTP 200 OK

        expected_response_data = PaymentIntentResponseSerializer({
            'client_secret': 'mocked_client_secret_123',
            'payment_id': Payment.objects.get(booking=self.booking).id
        }).data
        self.assertEqual(response.data, expected_response_data)

        # Verify a Payment object was created or updated
        payment_exists = Payment.objects.filter(
            booking=self.booking,
            stripe_payment_intent_id='pi_mockedpaymentintent123'
        ).exists()
        self.assertTrue(payment_exists)

        payment = Payment.objects.get(booking=self.booking)
        self.assertEqual(payment.amount, self.booking.total_price)
        self.assertEqual(payment.status, 'pending') # Initial status before webhook

        # Verify Stripe API was called correctly
        mock_stripe_intent_create.assert_called_once_with(
            amount=1000, # 10.00 USD in cents
            currency='usd',
            metadata={'booking_id': str(self.booking.id), 'payment_id': str(payment.id)}
        )

    @patch('stripe.PaymentIntent.create')
    def test_create_payment_intent_booking_not_found(self, mock_stripe_intent_create):
        url = reverse('payments:create_payment_intent')
        invalid_booking_id = uuid.uuid4()
        data = {'booking_id': str(invalid_booking_id)}

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, 404) # HTTP 404 Not Found
        self.assertIn('error', response.data)
        mock_stripe_intent_create.assert_not_called()

    @patch('stripe.PaymentIntent.create')
    def test_create_payment_intent_already_paid(self, mock_stripe_intent_create):
        # Create an existing successful payment for the booking
        Payment.objects.create(
            booking=self.booking,
            amount=self.booking.total_price,
            status='succeeded',
            stripe_payment_intent_id='pi_already_paid'
        )

        url = reverse('payments:create_payment_intent')
        data = {'booking_id': str(self.booking.id)}

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, 400) # HTTP 400 Bad Request
        self.assertIn('error', response.data)
        self.assertIn('already has a payment with status: succeeded', response.data['error'])
        mock_stripe_intent_create.assert_not_called()


    @patch('stripe.Webhook.construct_event')
    def test_stripe_webhook_payment_intent_succeeded(self, mock_construct_event):
        # Create a pending payment
        payment = Payment.objects.create(
            booking=self.booking,
            amount=self.booking.total_price,
            status='pending',
            stripe_payment_intent_id='pi_testwebhook123'
        )

        # Mock Stripe event
        mock_event_payload = {
            'id': 'evt_testevent123',
            'type': 'payment_intent.succeeded',
            'data': {
                'object': {
                    'id': 'pi_testwebhook123', # Matches our payment's intent ID
                    'object': 'payment_intent',
                    'amount': int(self.booking.total_price * 100),
                    'currency': 'usd',
                    'status': 'succeeded',
                    'metadata': {'booking_id': str(self.booking.id), 'payment_id': str(payment.id)}
                }
            }
        }
        mock_construct_event.return_value = stripe.Event.construct_from(mock_event_payload, stripe.api_key)

        url = reverse('payments:stripe_webhook')
        # The signature doesn't matter here as construct_event is mocked
        response = self.client.post(url, data=mock_event_payload, content_type='application/json', HTTP_STRIPE_SIGNATURE='dummy_sig')

        self.assertEqual(response.status_code, 200) # HTTP 200 OK

        payment.refresh_from_db()
        self.assertEqual(payment.status, 'succeeded')

        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, 'confirmed') # Check if booking status updated

    @patch('stripe.Webhook.construct_event')
    def test_stripe_webhook_payment_intent_failed(self, mock_construct_event):
        payment = Payment.objects.create(
            booking=self.booking,
            amount=self.booking.total_price,
            status='pending',
            stripe_payment_intent_id='pi_testwebhook_failed'
        )
        mock_event_payload = {
            'id': 'evt_testevent_failed',
            'type': 'payment_intent.payment_failed',
            'data': {
                'object': {
                    'id': 'pi_testwebhook_failed',
                    'object': 'payment_intent',
                     'metadata': {'booking_id': str(self.booking.id), 'payment_id': str(payment.id)}
                }
            }
        }
        mock_construct_event.return_value = stripe.Event.construct_from(mock_event_payload, stripe.api_key)
        url = reverse('payments:stripe_webhook')
        response = self.client.post(url, data=mock_event_payload, content_type='application/json', HTTP_STRIPE_SIGNATURE='dummy_sig')
        self.assertEqual(response.status_code, 200)
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'failed')

    def test_stripe_webhook_missing_secret(self):
        # Temporarily unset STRIPE_WEBHOOK_SECRET
        original_secret = settings.STRIPE_WEBHOOK_SECRET
        settings.STRIPE_WEBHOOK_SECRET = "" # Simulate missing secret

        url = reverse('payments:stripe_webhook')
        response = self.client.post(url, data={}, content_type='application/json')

        self.assertEqual(response.status_code, 500) # Internal Server Error
        self.assertIn('Webhook secret not configured', response.data['error'])

        settings.STRIPE_WEBHOOK_SECRET = original_secret # Restore

    @patch('stripe.Webhook.construct_event')
    def test_stripe_webhook_invalid_signature(self, mock_construct_event):
        mock_construct_event.side_effect = stripe.error.SignatureVerificationError("Invalid signature", "sig_invalid")

        url = reverse('payments:stripe_webhook')
        response = self.client.post(url, data={'id': 'evt_test'}, content_type='application/json', HTTP_STRIPE_SIGNATURE='invalid_sig')

        self.assertEqual(response.status_code, 400) # Bad Request
        self.assertIn('Invalid signature', response.data['error'])

    # Add more tests for other webhook events (requires_action, canceled) if desired
    # Add tests for PaymentDetailView (permissions, retrieval)
    def test_get_payment_detail_authenticated_owner(self):
        payment = Payment.objects.create(booking=self.booking, amount=self.booking.total_price, status='succeeded')
        url = reverse('payments:payment_detail', kwargs={'id': payment.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['id'], str(payment.id))

    def test_get_payment_detail_authenticated_not_owner(self):
        other_user = User.objects.create_user(username='otheruser', email='other@example.com', password='password123')
        other_booking = Booking.objects.create(user=other_user, event=self.event, number_of_tickets=1, total_price=self.event.ticket_price, status='pending')
        payment = Payment.objects.create(booking=other_booking, amount=other_booking.total_price, status='succeeded')

        url = reverse('payments:payment_detail', kwargs={'id': payment.id})
        response = self.client.get(url) # Current client is self.user
        self.assertEqual(response.status_code, 404) # Should not find it due to queryset filtering

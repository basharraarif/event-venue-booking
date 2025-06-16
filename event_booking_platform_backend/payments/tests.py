import json
import stripe # For errors and mocking
from unittest.mock import patch, MagicMock
import uuid # For Payment model ID if it's UUID

from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import models # For Sum in BookingSerializer tests if any
from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from events.models import Event, Venue, Category # Assuming Category is used by Event
from bookings.models import Booking
from .models import Payment
# from .serializers import PaymentIntentResponseSerializer # Not directly used in these tests but good for context

User = get_user_model()

# Existing PaymentModelTests (kept as is)
class PaymentModelTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser_model', email='test_model@example.com', password='password123')
        # Assuming Venue requires an owner; if not, this can be simplified.
        # If Venue has an owner field and it's `settings.AUTH_USER_MODEL`
        self.venue = Venue.objects.create(name="Test Venue Model", capacity=100, owner=self.user if hasattr(Venue, 'owner') else None)
        self.category = Category.objects.create(name='Test Category Model')
        self.event = Event.objects.create(
            name="Test Event Model",
            description="A test event for model",
            venue=self.venue,
            category=self.category, # Added category
            start_time=timezone.now() + timezone.timedelta(days=1), # Ensure start_time is in future
            end_time=timezone.now() + timezone.timedelta(days=1, hours=2),
            ticket_price=Decimal("25.00"),
            organizer=self.user if hasattr(Event, 'organizer') else None # Assuming Event might have an organizer
        )
        self.booking = Booking.objects.create(
            user=self.user,
            event=self.event,
            number_of_tickets=2
            # total_price is auto-calculated by model's save method
        )
        self.booking.save() # Ensure total_price is calculated

    def test_create_payment(self):
        payment = Payment.objects.create(
            booking=self.booking,
            amount=self.booking.total_price, # Use calculated total_price
            currency="USD",
            status="pending", # Valid status from Payment model
            stripe_payment_intent_id="pi_model_test123",
            # payment_method="simulated_card" # This field was in existing model, check if still relevant
        )
        self.assertIsNotNone(payment.id) # ID is UUIDField in existing model
        self.assertEqual(payment.booking, self.booking)
        self.assertEqual(payment.amount, self.booking.total_price) # Check against calculated price
        self.assertEqual(payment.status, "pending")
        self.assertEqual(payment.stripe_payment_intent_id, "pi_model_test123")
        # self.assertEqual(payment.payment_method, "simulated_card")
        self.assertEqual(str(payment), f"Payment {payment.id} for Booking {self.booking.id} - pending")

    def test_payment_status_choices(self):
        # Test with status from Payment model's choices
        payment = Payment.objects.create(booking=self.booking, amount=Decimal("10.00"), status='pending')
        self.assertEqual(payment.status, 'pending')
        payment.status = 'succeeded'; payment.save() # Valid status from Payment model
        self.assertEqual(payment.status, 'succeeded')
        payment.status = 'failed'; payment.save() # Valid status from Payment model
        self.assertEqual(payment.status, 'failed')

# New PaymentAPITests for CreatePaymentIntentView and StripeWebhookView
class PaymentAPITests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser_api', email='test_api@example.com', password='password123')
        self.other_user = User.objects.create_user(username='otheruser_api', email='other_api@example.com', password='password123')

        self.category = Category.objects.create(name='Test Category API')
        # Ensure Venue has an owner if required by its model definition
        self.venue = Venue.objects.create(name='Test Venue API', capacity=100, owner=self.user if hasattr(Venue, 'owner') else None)
        self.event = Event.objects.create(
            name='Test Event API',
            description='A great event for API',
            venue=self.venue,
            category=self.category, # Added category
            start_time=timezone.now() + timezone.timedelta(days=10),
            end_time=timezone.now() + timezone.timedelta(days=10, hours=2),
            ticket_price=Decimal("50.00"), # Use Decimal
            status='upcoming' # Ensure event is bookable
        )

        # Create a PENDING_PAYMENT booking for tests
        self.booking_pending_payment = Booking.objects.create(
            user=self.user,
            event=self.event,
            number_of_tickets=2,
            status=Booking.BookingStatus.PENDING_PAYMENT # Crucial for create_payment_intent
        )
        self.booking_pending_payment.save() # Ensure total_price calculation
        # Associated payment object, as the view expects it for PENDING_PAYMENT bookings
        self.payment_for_pending_booking, _ = Payment.objects.get_or_create(
            booking=self.booking_pending_payment,
            defaults={
                'amount': self.booking_pending_payment.total_price,
                'currency': 'USD', # Default currency
                'status': 'pending' # Default status from Payment model
            }
        )

        self.booking_confirmed = Booking.objects.create(
            user=self.user,
            event=self.event,
            number_of_tickets=1,
            status=Booking.BookingStatus.CONFIRMED # This booking is already confirmed
        )
        self.booking_confirmed.save()
        Payment.objects.create(
            booking=self.booking_confirmed,
            amount=self.booking_confirmed.total_price,
            currency='USD',
            status='succeeded', # Valid status from Payment model
            stripe_payment_intent_id='pi_confirmed_test_api'
        )

        self.booking_other_user = Booking.objects.create(
            user=self.other_user,
            event=self.event,
            number_of_tickets=1,
            status=Booking.BookingStatus.PENDING_PAYMENT
        )
        self.booking_other_user.save()
        Payment.objects.create(
            booking=self.booking_other_user,
            amount=self.booking_other_user.total_price,
            currency='USD',
            status='pending' # Valid status
        )

        self.client.force_authenticate(user=self.user)

    @patch('stripe.PaymentIntent.create')
    @patch('stripe.PaymentIntent.retrieve')
    def test_create_payment_intent_success(self, mock_retrieve_pi, mock_create_pi):
        mock_pi_object = MagicMock(
            id='pi_test123_api',
            client_secret='pi_test123_secret_test123_api',
            status='requires_payment_method', # Or any other valid Stripe PI status
            amount=int(self.booking_pending_payment.total_price * 100),
            currency='usd'
        )
        mock_create_pi.return_value = mock_pi_object
        mock_retrieve_pi.return_value = mock_pi_object

        url = reverse('payments:create-payment-intent')
        data = {'booking_id': str(self.booking_pending_payment.id)} # ID is UUID

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('client_secret', response.data)
        self.assertIn('payment_id', response.data) # payment_id from our DB
        self.assertEqual(response.data['client_secret'], 'pi_test123_secret_test123_api')

        mock_create_pi.assert_called_once()
        self.booking_pending_payment.refresh_from_db()
        self.assertEqual(self.booking_pending_payment.payment_intent_id, 'pi_test123_api')
        payment = Payment.objects.get(booking=self.booking_pending_payment)
        self.assertEqual(payment.stripe_payment_intent_id, 'pi_test123_api')
        self.assertEqual(payment.status, 'pending')

    def test_create_payment_intent_booking_not_found_serializer(self):
        # Test serializer validation for non-existent booking_id
        url = reverse('payments:create-payment-intent')
        # Generate a random UUID that doesn't exist
        non_existent_uuid = uuid.uuid4()
        data = {'booking_id': str(non_existent_uuid)}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Booking not found.', response.data['booking_id'][0])


    def test_create_payment_intent_booking_not_owned_view(self):
        # Test view-level check for booking ownership
        url = reverse('payments:create-payment-intent')
        data = {'booking_id': str(self.booking_other_user.id)} # Belongs to other_user
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('Booking not found or you do not have permission', response.data['error'])


    def test_create_payment_intent_booking_already_paid_serializer(self):
        url = reverse('payments:create-payment-intent')
        data = {'booking_id': str(self.booking_confirmed.id)} # Already confirmed
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Based on PaymentIntentCreateSerializer validation
        self.assertIn("status is 'confirmed'", response.data.get('booking_id', [""])[0])


    @patch('stripe.Webhook.construct_event')
    @patch('core.email_utils.send_booking_related_email') # Mock email sending
    def test_stripe_webhook_payment_intent_succeeded(self, mock_send_email, mock_construct_event):
        booking_to_succeed = Booking.objects.create(
            user=self.user, event=self.event, number_of_tickets=1,
            status=Booking.BookingStatus.PENDING_PAYMENT,
            payment_intent_id='pi_succeed_test_api'
        )
        booking_to_succeed.save()
        Payment.objects.create(
            booking=booking_to_succeed,
            amount=booking_to_succeed.total_price,
            currency='USD', status='pending',
            stripe_payment_intent_id='pi_succeed_test_api'
        )

        event_payload = {
            'id': 'evt_test_succeeded_api', 'type': 'payment_intent.succeeded',
            'data': { 'object': {
                    'id': 'pi_succeed_test_api', 'amount': int(booking_to_succeed.total_price * 100),
                    'currency': 'usd', 'metadata': {'booking_id': str(booking_to_succeed.id)},
                    'status': 'succeeded'
            }}}
        mock_construct_event.return_value = stripe.Event.construct_from(event_payload, settings.STRIPE_SECRET_KEY)

        url = reverse('payments:stripe-webhook')
        response = self.client.post(url, data=json.dumps(event_payload), content_type='application/json', HTTP_STRIPE_SIGNATURE='whsec_test_signature_api')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        booking_to_succeed.refresh_from_db()
        self.assertEqual(booking_to_succeed.status, Booking.BookingStatus.CONFIRMED)
        payment = Payment.objects.get(stripe_payment_intent_id='pi_succeed_test_api')
        self.assertEqual(payment.status, 'succeeded')
        mock_send_email.assert_called_once() # Check if email was called

    @patch('stripe.Webhook.construct_event')
    @patch('core.email_utils.send_booking_related_email') # Mock email sending
    def test_stripe_webhook_payment_intent_failed(self, mock_send_email, mock_construct_event):
        booking_to_fail = Booking.objects.create(
            user=self.user, event=self.event, number_of_tickets=1,
            status=Booking.BookingStatus.PENDING_PAYMENT,
            payment_intent_id='pi_fail_test_api'
        )
        booking_to_fail.save()
        Payment.objects.create(
            booking=booking_to_fail,
            amount=booking_to_fail.total_price,
            currency='USD', status='pending',
            stripe_payment_intent_id='pi_fail_test_api'
        )

        event_payload = {
            'id': 'evt_test_failed_api', 'type': 'payment_intent.payment_failed',
            'data': { 'object': {
                    'id': 'pi_fail_test_api', 'amount': int(booking_to_fail.total_price * 100),
                    'currency': 'usd', 'metadata': {'booking_id': str(booking_to_fail.id)},
                    'status': 'requires_payment_method', 'last_payment_error': {'message': 'Your card was declined.'}
            }}}
        mock_construct_event.return_value = stripe.Event.construct_from(event_payload, settings.STRIPE_SECRET_KEY)

        url = reverse('payments:stripe-webhook')
        response = self.client.post(url, data=json.dumps(event_payload), content_type='application/json', HTTP_STRIPE_SIGNATURE='whsec_test_signature_api_fail')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        booking_to_fail.refresh_from_db()
        self.assertEqual(booking_to_fail.status, Booking.BookingStatus.PENDING_PAYMENT)
        payment = Payment.objects.get(stripe_payment_intent_id='pi_fail_test_api')
        self.assertEqual(payment.status, 'failed')
        mock_send_email.assert_called_once() # Check if email was called

    @patch('stripe.Webhook.construct_event')
    def test_stripe_webhook_invalid_signature(self, mock_construct_event):
        mock_construct_event.side_effect = stripe.error.SignatureVerificationError("Invalid signature", "sig_header_api")

        url = reverse('payments:stripe-webhook')
        response = self.client.post(url, data=json.dumps({'id': 'evt_test_sig_api', 'type': 'payment_intent.succeeded'}), content_type='application/json', HTTP_STRIPE_SIGNATURE='whsec_invalid_signature_api')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Invalid signature', response.data['error'])

    def test_create_payment_intent_unauthenticated(self):
        self.client.force_authenticate(user=None)
        url = reverse('payments:create-payment-intent')
        data = {'booking_id': str(self.booking_pending_payment.id)}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('stripe.PaymentIntent.create')
    def test_create_payment_intent_zero_price_booking_serializer(self, mock_create_pi):
        zero_price_event = Event.objects.create(
            name='Free Event API', venue=self.venue, category=self.category,
            start_time=timezone.now() + timezone.timedelta(days=5),
            end_time=timezone.now() + timezone.timedelta(days=5, hours=1),
            ticket_price=Decimal("0.00"), status='upcoming' # Zero price
        )
        zero_price_booking = Booking.objects.create(user=self.user, event=zero_price_event, number_of_tickets=1, status=Booking.BookingStatus.PENDING_PAYMENT)
        zero_price_booking.save() # Ensure total_price is 0
        self.assertEqual(zero_price_booking.total_price, Decimal("0.00"))

        url = reverse('payments:create-payment-intent')
        data = {'booking_id': str(zero_price_booking.id)}
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Booking does not require payment', response.data.get('booking_id', [""])[0])
        mock_create_pi.assert_not_called()

    @patch('stripe.PaymentIntent.create')
    def test_create_payment_intent_booking_status_not_pending_payment_serializer(self, mock_create_pi):
        pending_booking = Booking.objects.create(user=self.user, event=self.event, number_of_tickets=1, status=Booking.BookingStatus.PENDING) # Not PENDING_PAYMENT
        pending_booking.save()
        Payment.objects.create(booking=pending_booking, amount=pending_booking.total_price, currency='USD', status='pending')

        url = reverse('payments:create-payment-intent')
        data = {'booking_id': str(pending_booking.id)}
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("status is 'pending'. Payment intent can only be created for bookings in 'pending_payment' status.", response.data.get('booking_id', [""])[0])
        mock_create_pi.assert_not_called()


# Existing PaymentViewSetTests (can be reviewed and cleaned up later if needed)
class PaymentViewSetTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='apiuser_pv', email='api_pv@example.com', password='password123')
        self.venue = Venue.objects.create(name="API Venue PV", capacity=50, owner=self.user if hasattr(Venue, 'owner') else None)
        self.category = Category.objects.create(name='Test Category PV')
        self.event = Event.objects.create(
            name="API Test Event PV", venue=self.venue, category=self.category,
            start_time=timezone.now() + timezone.timedelta(days=20), # Ensure distinct times
            end_time=timezone.now() + timezone.timedelta(days=20, hours=2),
            ticket_price=Decimal("10.00"), organizer=self.user if hasattr(Event, 'organizer') else None
        )
        self.booking = Booking.objects.create(user=self.user, event=self.event, number_of_tickets=1)
        self.booking.save()
        self.payment = Payment.objects.create(booking=self.booking, amount=self.booking.total_price, currency="USD", status="pending")

        self.other_user = User.objects.create_user(username='otheruserpay_pv', email='otherpay_pv@example.com', password='otherpassword')
        self.admin_user = User.objects.create_superuser('adminpay_pv', 'adminpay_pv@example.com', 'adminpaypass')

        self.payment_list_url = reverse('payments:payment-view-list') # Ensure correct basename 'payment-view'
        self.payment_detail_url = reverse('payments:payment-view-detail', kwargs={'pk': self.payment.pk})

        self.client.force_authenticate(user=self.user) # Authenticate as normal user for most tests


    def test_list_payments_for_user(self):
        booking2 = Booking.objects.create(user=self.user, event=self.event, number_of_tickets=2)
        booking2.save()
        Payment.objects.create(booking=booking2, amount=booking2.total_price, status='pending')
        response = self.client.get(self.payment_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data if isinstance(response.data, list) else response.data.get('results', [])
        self.assertEqual(len(results), 2)

    def test_list_payments_other_user_no_access(self):
        other_booking = Booking.objects.create(user=self.other_user, event=self.event, number_of_tickets=1)
        other_booking.save()
        Payment.objects.create(booking=other_booking, amount=other_booking.total_price, status='pending')
        response = self.client.get(self.payment_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data if isinstance(response.data, list) else response.data.get('results', [])
        self.assertEqual(len(results), 1) # Should only see self.payment
        self.assertEqual(results[0]['id'], str(self.payment.id))

    def test_retrieve_payment_detail_owner(self):
        response = self.client.get(self.payment_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], str(self.payment.id))

    def test_retrieve_payment_detail_not_owner(self):
        other_booking = Booking.objects.create(user=self.other_user, event=self.event, number_of_tickets=1)
        other_booking.save()
        other_payment = Payment.objects.create(booking=other_booking, amount=other_booking.total_price, status='pending')
        url = reverse('payments:payment-view-detail', kwargs={'pk': other_payment.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_can_list_all_payments(self):
        self.client.force_authenticate(user=self.admin_user)

        other_booking = Booking.objects.create(user=self.other_user, event=self.event, number_of_tickets=1)
        other_booking.save()
        other_payment = Payment.objects.create(booking=other_booking, amount=other_booking.total_price, status='pending')

        admin_booking = Booking.objects.create(user=self.admin_user, event=self.event, number_of_tickets=3)
        admin_booking.save()
        admin_payment = Payment.objects.create(booking=admin_booking, amount=admin_booking.total_price, status='pending')

        response = self.client.get(self.payment_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data if isinstance(response.data, list) else response.data.get('results', [])
        # Admin should see all payments: self.payment (owned by self.user), other_payment, admin_payment
        self.assertEqual(len(results), 3)
        payment_ids_in_response = {p['id'] for p in results}
        self.assertIn(str(self.payment.id), payment_ids_in_response)
        self.assertIn(str(other_payment.id), payment_ids_in_response)
        self.assertIn(str(admin_payment.id), payment_ids_in_response)

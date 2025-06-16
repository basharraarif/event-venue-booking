from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal
from rest_framework.exceptions import ValidationError
import uuid

from payments.models import Payment
from payments.serializers import PaymentSerializer, PaymentIntentCreateSerializer, PaymentIntentResponseSerializer
from bookings.models import Booking
from events.models import Event # Venue removed from here
from venues.models import Venue # Venue imported from here
from django.utils import timezone

User = get_user_model()

class PaymentSerializerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='testpaymentuser', password='password')
        cls.venue = Venue.objects.create(name='Payment Venue', address='1 Pay St', capacity=10, owner=cls.user)
        cls.event = Event.objects.create(
            name='Payment Event', venue=cls.venue, organizer=cls.user,
            start_time=timezone.now() + timezone.timedelta(days=1),
            end_time=timezone.now() + timezone.timedelta(days=2),
            ticket_price=Decimal('100.00')
        )
        cls.booking = Booking.objects.create(event=cls.event, user=cls.user, number_of_tickets=1)
        # cls.booking.status = Booking.BookingStatus.PENDING_PAYMENT # Set by view usually
        # cls.booking.save()

        cls.payment = Payment.objects.create(
            booking=cls.booking,
            amount=cls.booking.total_price, # Should be 100.00
            currency='USD',
            status='succeeded',
            stripe_payment_intent_id='pi_test_123'
        )

    def test_payment_serializer_data(self):
        serializer = PaymentSerializer(instance=self.payment)
        data = serializer.data

        self.assertEqual(data['id'], str(self.payment.id))
        self.assertEqual(data['booking_id'], self.booking.id)
        self.assertEqual(data['user_id'], str(self.user.id)) # User ID is string in serializer
        self.assertEqual(Decimal(data['amount']), self.payment.amount)
        self.assertEqual(data['currency'], self.payment.currency)
        self.assertEqual(data['status'], self.payment.status)
        self.assertEqual(data['stripe_payment_intent_id'], self.payment.stripe_payment_intent_id)
        self.assertIn('created_at', data)
        self.assertIn('updated_at', data)

    def test_payment_serializer_read_only_fields(self):
        # Attempt to update read-only fields should be ignored
        update_data = {
            'amount': Decimal('200.00'), # This is read-only
            'status': 'failed', # This is read-only
            'stripe_payment_intent_id': 'pi_new_id_attempt' # Read-only
        }
        serializer = PaymentSerializer(instance=self.payment, data=update_data, partial=True)
        self.assertTrue(serializer.is_valid()) # Serializer will be valid as it ignores read-only fields for update
        serializer.save() # Save will not modify read-only fields

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.amount, Decimal('100.00')) # Should not change
        self.assertEqual(self.payment.status, 'succeeded') # Should not change
        self.assertEqual(self.payment.stripe_payment_intent_id, 'pi_test_123') # Should not change


class PaymentIntentCreateSerializerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='testpicuser', password='password')
        cls.venue = Venue.objects.create(name='PIC Venue', address='1 PIC St', capacity=10, owner=cls.user)

        cls.event_payable = Event.objects.create(
            name='Payable Event', venue=cls.venue, organizer=cls.user,
            start_time=timezone.now() + timezone.timedelta(days=1), ticket_price=Decimal('50.00')
        )
        cls.booking_pending_payment = Booking.objects.create(event=cls.event_payable, user=cls.user, number_of_tickets=1)
        cls.booking_pending_payment.status = Booking.BookingStatus.PENDING_PAYMENT # Explicitly set for test
        cls.booking_pending_payment.save()
        # Payment object usually created by view logic when booking becomes PENDING_PAYMENT
        Payment.objects.create(booking=cls.booking_pending_payment, amount=cls.booking_pending_payment.total_price, status='pending')


        cls.event_free = Event.objects.create(
            name='Free Event', venue=cls.venue, organizer=cls.user,
            start_time=timezone.now() + timezone.timedelta(days=1), ticket_price=Decimal('0.00')
        )
        cls.booking_free = Booking.objects.create(event=cls.event_free, user=cls.user, number_of_tickets=1)
        cls.booking_free.status = Booking.BookingStatus.CONFIRMED # Free events are confirmed directly
        cls.booking_free.save()

        cls.booking_confirmed_paid = Booking.objects.create(event=cls.event_payable, user=cls.user, number_of_tickets=1)
        cls.booking_confirmed_paid.status = Booking.BookingStatus.CONFIRMED
        cls.booking_confirmed_paid.save()
        Payment.objects.create(booking=cls.booking_confirmed_paid, amount=cls.booking_confirmed_paid.total_price, status='succeeded')

        cls.booking_failed_payment = Booking.objects.create(event=cls.event_payable, user=cls.user, number_of_tickets=1)
        cls.booking_failed_payment.status = Booking.BookingStatus.PENDING_PAYMENT # Still PENDING_PAYMENT
        cls.booking_failed_payment.save()
        Payment.objects.create(booking=cls.booking_failed_payment, amount=cls.booking_failed_payment.total_price, status='failed')


    def test_valid_booking_id_pending_payment(self):
        data = {'booking_id': self.booking_pending_payment.id}
        serializer = PaymentIntentCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['booking_id'], self.booking_pending_payment.id)

    def test_valid_booking_id_failed_payment_object(self):
        # Booking status is PENDING_PAYMENT, associated Payment object status is 'failed'
        data = {'booking_id': self.booking_failed_payment.id}
        serializer = PaymentIntentCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['booking_id'], self.booking_failed_payment.id)

    def test_invalid_booking_id_not_found(self):
        data = {'booking_id': uuid.uuid4()} # Non-existent booking
        serializer = PaymentIntentCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('booking_id', serializer.errors)
        self.assertIn('Booking not found.', str(serializer.errors['booking_id']))

    def test_invalid_booking_id_free_event(self):
        # Booking for a free event (total_price=0)
        data = {'booking_id': self.booking_free.id}
        serializer = PaymentIntentCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('booking_id', serializer.errors)
        self.assertIn('Booking does not require payment', str(serializer.errors['booking_id']))

    def test_invalid_booking_id_already_confirmed_paid(self):
        # Booking is already CONFIRMED, and associated Payment is 'succeeded'
        data = {'booking_id': self.booking_confirmed_paid.id}
        serializer = PaymentIntentCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('booking_id', serializer.errors)
        # Error message comes from booking.status != PENDING_PAYMENT check
        self.assertIn(f"Booking status is '{Booking.BookingStatus.CONFIRMED}'. Payment intent can only be created for bookings in '{Booking.BookingStatus.PENDING_PAYMENT}' status.", str(serializer.errors['booking_id']))


class PaymentIntentResponseSerializerTests(TestCase):
    def test_serialize_payment_intent_response(self):
        data = {'client_secret': 'cs_test_123', 'payment_id': uuid.uuid4()}
        serializer = PaymentIntentResponseSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        # Accessing .data after is_valid() is fine
        self.assertEqual(serializer.data['client_secret'], 'cs_test_123')
        self.assertEqual(serializer.data['payment_id'], data['payment_id'])

    def test_deserialize_payment_intent_response_invalid_missing_field(self):
        data = {'client_secret': 'cs_test_123'} # Missing payment_id
        serializer = PaymentIntentResponseSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('payment_id', serializer.errors)
        self.assertIn('This field is required.', str(serializer.errors['payment_id']))

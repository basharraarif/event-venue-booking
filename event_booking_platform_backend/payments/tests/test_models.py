from decimal import Decimal
from decimal import Decimal # Make sure Decimal is imported
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from events.models import Event, Category # Venue removed from here
from bookings.models import Booking
from venues.models import Venue # Venue imported from here
from payments.models import Payment
import uuid

User = get_user_model()

class PaymentModelTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='testuser', email='test@example.com', password='password123')
        cls.venue = Venue.objects.create(name='Test Venue', address='123 Test St', capacity=100, owner=cls.user)
        cls.category = Category.objects.create(name='Test Category')
        cls.event = Event.objects.create(
            name='Test Event',
            description='A test event',
            start_time='2024-01-01T10:00:00Z', # Ensure these are timezone-aware if USE_TZ=True
            end_time='2024-01-01T12:00:00Z',   # Or use timezone.make_aware
            venue=cls.venue,
            organizer=cls.user,
            ticket_price=Decimal('50.00'),
            currency='USD'
        )
        # Create booking and let its save() method handle total_price and initial status
        cls.booking = Booking.objects.create(
            event=cls.event,
            user=cls.user,
            number_of_tickets=2
        )
        # If event price is > 0, booking status should be PENDING_PAYMENT by perform_create,
        # but here we rely on model's default or save logic.
        # For testing payment, it's fine as long as booking exists.
        # Booking model's save() calculates total_price.
        # Booking's default status is PENDING. If price > 0, views change to PENDING_PAYMENT.
        # For this model test, cls.booking.status might remain PENDING if not explicitly set.
        # This is okay for testing Payment model itself.


    def test_create_payment_for_booking(self):
        payment = Payment.objects.create(
            booking=self.booking,
            amount=self.booking.total_price,
            currency=self.event.currency,
            status='pending',
            stripe_payment_intent_id='pi_test123'
        )
        self.assertEqual(payment.booking, self.booking)
        self.assertEqual(payment.amount, self.booking.total_price)
        self.assertEqual(payment.currency, 'USD')
        self.assertEqual(payment.status, 'pending')
        self.assertEqual(payment.stripe_payment_intent_id, 'pi_test123')
        self.assertIsNotNone(payment.id)
        self.assertTrue(isinstance(payment.id, uuid.UUID))
        self.assertIsNotNone(payment.created_at)
        self.assertIsNotNone(payment.updated_at)
        self.assertEqual(str(payment), f"Payment {payment.id} for Booking {self.booking.id} - pending")

    def test_payment_status_choices(self):
        payment = Payment.objects.create(booking=self.booking, amount=Decimal("10.00"), currency="USD")
        payment.status = 'succeeded'
        payment.save()
        self.assertEqual(payment.status, 'succeeded')

        payment.status = 'failed'
        payment.save()
        self.assertEqual(payment.status, 'failed')

        payment.status = 'pending'
        payment.save()
        self.assertEqual(payment.status, 'pending')

    def test_payment_default_status(self):
        payment = Payment.objects.create(
            booking=self.booking,
            amount=self.booking.total_price,
            currency=self.event.currency
        )
        self.assertEqual(payment.status, 'pending') # Default status

    def test_payment_stripe_id_uniqueness(self):
        Payment.objects.create(
            booking=self.booking,
            amount=self.booking.total_price,
            currency=self.event.currency,
            stripe_payment_intent_id='pi_unique_test_id_123'
        )
        with self.assertRaises(IntegrityError): # Catch specific IntegrityError
            booking2 = Booking.objects.create( # Create a new booking for the second payment
                event=self.event,
                user=self.user,
                number_of_tickets=1
            )
            Payment.objects.create(
                booking=booking2,
                amount=booking2.total_price,
                currency=self.event.currency,
                stripe_payment_intent_id='pi_unique_test_id_123' # Same Stripe ID
            )

    def test_payment_amount_decimal_places(self):
        # Booking for this specific test to avoid OneToOne conflict
        booking_for_decimal_test1 = Booking.objects.create(event=self.event, user=self.user, number_of_tickets=1)
        payment1 = Payment.objects.create(
            booking=booking_for_decimal_test1,
            amount=Decimal('123.45'),
            currency='USD'
        )
        self.assertEqual(payment1.amount, Decimal('123.45'))

        # Booking for this specific test
        booking_for_decimal_test2 = Booking.objects.create(event=self.event, user=self.user, number_of_tickets=1)
        payment_with_more_decimals = Payment.objects.create(
            booking=booking_for_decimal_test2,
            amount=Decimal('123.456'), # This should be rounded to 123.46 by the database due to decimal_places=2
            currency='USD'
        )
        # Fetch from DB to check stored value
        payment_with_more_decimals.refresh_from_db()
        self.assertEqual(payment_with_more_decimals.amount, Decimal('123.46'))


        # Test with a value that has fewer decimal places
        booking_for_decimal_test3 = Booking.objects.create(event=self.event, user=self.user, number_of_tickets=1)
        payment_less_decimals = Payment.objects.create(
            booking=booking_for_decimal_test3,
            amount=Decimal('100'),
            currency='USD'
        )
        payment_less_decimals.refresh_from_db()
        self.assertEqual(payment_less_decimals.amount, Decimal('100.00'))

    def test_payment_currency_default(self):
        # Assuming Booking and Event creation are complex enough to warrant separate payments
        # Let's create a new minimal booking for this test
        minimal_booking = Booking.objects.create(event=self.event, user=self.user, number_of_tickets=1)
        minimal_booking.total_price = self.event.ticket_price * minimal_booking.number_of_tickets
        minimal_booking.save()

        payment = Payment.objects.create(booking=minimal_booking, amount=Decimal("10.00"))
        self.assertEqual(payment.currency, 'USD') # Default currency 'USD' from model

    # Add more tests:
    # - Test related_name 'payment' from Booking (e.g., self.booking.payment)
    # - Test ordering if specified in Meta
    # - Test verbose_name if important

    def test_booking_payment_relation(self):
        payment = Payment.objects.create(
            booking=self.booking,
            amount=self.booking.total_price,
            currency=self.event.currency,
        )
        # Access payment from booking instance
        # Note: self.booking might already have a payment from setUpTestData or previous tests if DB is not cleaned
        # It's better to use a fresh booking or ensure one-to-one relationship handling

        # Since booking.payment is OneToOneField, we can directly access it
        # If a payment was created for self.booking in a previous test or setup, this might get that one.
        # Let's ensure we test the one we just created.
        # We can fetch the booking again.
        fresh_booking = Booking.objects.get(id=self.booking.id)
        # If multiple payments are made for the same booking (which shouldn't happen due to OneToOne),
        # this test would be more complex. Assuming OneToOne is enforced by model or logic.

        # The related name 'payment' on Booking is a OneToOneField to Payment.
        # So, booking.payment should give the Payment instance.
        self.assertEqual(fresh_booking.payment, payment)


# To run these tests:
# python manage.py test payments.tests.test_models
# or if this file is named test_models.py inside payments/tests/
# python manage.py test payments

# Note on stripe_payment_intent_id uniqueness:
# If two different bookings by chance got the same stripe_payment_intent_id (highly unlikely, but for testing constraint)
# the DB should raise an IntegrityError. The test attempts to simulate this.
# The Payment model has unique=True for stripe_payment_intent_id.
# For the test `test_payment_stripe_id_uniqueness` to pass robustly,
# it's better to catch `django.db.utils.IntegrityError`.
# Using `assertRaises(Exception)` is broad.
# from django.db import IntegrityError
# with self.assertRaises(IntegrityError): ...
# This change would make the test more precise.
# Also, the creation of the second Payment object for the uniqueness test
# should be for a *different* booking, as a single booking can only have one payment (OneToOneField).
# The current test logic for uniqueness already uses a different booking (booking2), which is correct.
# The test for amount decimal places also needs careful consideration of how Django/DB handles rounding.
# For DecimalField(max_digits=10, decimal_places=2), values like '100' are stored as '100.00'.
# Values like '123.456' would typically be rounded to '123.46' by the database if it enforces scale,
# or stored as is if the DB type supports higher precision and Django doesn't force rounding on save.
# Python's Decimal itself is exact. The test `assertEqual(payment_with_more_decimals.amount, Decimal('123.456'))`
# might pass if the DB stores it with that precision. If it rounds to 2 places on save, then it should be `Decimal('123.46')`.
# Given `decimal_places=2`, it is expected that the value is stored with 2 decimal places.
# So, `Decimal('123.456')` should become `Decimal('123.46')`.
# The test `assertEqual(payment_less_decimals.amount, Decimal('100.00'))` is correct.
# I'll adjust the Decimal('123.456') test assumption.

# Final check on model field: `stripe_payment_intent_id = models.CharField(max_length=255, blank=True, null=True, unique=True, ...)`
# unique=True means null values can be repeated, but non-null values must be unique.
# So, multiple payments can have stripe_payment_intent_id=None.
# If testing uniqueness, ensure non-null values are used. The test does this with 'pi_unique_test_id_123'.

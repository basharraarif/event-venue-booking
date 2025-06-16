from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from decimal import Decimal
from rest_framework.exceptions import ValidationError

from bookings.models import Booking
from bookings.serializers import BookingSerializer
from events.models import Event, Category
from venues.models import Venue
from core.models import Role # For setting up user roles if needed for specific tests

User = get_user_model()

class BookingSerializerTests(TestCase):

    def setUp(self):
        self.booker_user = User.objects.create_user(username='booker', password='password')
        self.organizer_user = User.objects.create_user(username='event_org', password='password')

        self.venue = Venue.objects.create(name='Event Venue', address='123 Test Ave', capacity=100, owner=self.organizer_user)
        self.event = Event.objects.create(
            name='Test Capacity Event',
            venue=self.venue,
            organizer=self.organizer_user,
            start_time=timezone.now() + timezone.timedelta(days=5),
            end_time=timezone.now() + timezone.timedelta(days=5, hours=3),
            ticket_price=Decimal('20.00'),
            status='upcoming'
            # max_capacity will be tested with different values
        )
        # Context for serializer if it uses request (e.g., for user)
        self.serializer_context = {'request': None}


    def test_booking_successful_within_venue_capacity(self):
        self.event.max_capacity = None # Use venue capacity
        self.event.save()

        data = {'event': self.event.pk, 'number_of_tickets': 5}
        serializer = BookingSerializer(data=data, context=self.serializer_context)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        # In actual flow, viewset's perform_create passes price_per_ticket_at_booking to save.
        # Here, we simulate that or let the model's save() handle it.
        # Let's assume model's save will snapshot it from self.event.ticket_price as price_per_ticket_at_booking is not in `data`.
        booking = serializer.save(user=self.booker_user)

        self.assertEqual(booking.number_of_tickets, 5)
        self.assertEqual(Booking.objects.count(), 1)
        # Assert that price_per_ticket_at_booking was snapshotted from event's current price
        self.assertEqual(booking.price_per_ticket_at_booking, self.event.ticket_price) # self.event.ticket_price is 20.00
        # Assert total_price is calculated based on the snapshot
        expected_total_price = self.event.ticket_price * 5
        self.assertEqual(booking.total_price, expected_total_price)


    def test_booking_successful_within_event_max_capacity(self):
        self.event.max_capacity = 10 # Event specific capacity, less than venue's 100
        self.event.save()

        data = {'event': self.event.pk, 'number_of_tickets': 7}
        serializer = BookingSerializer(data=data, context=self.serializer_context)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        booking = serializer.save(user=self.booker_user)
        self.assertEqual(booking.number_of_tickets, 7)

    def test_fail_booking_tickets_less_than_or_equal_to_zero(self):
        data_zero_tickets = {'event': self.event.pk, 'number_of_tickets': 0}
        serializer_zero = BookingSerializer(data=data_zero_tickets, context=self.serializer_context)
        self.assertFalse(serializer_zero.is_valid())
        self.assertIn('number_of_tickets', serializer_zero.errors)
        self.assertIn("Number of tickets must be greater than zero.", serializer_zero.errors['number_of_tickets'][0]) # From validate_number_of_tickets

        data_negative_tickets = {'event': self.event.pk, 'number_of_tickets': -1}
        serializer_neg = BookingSerializer(data=data_negative_tickets, context=self.serializer_context)
        self.assertFalse(serializer_neg.is_valid())
        self.assertIn('number_of_tickets', serializer_neg.errors)


    def test_fail_booking_event_effective_capacity_zero(self):
        self.event.max_capacity = 0 # Event capacity is zero
        self.event.save()

        data = {'event': self.event.pk, 'number_of_tickets': 1}
        serializer = BookingSerializer(data=data, context=self.serializer_context)
        self.assertFalse(serializer.is_valid())
        self.assertIn('number_of_tickets', serializer.errors)
        self.assertIn("This event is not available for booking as it has zero capacity.", serializer.errors['number_of_tickets'][0])

    def test_fail_booking_exceeds_event_max_capacity(self):
        self.event.max_capacity = 5
        self.event.save()

        data = {'event': self.event.pk, 'number_of_tickets': 6}
        serializer = BookingSerializer(data=data, context=self.serializer_context)
        self.assertFalse(serializer.is_valid())
        self.assertIn('number_of_tickets', serializer.errors)
        self.assertIn("Only 5 ticket(s) currently available", str(serializer.errors['number_of_tickets'][0])) # Adjusted wording

    def test_fail_booking_exceeds_venue_capacity_when_event_max_capacity_none(self):
        self.venue.capacity = 3
        self.venue.save()
        self.event.max_capacity = None # Event uses venue capacity
        self.event.save()

        data = {'event': self.event.pk, 'number_of_tickets': 4}
        serializer = BookingSerializer(data=data, context=self.serializer_context)
        self.assertFalse(serializer.is_valid())
        self.assertIn('number_of_tickets', serializer.errors)
        self.assertIn("Only 3 ticket(s) currently available", str(serializer.errors['number_of_tickets'][0])) # Adjusted wording

    def test_concurrent_booking_fill_capacity(self):
        self.event.max_capacity = 2
        self.event.save()

        user1 = User.objects.create_user('concurrent_user1', 'pass1')
        user2 = User.objects.create_user('concurrent_user2', 'pass2')
        user3 = User.objects.create_user('concurrent_user3', 'pass3')

        # User 1 books 1 ticket (1 remaining)
        data1 = {'event': self.event.pk, 'number_of_tickets': 1}
        serializer1 = BookingSerializer(data=data1, context=self.serializer_context)
        self.assertTrue(serializer1.is_valid(), serializer1.errors)
        booking1 = serializer1.save(user=user1)
        booking1.status = Booking.BookingStatus.CONFIRMED # Confirm booking to count against capacity
        booking1.save()

        self.assertEqual(self.event.confirmed_tickets_count(), 1)

        # User 2 books 1 ticket (0 remaining)
        data2 = {'event': self.event.pk, 'number_of_tickets': 1}
        serializer2 = BookingSerializer(data=data2, context=self.serializer_context)
        self.assertTrue(serializer2.is_valid(), serializer2.errors)
        booking2 = serializer2.save(user=user2)
        booking2.status = Booking.BookingStatus.CONFIRMED
        booking2.save()

        self.assertEqual(self.event.confirmed_tickets_count(), 2)

        # User 3 tries to book 1 ticket (should fail)
        data3 = {'event': self.event.pk, 'number_of_tickets': 1}
        serializer3 = BookingSerializer(data=data3, context=self.serializer_context)
        self.assertFalse(serializer3.is_valid())
        self.assertIn('number_of_tickets', serializer3.errors)
        self.assertIn("Only 0 ticket(s) currently available", str(serializer3.errors['number_of_tickets'][0])) # Adjusted wording

    def test_pending_or_cancelled_bookings_do_not_affect_capacity(self):
        self.event.max_capacity = 5
        self.event.save()

        user_pending = User.objects.create_user('pending_booker', 'pass')
        user_cancelled = User.objects.create_user('cancelled_booker', 'pass')
        user_confirmed = User.objects.create_user('confirmed_booker', 'pass')

        Booking.objects.create(event=self.event, user=user_pending, number_of_tickets=2, status=Booking.BookingStatus.PENDING_PAYMENT)
        Booking.objects.create(event=self.event, user=user_cancelled, number_of_tickets=2, status=Booking.BookingStatus.CANCELLED)
        Booking.objects.create(event=self.event, user=user_confirmed, number_of_tickets=1, status=Booking.BookingStatus.CONFIRMED) # Consumes 1

        # With the updated serializer logic, PENDING_PAYMENT and CONFIRMED bookings count towards capacity.
        # Active tickets = 2 (pending_payment from user_pending) + 1 (confirmed from user_confirmed) = 3.
        # Event max_capacity = 5. Available capacity = 5 - 3 = 2.

        # Try to book 2 tickets. Should succeed.
        data = {'event': self.event.pk, 'number_of_tickets': 2}
        serializer = BookingSerializer(data=data, context=self.serializer_context)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        booking = serializer.save(user=self.booker_user)
        # This new booking will be PENDING_PAYMENT by default if event price > 0 (handled by view/perform_create, here it's just PENDING)
        # For capacity check, its requested tickets are added to current active.
        self.assertEqual(booking.number_of_tickets, 2)

        # To accurately test the next step, let's assume this booking also becomes active (e.g., PENDING_PAYMENT or CONFIRMED).
        # If event price > 0, it would typically become PENDING_PAYMENT.
        booking.status = Booking.BookingStatus.PENDING_PAYMENT # or CONFIRMED
        booking.save()

        # Now, active tickets = 3 (initial) + 2 (new booking) = 5. Available capacity = 0.

        # Try to book 1 more ticket. Should fail.
        data_fail = {'event': self.event.pk, 'number_of_tickets': 1}
        serializer_fail = BookingSerializer(data=data_fail, context=self.serializer_context)
        self.assertFalse(serializer_fail.is_valid())
        self.assertIn('number_of_tickets', serializer_fail.errors)
        # The error message from the serializer is "Booking exceeds event capacity. Only {available_tickets} ticket(s) currently available..."
        self.assertIn("Only 0 ticket(s) currently available", str(serializer_fail.errors['number_of_tickets'][0]))


    def test_update_booking_adjusts_capacity_check_correctly(self):
        self.event.max_capacity = 5
        self.event.save()

        # User A makes a confirmed booking for 2 tickets
        user_a = User.objects.create_user('user_a_cap', 'pass')
        booking_a = Booking.objects.create(event=self.event, user=user_a, number_of_tickets=2, status=Booking.BookingStatus.CONFIRMED)

        # User B makes a confirmed booking for 1 ticket
        user_b = User.objects.create_user('user_b_cap', 'pass')
        Booking.objects.create(event=self.event, user=user_b, number_of_tickets=1, status=Booking.BookingStatus.CONFIRMED)

        # Total confirmed tickets = 2 (A) + 1 (B) = 3. Remaining capacity = 5 - 3 = 2.

        # User A tries to update their booking from 2 to 4 tickets.
        # effective_tickets_for_others = 1 (from User B).
        # requested_tickets = 4.
        # effective_tickets_for_others (1) + requested_tickets (4) = 5. This should be allowed.
        update_data = {'number_of_tickets': 4}
        serializer_update = BookingSerializer(instance=booking_a, data=update_data, partial=True, context=self.serializer_context)
        self.assertTrue(serializer_update.is_valid(), serializer_update.errors)
        updated_booking_a = serializer_update.save()
        updated_booking_a.status = Booking.BookingStatus.CONFIRMED # Simulate re-confirmation
        updated_booking_a.save()
        self.assertEqual(updated_booking_a.number_of_tickets, 4)

        # Total confirmed tickets = 4 (A updated) + 1 (B) = 5. Remaining capacity = 0.

        # User B tries to update their booking from 1 to 2 tickets.
        # effective_tickets_for_others = 4 (from User A's updated booking).
        # requested_tickets = 2.
        # effective_tickets_for_others (4) + requested_tickets (2) = 6. Capacity is 5. Should fail.
        # Available = 5 - 4 = 1.
        booking_b = Booking.objects.get(user=user_b, event=self.event)
        update_data_b = {'number_of_tickets': 2}
        serializer_update_b = BookingSerializer(instance=booking_b, data=update_data_b, partial=True, context=self.serializer_context)
        self.assertFalse(serializer_update_b.is_valid())
        self.assertIn('number_of_tickets', serializer_update_b.errors)
        self.assertIn("Only 1 ticket(s) available", str(serializer_update_b.errors['number_of_tickets'][0]))


    def test_booking_for_event_with_no_specific_max_capacity(self):
        # Event max_capacity is None, venue capacity is 100
        self.event.max_capacity = None
        self.event.save()

        data = {'event': self.event.pk, 'number_of_tickets': 100} # Max out venue capacity
        serializer = BookingSerializer(data=data, context=self.serializer_context)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        booking = serializer.save(user=self.booker_user)
        booking.status = Booking.BookingStatus.CONFIRMED
        booking.save()

        self.assertEqual(self.event.confirmed_tickets_count(), 100)

        data_fail = {'event': self.event.pk, 'number_of_tickets': 1}
        serializer_fail = BookingSerializer(data=data_fail, context=self.serializer_context)
        self.assertFalse(serializer_fail.is_valid())
        self.assertIn("Only 0 ticket(s) currently available", str(serializer_fail.errors['number_of_tickets'][0])) # Adjusted wording

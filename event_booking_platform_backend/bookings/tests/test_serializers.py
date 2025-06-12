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
        booking = serializer.save(user=self.booker_user) # Pass user to save method
        self.assertEqual(booking.number_of_tickets, 5)
        self.assertEqual(Booking.objects.count(), 1)

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
        self.assertIn('event', serializer.errors) # Error should be on 'event' or non_field_errors
        self.assertIn("This event is not available for booking (capacity: 0).", serializer.errors['event'][0])

    def test_fail_booking_exceeds_event_max_capacity(self):
        self.event.max_capacity = 5
        self.event.save()

        data = {'event': self.event.pk, 'number_of_tickets': 6}
        serializer = BookingSerializer(data=data, context=self.serializer_context)
        self.assertFalse(serializer.is_valid())
        self.assertIn('number_of_tickets', serializer.errors)
        self.assertIn("Booking exceeds event capacity. Only 5 tickets remaining.", serializer.errors['number_of_tickets'][0])

    def test_fail_booking_exceeds_venue_capacity_when_event_max_capacity_none(self):
        self.venue.capacity = 3
        self.venue.save()
        self.event.max_capacity = None # Event uses venue capacity
        self.event.save()

        data = {'event': self.event.pk, 'number_of_tickets': 4}
        serializer = BookingSerializer(data=data, context=self.serializer_context)
        self.assertFalse(serializer.is_valid())
        self.assertIn('number_of_tickets', serializer.errors)
        self.assertIn("Booking exceeds event capacity. Only 3 tickets remaining.", serializer.errors['number_of_tickets'][0])

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
        self.assertIn("Booking exceeds event capacity. Only 0 tickets remaining.", serializer3.errors['number_of_tickets'][0])

    def test_pending_or_cancelled_bookings_do_not_affect_capacity(self):
        self.event.max_capacity = 5
        self.event.save()

        user_pending = User.objects.create_user('pending_booker', 'pass')
        user_cancelled = User.objects.create_user('cancelled_booker', 'pass')
        user_confirmed = User.objects.create_user('confirmed_booker', 'pass')

        Booking.objects.create(event=self.event, user=user_pending, number_of_tickets=2, status=Booking.BookingStatus.PENDING)
        Booking.objects.create(event=self.event, user=user_cancelled, number_of_tickets=2, status=Booking.BookingStatus.CANCELLED)
        Booking.objects.create(event=self.event, user=user_confirmed, number_of_tickets=1, status=Booking.BookingStatus.CONFIRMED)

        self.assertEqual(self.event.confirmed_tickets_count(), 1) # Only 1 confirmed ticket

        # Try to book 4 tickets. Available = 5 (event.max_capacity) - 1 (confirmed) = 4. Should succeed.
        data = {'event': self.event.pk, 'number_of_tickets': 4}
        serializer = BookingSerializer(data=data, context=self.serializer_context)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        booking = serializer.save(user=self.booker_user)
        self.assertEqual(booking.number_of_tickets, 4)

        # Try to book 1 more ticket. Available should now be 0.
        booking.status = Booking.BookingStatus.CONFIRMED # Confirm the previous booking
        booking.save()
        self.assertEqual(self.event.confirmed_tickets_count(), 5)

        data_fail = {'event': self.event.pk, 'number_of_tickets': 1}
        serializer_fail = BookingSerializer(data=data_fail, context=self.serializer_context)
        self.assertFalse(serializer_fail.is_valid())
        self.assertIn("Only 0 tickets remaining", serializer_fail.errors['number_of_tickets'][0])

    def test_update_booking_adjusts_capacity_check(self):
        self.event.max_capacity = 5
        self.event.save()

        # Booker user makes a confirmed booking for 2 tickets
        initial_booking = Booking.objects.create(event=self.event, user=self.booker_user, number_of_tickets=2, status=Booking.BookingStatus.CONFIRMED)
        self.assertEqual(self.event.confirmed_tickets_count(), 2) # 2 tickets confirmed

        # Try to update this booking to 4 tickets (2 existing + 2 new = 4 total by this user for this event)
        # Available for others = 5 - 2 = 3. This update implies user wants 4 total.
        # Change for this user = 4 (new total) - 2 (old total) = +2 tickets.
        # Other confirmed = 0.
        # 0 (other_confirmed) + 4 (requested_total_for_this_booking) <= 5 (capacity). This should be fine.
        update_data = {'number_of_tickets': 4}
        serializer_update = BookingSerializer(instance=initial_booking, data=update_data, partial=True, context=self.serializer_context)
        self.assertTrue(serializer_update.is_valid(), serializer_update.errors)
        updated_booking = serializer_update.save()
        updated_booking.status = Booking.BookingStatus.CONFIRMED # Assume it remains/becomes confirmed
        updated_booking.save()

        self.assertEqual(updated_booking.number_of_tickets, 4)
        self.assertEqual(self.event.confirmed_tickets_count(), 4)

        # Now, another user tries to book. Remaining capacity = 5 - 4 = 1.
        other_user = User.objects.create_user('other_cap_booker', 'pass')
        data_other_user = {'event': self.event.pk, 'number_of_tickets': 2}
        serializer_other = BookingSerializer(data=data_other_user, context=self.serializer_context)
        self.assertFalse(serializer_other.is_valid())
        self.assertIn("Only 1 tickets remaining", serializer_other.errors['number_of_tickets'][0])

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
        self.assertIn("Only 0 tickets remaining", serializer_fail.errors['number_of_tickets'][0])

from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from decimal import Decimal
from django.core.exceptions import ValidationError

from bookings.models import Booking
from events.models import Event
from venues.models import Venue

User = get_user_model()

class BookingModelSaveTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testbooker', password='password123')
        self.venue_owner = User.objects.create_user(username='testvenueowner', password='password123')
        self.venue = Venue.objects.create(name='Test Venue for Booking Save', address='123 Booking St', capacity=100, owner=self.venue_owner)
        self.event = Event.objects.create(
            name="Test Event for Booking Save",
            venue=self.venue,
            organizer=self.user,
            start_time=timezone.now() + timezone.timedelta(days=10),
            end_time=timezone.now() + timezone.timedelta(days=11),
            ticket_price=Decimal('25.00') # Event ticket price
        )

    def test_booking_save_calculates_total_price(self):
        # Case 1: price_per_ticket_at_booking is set directly (e.g. by viewset)
        booking1 = Booking(
            event=self.event,
            user=self.user,
            number_of_tickets=3,
            price_per_ticket_at_booking=Decimal('30.00') # Explicitly set for test
        )
        booking1.save()
        self.assertEqual(booking1.total_price, Decimal('90.00')) # 3 * 30.00

        # Case 2: price_per_ticket_at_booking is NOT set, should be snapshotted from event
        booking2 = Booking(
            event=self.event,
            user=self.user,
            number_of_tickets=2
            # price_per_ticket_at_booking is None initially
        )
        booking2.save()
        self.assertEqual(booking2.price_per_ticket_at_booking, self.event.ticket_price) # Should be 25.00
        self.assertEqual(booking2.total_price, Decimal('50.00')) # 2 * 25.00

    def test_booking_save_updates_total_price_on_number_of_tickets_change(self):
        booking = Booking.objects.create(
            event=self.event,
            user=self.user,
            number_of_tickets=2,
            price_per_ticket_at_booking=Decimal('20.00') # Snapshotted price
        )
        self.assertEqual(booking.total_price, Decimal('40.00'))

        booking.number_of_tickets = 5
        booking.save() # Should recalculate total_price using the snapshotted price_per_ticket
        self.assertEqual(booking.total_price, Decimal('100.00')) # 5 * 20.00
        self.assertEqual(booking.price_per_ticket_at_booking, Decimal('20.00')) # Snapshot price should not change

    def test_booking_save_with_no_event_ticket_price(self):
        # Scenario: Event has no ticket_price (or it's None), model should default price_per_ticket_at_booking
        self.event.ticket_price = None
        self.event.save()

        booking = Booking(
            event=self.event,
            user=self.user,
            number_of_tickets=3
        )
        booking.save()
        # The model's save method defaults price_per_ticket_at_booking to 0.00 if event.ticket_price is None
        self.assertEqual(booking.price_per_ticket_at_booking, Decimal('0.00'))
        self.assertEqual(booking.total_price, Decimal('0.00')) # 3 * 0.00

    def test_booking_save_does_not_change_snapshotted_price_if_event_price_changes(self):
        booking = Booking.objects.create(
            event=self.event, # Event price is 25.00
            user=self.user,
            number_of_tickets=2
        )
        self.assertEqual(booking.price_per_ticket_at_booking, Decimal('25.00'))
        self.assertEqual(booking.total_price, Decimal('50.00'))

        # Now, change the event's ticket price
        self.event.ticket_price = Decimal('100.00')
        self.event.save()

        # Re-save the booking (e.g., status change or number_of_tickets change)
        booking.number_of_tickets = 3 # Also change number of tickets
        booking.save()

        # The snapshotted price should remain 25.00
        self.assertEqual(booking.price_per_ticket_at_booking, Decimal('25.00'))
        # Total price should be based on the snapshotted price
        self.assertEqual(booking.total_price, Decimal('75.00')) # 3 * 25.00

    def test_booking_clean_number_of_tickets_validation(self):
        booking = Booking(event=self.event, user=self.user, number_of_tickets=0)
        with self.assertRaises(ValidationError) as context:
            booking.clean()
        self.assertIn('number_of_tickets', context.exception.message_dict)
        self.assertIn('Number of tickets must be greater than zero.', context.exception.message_dict['number_of_tickets'])

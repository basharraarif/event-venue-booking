from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from decimal import Decimal
from ..models import Event, Category
from venues.models import Venue
from bookings.models import Booking # Required for confirmed_tickets_count

User = get_user_model()

class EventModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='eventtestuser', password='password')
        self.venue = Venue.objects.create(name='Test Venue For Event', address='123 Event St', capacity=100, owner=self.user)
        self.category = Category.objects.create(name='Tech Conference')
        self.event = Event.objects.create(
            name="Tech Summit 2024",
            venue=self.venue,
            organizer=self.user,
            start_time=timezone.now() + timezone.timedelta(days=30),
            end_time=timezone.now() + timezone.timedelta(days=30, hours=8),
            ticket_price=Decimal('199.99')
        )
        self.event.categories.add(self.category)

    def test_event_creation(self):
        self.assertEqual(str(self.event), "Tech Summit 2024")
        self.assertEqual(self.event.status, 'upcoming')
        self.assertTrue(self.event.categories.filter(name='Tech Conference').exists())

    def test_event_clean_method(self):
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            event_invalid_time = Event(
                name="Invalid Time Event",
                venue=self.venue,
                organizer=self.user,
                start_time=timezone.now() + timezone.timedelta(days=1),
                end_time=timezone.now() + timezone.timedelta(hours=12) # End before start
            )
            event_invalid_time.clean()

    def test_effective_capacity_event_max_capacity_set(self):
        self.event.max_capacity = 50
        self.event.save()
        self.assertEqual(self.event.effective_capacity, 50)

    def test_effective_capacity_event_max_capacity_none(self):
        # Event max_capacity is None, should use venue capacity
        self.event.max_capacity = None
        self.event.save()
        self.assertEqual(self.event.effective_capacity, self.venue.capacity) # venue.capacity is 100

    def test_effective_capacity_no_venue(self):
        event_no_venue = Event(
            name="No Venue Event", organizer=self.user,
            start_time=timezone.now(), end_time=timezone.now() + timezone.timedelta(hours=1)
        )
        # event_no_venue.venue is None, event.max_capacity is None
        self.assertIsNone(event_no_venue.effective_capacity)

    def test_effective_capacity_venue_no_capacity(self):
        self.venue.capacity = 0 # Set venue capacity to 0
        self.venue.save()
        self.event.max_capacity = None # Event uses venue capacity
        self.event.save()
        self.assertEqual(self.event.effective_capacity, 0)

        self.event.max_capacity = 50 # Event capacity explicitly set, should override venue's 0
        self.event.save()
        self.assertEqual(self.event.effective_capacity, 50)


    def test_active_tickets_count_includes_confirmed_and_pending_payment(self):
        # No bookings initially
        self.assertEqual(self.event.active_tickets_count(), 0)

        # Add some bookings with different statuses
        booking_user1 = User.objects.create_user(username='booker1', password='pwd')
        booking_user2 = User.objects.create_user(username='booker2', password='pwd')
        booking_user3 = User.objects.create_user(username='booker3', password='pwd')
        booking_user4 = User.objects.create_user(username='booker4', password='pwd')


        Booking.objects.create(event=self.event, user=booking_user1, number_of_tickets=2, status=Booking.BookingStatus.CONFIRMED)
        Booking.objects.create(event=self.event, user=booking_user2, number_of_tickets=3, status=Booking.BookingStatus.PENDING_PAYMENT)
        Booking.objects.create(event=self.event, user=booking_user3, number_of_tickets=1, status=Booking.BookingStatus.PENDING)
        Booking.objects.create(event=self.event, user=booking_user4, number_of_tickets=1, status=Booking.BookingStatus.CANCELLED)

        # Another event to ensure counts are specific to self.event
        other_event = Event.objects.create(
            name="Other Event", venue=self.venue, organizer=self.user,
            start_time=timezone.now(), end_time=timezone.now() + timezone.timedelta(hours=1)
        )
        Booking.objects.create(event=other_event, user=booking_user1, number_of_tickets=5, status=Booking.BookingStatus.CONFIRMED)
        Booking.objects.create(event=other_event, user=booking_user2, number_of_tickets=2, status=Booking.BookingStatus.PENDING_PAYMENT)


        # active_tickets_count should sum CONFIRMED (2) and PENDING_PAYMENT (3) for self.event
        self.assertEqual(self.event.active_tickets_count(), 5)

    def test_active_tickets_count_no_active_bookings(self):
        booking_user1 = User.objects.create_user(username='booker_pending', password='pwd')
        Booking.objects.create(event=self.event, user=booking_user1, number_of_tickets=2, status=Booking.BookingStatus.PENDING)
        Booking.objects.create(event=self.event, user=booking_user1, number_of_tickets=1, status=Booking.BookingStatus.CANCELLED)
        self.assertEqual(self.event.active_tickets_count(), 0)

    def test_event_with_zero_max_capacity(self):
        self.event.max_capacity = 0
        self.event.save()
        self.assertEqual(self.event.effective_capacity, 0)
        # Ensure active_tickets_count still works (should be 0 if capacity is 0 and no bookings made)
        self.assertEqual(self.event.active_tickets_count(), 0)

class CategoryModelTests(TestCase):
    def test_category_creation(self):
        category = Category.objects.create(name="Workshop", description="Educational workshops.")
        self.assertEqual(str(category), "Workshop")
        self.assertEqual(Category.objects.count(), 1)

    def test_category_uniqueness(self):
        Category.objects.create(name="UniqueCat")
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Category.objects.create(name="UniqueCat")

    def test_category_verbose_name_plural(self):
        self.assertEqual(str(Category._meta.verbose_name_plural), "Categories")

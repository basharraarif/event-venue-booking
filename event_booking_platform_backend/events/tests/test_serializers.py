from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from decimal import Decimal
from rest_framework.exceptions import ValidationError

from ..models import Event, Category
from ..serializers import EventSerializer, CategorySerializer
from venues.models import Venue
from bookings.models import Booking # For testing confirmed_tickets_count interaction

User = get_user_model()

class CategorySerializerTests(TestCase):
    def test_serialize_category(self):
        category = Category.objects.create(name="Music", description="Live music events")
        serializer = CategorySerializer(instance=category)
        data = serializer.data
        self.assertEqual(data['name'], "Music")
        self.assertEqual(data['description'], "Live music events")

    def test_deserialize_category_valid(self):
        data = {'name': 'Sports', 'description': 'Various sporting events'}
        serializer = CategorySerializer(data=data)
        self.assertTrue(serializer.is_valid())
        category = serializer.save()
        self.assertEqual(category.name, 'Sports')

    def test_deserialize_category_invalid_missing_name(self):
        data = {'description': 'A category without a name'}
        serializer = CategorySerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('name', serializer.errors)


class EventSerializerTests(TestCase):
    def setUp(self):
        self.user_organizer = User.objects.create_user(username='organizer', password='password')
        self.venue_default = Venue.objects.create(name='Default Venue', address='1 Main St', capacity=200, owner=self.user_organizer)
        self.category_music = Category.objects.create(name='Music')
        self.category_conference = Category.objects.create(name='Conference')

        self.event_attributes = {
            'name': 'Big Tech Conf',
            'venue': self.venue_default,
            'organizer': self.user_organizer,
            'start_time': timezone.now() + timezone.timedelta(days=10),
            'end_time': timezone.now() + timezone.timedelta(days=10, hours=5),
            'ticket_price': Decimal('99.99'),
            'status': 'upcoming',
        }
        self.event = Event.objects.create(**self.event_attributes)
        self.event.categories.add(self.category_conference)

        self.serializer_context = {'request': None} # Mock request if needed by serializer methods

    def test_serialize_event(self):
        serializer = EventSerializer(instance=self.event, context=self.serializer_context)
        data = serializer.data
        self.assertEqual(data['name'], self.event.name)
        self.assertEqual(data['venue'], self.venue_default.pk)
        self.assertEqual(data['organizer'], self.user_organizer.pk)
        self.assertIn('Conference', data['categories'])
        self.assertEqual(Decimal(data['ticket_price']), self.event.ticket_price)
        self.assertIn('effective_capacity', data)
        self.assertIn('confirmed_tickets_count', data)
        self.assertEqual(data['effective_capacity'], self.venue_default.capacity) # Assuming no event.max_capacity initially
        self.assertEqual(data['confirmed_tickets_count'], 0)


    def test_deserialize_event_valid_create(self):
        valid_data = {
            'name': 'New Year Party',
            'venue': self.venue_default.pk,
            'organizer': self.user_organizer.pk,
            'categories': ['Music'], # Pass category name for SlugRelatedField
            'start_time': timezone.now() + timezone.timedelta(days=60),
            'end_time': timezone.now() + timezone.timedelta(days=60, hours=3),
            'ticket_price': '50.00',
            'max_capacity': 150 # Event specific capacity
        }
        serializer = EventSerializer(data=valid_data, context=self.serializer_context)
        if not serializer.is_valid():
            print("Validation Errors:", serializer.errors)
        self.assertTrue(serializer.is_valid())
        event = serializer.save()
        self.assertEqual(event.name, 'New Year Party')
        self.assertEqual(event.max_capacity, 150)
        self.assertTrue(event.categories.filter(name='Music').exists())

    def test_validate_max_capacity_exceeds_venue_capacity(self):
        invalid_data = {
            'name': 'Too Big Event', 'venue': self.venue_default.pk, 'organizer': self.user_organizer.pk,
            'start_time': timezone.now() + timezone.timedelta(days=1), 'end_time': timezone.now() + timezone.timedelta(days=2),
            'ticket_price': '10.00', 'max_capacity': self.venue_default.capacity + 1
        }
        serializer = EventSerializer(data=invalid_data, context=self.serializer_context)
        self.assertFalse(serializer.is_valid())
        self.assertIn('max_capacity', serializer.errors)
        self.assertIn('cannot exceed venue capacity', serializer.errors['max_capacity'][0])

    def test_validate_max_capacity_zero_allowed(self):
        data = {
            'name': 'Zero Cap Event', 'venue': self.venue_default.pk, 'organizer': self.user_organizer.pk,
            'start_time': timezone.now() + timezone.timedelta(days=1), 'end_time': timezone.now() + timezone.timedelta(days=2),
            'ticket_price': '10.00', 'max_capacity': 0
        }
        serializer = EventSerializer(data=data, context=self.serializer_context)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        event = serializer.save()
        self.assertEqual(event.max_capacity, 0)
        self.assertEqual(event.effective_capacity, 0)


    def test_validate_max_capacity_less_than_confirmed_on_update(self):
        # Create some confirmed bookings for the event
        user1 = User.objects.create_user('booker1_cap_test', 'p1')
        user2 = User.objects.create_user('booker2_cap_test', 'p2')
        Booking.objects.create(event=self.event, user=user1, number_of_tickets=10, status=Booking.BookingStatus.CONFIRMED)
        Booking.objects.create(event=self.event, user=user2, number_of_tickets=5, status=Booking.BookingStatus.CONFIRMED)
        # Total confirmed = 15

        self.event.refresh_from_db() # Ensure event instance has latest booking data for confirmed_tickets_count()

        # Try to update max_capacity to be less than 15
        invalid_update_data = {'max_capacity': 10}
        serializer = EventSerializer(self.event, data=invalid_update_data, partial=True, context=self.serializer_context)

        self.assertFalse(serializer.is_valid())
        self.assertIn('max_capacity', serializer.errors)
        self.assertIn(f"cannot be less than already confirmed tickets ({self.event.confirmed_tickets_count()})", serializer.errors['max_capacity'][0])

    def test_validate_max_capacity_equal_to_confirmed_on_update_allowed(self):
        user1 = User.objects.create_user('booker3_cap_test', 'p3')
        Booking.objects.create(event=self.event, user=user1, number_of_tickets=20, status=Booking.BookingStatus.CONFIRMED)
        self.event.refresh_from_db()

        valid_update_data = {'max_capacity': 20} # Confirmed is 20
        serializer = EventSerializer(self.event, data=valid_update_data, partial=True, context=self.serializer_context)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        self.event.refresh_from_db()
        self.assertEqual(self.event.max_capacity, 20)


    def test_validate_end_time_before_start_time(self):
        invalid_data = {
            'name': 'Time Travel Meetup', 'venue': self.venue_default.pk, 'organizer': self.user_organizer.pk,
            'start_time': timezone.now() + timezone.timedelta(days=2),
            'end_time': timezone.now() + timezone.timedelta(days=1), # End before start
            'ticket_price': '10.00'
        }
        serializer = EventSerializer(data=invalid_data, context=self.serializer_context)
        self.assertFalse(serializer.is_valid())
        self.assertIn('end_time', serializer.errors)
        self.assertIn('End time must be after start time', serializer.errors['end_time'][0])

    def test_read_only_fields_in_serializer(self):
        serializer = EventSerializer(instance=self.event, context=self.serializer_context)
        data = serializer.data
        self.assertEqual(data['effective_capacity'], self.event.effective_capacity)
        self.assertEqual(data['confirmed_tickets_count'], self.event.confirmed_tickets_count())
        self.assertEqual(data['organizer_username'], self.event.organizer.username)
        self.assertEqual(data['venue_name'], self.event.venue.name)
        # Attempting to write to these fields should be ignored or raise error depending on serializer setup
        # For ReadOnlyField, they are simply not used for deserialization.
        update_data = {
            'effective_capacity': 5000,
            'confirmed_tickets_count': 1000,
            'organizer_username': 'new_org', # This is not a writable field
        }
        update_serializer = EventSerializer(self.event, data=update_data, partial=True, context=self.serializer_context)
        self.assertTrue(update_serializer.is_valid()) # It will be valid as read-only fields are ignored
        update_serializer.save()
        self.event.refresh_from_db()
        self.assertNotEqual(self.event.effective_capacity, 5000) # Should not have changed
        # organizer_username is derived, so can't be "changed" directly via serializer input
        self.assertEqual(self.event.organizer.username, self.user_organizer.username)

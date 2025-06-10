from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import timedelta
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from .models import Event, Category
from .serializers import EventSerializer, CategorySerializer
from venues.models import Venue # Assuming Venue model is in venues.models

User = get_user_model()

class CategoryModelTests(APITestCase):
    def test_create_category(self):
        category = Category.objects.create(name="Music", description="Live music events")
        self.assertEqual(category.name, "Music")
        self.assertEqual(category.description, "Live music events")
        self.assertEqual(str(category), "Music")

class EventModelTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testorganizer', password='password123')
        self.venue = Venue.objects.create(name='Test Venue', address='123 Main St', capacity=100)
        self.category = Category.objects.create(name='Conference')
        self.now = timezone.now()

    def test_create_event(self):
        event = Event.objects.create(
            name="Tech Conference 2024",
            venue=self.venue,
            organizer=self.user,
            start_time=self.now + timedelta(days=10),
            end_time=self.now + timedelta(days=11),
            status='upcoming'
        )
        event.categories.add(self.category)
        self.assertEqual(event.name, "Tech Conference 2024")
        self.assertEqual(event.organizer, self.user)
        self.assertIn(self.category, event.categories.all())
        self.assertEqual(str(event), "Tech Conference 2024")

    def test_event_time_validation(self):
        with self.assertRaises(ValidationError) as context:
            event = Event(
                name="Invalid Event",
                venue=self.venue,
                organizer=self.user,
                start_time=self.now + timedelta(days=10),
                end_time=self.now + timedelta(days=9) # End time before start time
            )
            event.full_clean() # This calls the model's clean() method
        self.assertIn('end_time', context.exception.message_dict)


class CategorySerializerTests(APITestCase):
    def test_serialize_category(self):
        category = Category.objects.create(name="Sports", description="Sporting events")
        serializer = CategorySerializer(instance=category)
        expected_data = {
            'id': category.id,
            'name': "Sports",
            'description': "Sporting events"
        }
        self.assertEqual(serializer.data, expected_data)

    def test_deserialize_category(self):
        data = {'name': 'Workshop', 'description': 'Educational workshops'}
        serializer = CategorySerializer(data=data)
        self.assertTrue(serializer.is_valid())
        category = serializer.save()
        self.assertEqual(category.name, 'Workshop')


class EventSerializerTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='eventserializeruser', password='password')
        self.venue = Venue.objects.create(name='Serializer Venue', address='1 Test Rd', capacity=50)
        self.category1 = Category.objects.create(name='Music Concert')
        self.category2 = Category.objects.create(name='Festival')
        self.now = timezone.now()
        self.event_attributes = {
            'name': 'Big Summer Festival',
            'venue': self.venue,
            'organizer': self.user,
            'start_time': self.now + timedelta(days=30),
            'end_time': self.now + timedelta(days=31),
            'status': 'upcoming',
        }
        self.event = Event.objects.create(**self.event_attributes)
        self.event.categories.set([self.category1, self.category2])

    def test_serialize_event(self):
        serializer = EventSerializer(instance=self.event)
        data = serializer.data
        self.assertEqual(data['name'], self.event.name)
        self.assertEqual(data['venue'], self.venue.id)
        self.assertEqual(data['venue_name'], self.venue.name)
        self.assertEqual(data['organizer'], self.user.id)
        self.assertEqual(data['organizer_username'], self.user.username)
        self.assertCountEqual(data['categories'], [self.category1.name, self.category2.name]) # Due to SlugRelatedField

    def test_deserialize_event(self):
        new_venue = Venue.objects.create(name="Another Venue", address="Different St", capacity=10)
        new_organizer = User.objects.create_user(username="neworg", password="pwd")

        data = {
            'name': 'New Year Party',
            'venue': new_venue.id,
            'organizer': new_organizer.id,
            'categories': [self.category1.name, self.category2.name], # Using names due to SlugRelatedField
            'start_time': (self.now + timedelta(days=5)).isoformat(),
            'end_time': (self.now + timedelta(days=6)).isoformat(),
            'status': 'upcoming',
            'description': 'A cool new party'
        }
        serializer = EventSerializer(data=data)
        if not serializer.is_valid():
            print("Serializer errors:", serializer.errors) # Debugging
        self.assertTrue(serializer.is_valid())
        event = serializer.save()
        self.assertEqual(event.name, 'New Year Party')
        self.assertEqual(event.venue, new_venue)
        self.assertCountEqual(list(event.categories.all()), [self.category1, self.category2])

    def test_event_serializer_time_validation(self):
        data = {
            'name': 'Invalid Time Event',
            'venue': self.venue.id,
            'organizer': self.user.id,
            'categories': [self.category1.name],
            'start_time': (self.now + timedelta(days=5)).isoformat(),
            'end_time': (self.now + timedelta(days=4)).isoformat(), # End time before start - corrected typo daysAYS
            'status': 'upcoming'
        }
        serializer = EventSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('end_time', serializer.errors)


class BaseViewSetTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_superuser('admin_events', 'adminevents@example.com', 'adminpass')
        self.regular_user = User.objects.create_user('user_events', 'userevents@example.com', 'userpass')
        self.venue1 = Venue.objects.create(name='Venue One', address='Addr 1', capacity=100)
        self.venue2 = Venue.objects.create(name='Venue Two', address='Addr 2', capacity=200)
        self.cat_music = Category.objects.create(name='Music Test')
        self.cat_sports = Category.objects.create(name='Sports Test')

        self.now = timezone.now()
        self.event1 = Event.objects.create(
            name='Music Event Alpha', venue=self.venue1, organizer=self.regular_user,
            start_time=self.now + timedelta(days=10), end_time=self.now + timedelta(days=11), status='upcoming'
        )
        self.event1.categories.add(self.cat_music)

        self.event2 = Event.objects.create(
            name='Sports Event Beta', venue=self.venue2, organizer=self.admin_user,
            start_time=self.now + timedelta(days=20), end_time=self.now + timedelta(days=21), status='upcoming'
        )
        self.event2.categories.add(self.cat_sports)

        self.event3 = Event.objects.create(
            name='Music Festival Gamma', venue=self.venue1, organizer=self.admin_user,
            start_time=self.now + timedelta(days=5), end_time=self.now + timedelta(days=6), status='ongoing'
        )
        self.event3.categories.add(self.cat_music, self.cat_sports)


class CategoryViewSetTests(BaseViewSetTests):
    def test_list_categories_unauthenticated(self):
        response = self.client.get(reverse('category-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2) # cat_music, cat_sports

    def test_retrieve_category_authenticated(self):
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get(reverse('category-detail', kwargs={'pk': self.cat_music.pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.cat_music.name)

    def test_create_category_admin(self):
        self.client.force_authenticate(user=self.admin_user)
        data = {'name': 'Conference Test', 'description': 'Test conferences'}
        response = self.client.post(reverse('category-list'), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Category.objects.count(), 3)

    def test_create_category_non_admin_forbidden(self):
        self.client.force_authenticate(user=self.regular_user)
        data = {'name': 'Forbidden Category'}
        response = self.client.post(reverse('category-list'), data)
        # DjangoModelPermissionsOrAnonReadOnly means user needs 'add_category' permission
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_category_admin(self):
        self.client.force_authenticate(user=self.admin_user)
        data = {'description': 'Updated music description'}
        response = self.client.patch(reverse('category-detail', kwargs={'pk': self.cat_music.pk}), data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.cat_music.refresh_from_db()
        self.assertEqual(self.cat_music.description, 'Updated music description')

    def test_delete_category_admin(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.delete(reverse('category-detail', kwargs={'pk': self.cat_music.pk}))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Category.objects.count(), 1)


class EventViewSetTests(BaseViewSetTests):
    def test_list_events_unauthenticated(self):
        response = self.client.get(reverse('event-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3) # event1, event2, event3

    def test_retrieve_event_authenticated(self):
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get(reverse('event-detail', kwargs={'pk': self.event1.pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.event1.name)

    def test_create_event_admin(self):
        self.client.force_authenticate(user=self.admin_user)
        data = {
            'name': 'Admin Created Event',
            'venue': self.venue1.id,
            'organizer': self.admin_user.id,
            'categories': [self.cat_music.name],
            'start_time': (self.now + timedelta(days=1)).isoformat(),
            'end_time': (self.now + timedelta(days=2)).isoformat(),
            'status': 'upcoming'
        }
        response = self.client.post(reverse('event-list'), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Event.objects.count(), 4)

    def test_create_event_regular_user_with_permission(self):
        # This test assumes regular_user might be granted 'add_event' permission.
        # For now, let's assume they don't have it by default.
        self.client.force_authenticate(user=self.regular_user)
        data = {
            'name': 'User Created Event', 'venue': self.venue1.id, 'organizer': self.regular_user.id,
            'categories': [self.cat_music.name], 'start_time': (self.now + timedelta(days=3)).isoformat(),
            'end_time': (self.now + timedelta(days=4)).isoformat(), 'status': 'upcoming'
        }
        response = self.client.post(reverse('event-list'), data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) # Expect forbidden

    # Filtering Tests
    def test_filter_event_by_name(self):
        response = self.client.get(reverse('event-list') + '?name=Alpha')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], self.event1.name)

    def test_filter_event_by_venue_id(self):
        response = self.client.get(reverse('event-list') + f'?venue={self.venue2.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], self.event2.name)

    def test_filter_event_by_organizer_id(self):
        response = self.client.get(reverse('event-list') + f'?organizer={self.regular_user.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], self.event1.name)

    def test_filter_event_by_status(self):
        response = self.client.get(reverse('event-list') + '?status=ongoing')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], self.event3.name)

    def test_filter_event_by_category_name(self):
        response = self.client.get(reverse('event-list') + f'?category_name={self.cat_sports.name}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2) # event2, event3
        names = {item['name'] for item in response.data}
        self.assertIn(self.event2.name, names)
        self.assertIn(self.event3.name, names)

    def test_filter_event_start_time_after(self):
        # Events starting on or after 15 days from now (event2)
        date_filter_val = (self.now + timedelta(days=15)).strftime('%Y-%m-%d')
        response = self.client.get(reverse('event-list') + f'?start_time_after={date_filter_val}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], self.event2.name)

    def test_filter_event_start_time_before(self):
        # Events starting on or before 15 days from now (event1, event3)
        date_filter_val = (self.now + timedelta(days=15)).strftime('%Y-%m-%d')
        response = self.client.get(reverse('event-list') + f'?start_time_before={date_filter_val}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        names = {item['name'] for item in response.data}
        self.assertIn(self.event1.name, names)
        self.assertIn(self.event3.name, names)

    def test_update_event_organizer_or_admin(self):
        # Test if organizer (regular_user) can update their own event (event1)
        self.client.force_authenticate(user=self.regular_user)
        data = {'description': 'Updated by organizer'}
        # This will fail with 403 if regular_user doesn't have 'change_event' permission
        # For this test to pass with 200, user needs explicit 'change_event' or object-level permission.
        # Default DjangoModelPermissionsOrAnonReadOnly + no explicit perm = 403.
        response = self.client.patch(reverse('event-detail', kwargs={'pk': self.event1.pk}), data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Test admin can update any event
        self.client.force_authenticate(user=self.admin_user)
        admin_data = {'description': 'Updated by admin'}
        response_admin = self.client.patch(reverse('event-detail', kwargs={'pk': self.event1.pk}), admin_data)
        self.assertEqual(response_admin.status_code, status.HTTP_200_OK)
        self.event1.refresh_from_db()
        self.assertEqual(self.event1.description, 'Updated by admin')

    def test_delete_event_admin(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.delete(reverse('event-detail', kwargs={'pk': self.event1.pk}))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Event.objects.count(), 2)

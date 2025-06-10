from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import timedelta
from decimal import Decimal # Import Decimal
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
        # Create users with specific roles
        self.organizer_user = User.objects.create_user('organizer_user', 'organizer@example.com', 'orgpass', roles=User.Roles.ORGANIZER)
        self.customer_user = User.objects.create_user('customer_user', 'customer@example.com', 'custpass', roles=User.Roles.CUSTOMER)

        # Assign owner to venue for consistency if Venue model requires it (it does now)
        self.venue_owner = User.objects.create_user('venue_owner_for_events', 'vo_events@example.com', 'vopass')
        self.venue1 = Venue.objects.create(name='Venue One', address='Addr 1', capacity=100, owner=self.venue_owner)
        self.venue2 = Venue.objects.create(name='Venue Two', address='Addr 2', capacity=200, owner=self.venue_owner)
        self.cat_music = Category.objects.create(name='Music Test')
        self.cat_sports = Category.objects.create(name='Sports Test')

        self.now = timezone.now()
        # Event organized by the organizer_user
        self.event_by_organizer = Event.objects.create(
            name='Event by Organizer', venue=self.venue1, organizer=self.organizer_user,
            start_time=self.now + timedelta(days=10), end_time=self.now + timedelta(days=11), status='upcoming', ticket_price=Decimal("50.00")
        )
        self.event_by_organizer.categories.add(self.cat_music)

        # Event organized by admin_user
        self.event_by_admin = Event.objects.create(
            name='Event by Admin', venue=self.venue2, organizer=self.admin_user,
            start_time=self.now + timedelta(days=20), end_time=self.now + timedelta(days=21), status='upcoming', ticket_price=Decimal("60.00")
        )
        self.event_by_admin.categories.add(self.cat_sports)

        # Another event for list count checks
        self.event3 = Event.objects.create(
            name='Music Festival Gamma', venue=self.venue1, organizer=self.admin_user, # Keep organizer as admin for simplicity here
            start_time=self.now + timedelta(days=5), end_time=self.now + timedelta(days=6), status='ongoing', ticket_price=Decimal("70.00")
        )
        self.event3.categories.add(self.cat_music, self.cat_sports)



class CategoryViewSetTests(BaseViewSetTests):
    def test_list_categories_unauthenticated(self):
        response = self.client.get(reverse('category-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2) # cat_music, cat_sports

    def test_retrieve_category_authenticated(self):
        self.client.force_authenticate(user=self.customer_user) # Any authenticated user can retrieve
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
        self.client.force_authenticate(user=self.customer_user) # Customer cannot create categories
        data = {'name': 'Forbidden Category'}
        response = self.client.post(reverse('category-list'), data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_category_admin(self): # Admin can update
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
        self.assertEqual(len(response.data), 3)

    def test_retrieve_event_authenticated(self):
        self.client.force_authenticate(user=self.customer_user) # Any authenticated user can retrieve
        response = self.client.get(reverse('event-detail', kwargs={'pk': self.event_by_organizer.pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.event_by_organizer.name)

    def test_create_event_as_organizer(self):
        self.client.force_authenticate(user=self.organizer_user)
        data = {
            'name': 'Organizer Created Event', 'venue': self.venue1.id, 'organizer': self.organizer_user.id,
            'categories': [self.cat_music.name], 'start_time': (self.now + timedelta(days=1)).isoformat(),
            'end_time': (self.now + timedelta(days=2)).isoformat(), 'status': 'upcoming', 'ticket_price': Decimal("30.00")
        }
        response = self.client.post(reverse('event-list'), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Event.objects.count(), 4) # 3 initial + 1 new

    def test_create_event_as_customer_forbidden(self):
        self.client.force_authenticate(user=self.customer_user)
        data = {
            'name': 'Customer Created Event', 'venue': self.venue1.id, 'organizer': self.customer_user.id,
            'categories': [self.cat_music.name], 'start_time': (self.now + timedelta(days=3)).isoformat(),
            'end_time': (self.now + timedelta(days=4)).isoformat(), 'status': 'upcoming', 'ticket_price': Decimal("30.00")
        }
        response = self.client.post(reverse('event-list'), data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_own_event_as_organizer(self):
        self.client.force_authenticate(user=self.organizer_user)
        data = {'description': 'Updated by organizer owner'}
        response = self.client.patch(reverse('event-detail', kwargs={'pk': self.event_by_organizer.pk}), data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.event_by_organizer.refresh_from_db()
        self.assertEqual(self.event_by_organizer.description, 'Updated by organizer owner')

    def test_update_other_event_as_organizer_forbidden(self):
        # self.event_by_admin is organized by admin_user
        self.client.force_authenticate(user=self.organizer_user)
        data = {'description': 'Attempt to update other event'}
        response = self.client.patch(reverse('event-detail', kwargs={'pk': self.event_by_admin.pk}), data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_event_as_admin(self):
        self.client.force_authenticate(user=self.admin_user)
        data = {'description': 'Updated by admin'}
        response = self.client.patch(reverse('event-detail', kwargs={'pk': self.event_by_organizer.pk}), data) # Admin updates organizer's event
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.event_by_organizer.refresh_from_db()
        self.assertEqual(self.event_by_organizer.description, 'Updated by admin')

    def test_delete_own_event_as_organizer(self):
        self.client.force_authenticate(user=self.organizer_user)
        response = self.client.delete(reverse('event-detail', kwargs={'pk': self.event_by_organizer.pk}))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Event.objects.count(), 2) # 3 initial - 1 deleted

    def test_delete_other_event_as_organizer_forbidden(self):
        self.client.force_authenticate(user=self.organizer_user)
        response = self.client.delete(reverse('event-detail', kwargs={'pk': self.event_by_admin.pk}))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_event_as_customer_forbidden(self):
        self.client.force_authenticate(user=self.customer_user)
        response = self.client.delete(reverse('event-detail', kwargs={'pk': self.event_by_organizer.pk}))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # Filtering Tests (copied and adapted, ensure they still make sense with new events)
    def test_filter_event_by_name(self):
        response = self.client.get(reverse('event-list') + '?name=Organizer') # Event by Organizer
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], self.event_by_organizer.name)

    def test_filter_event_by_venue_id(self):
        response = self.client.get(reverse('event-list') + f'?venue={self.venue2.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], self.event_by_admin.name)

    def test_filter_event_by_organizer_id(self):
        response = self.client.get(reverse('event-list') + f'?organizer={self.organizer_user.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], self.event_by_organizer.name)

    def test_filter_event_by_status(self):
        response = self.client.get(reverse('event-list') + '?status=ongoing')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], self.event3.name)

    def test_filter_event_by_category_name(self):
        response = self.client.get(reverse('event-list') + f'?category_name={self.cat_sports.name}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        names = {item['name'] for item in response.data}
        self.assertIn(self.event_by_admin.name, names)
        self.assertIn(self.event3.name, names)

    def test_filter_event_start_time_after(self):
        date_filter_val = (self.now + timedelta(days=15)).strftime('%Y-%m-%d') # event_by_admin
        response = self.client.get(reverse('event-list') + f'?start_time_after={date_filter_val}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], self.event_by_admin.name)

    def test_filter_event_start_time_before(self):
        date_filter_val = (self.now + timedelta(days=15)).strftime('%Y-%m-%d') # event_by_organizer, event3
        response = self.client.get(reverse('event-list') + f'?start_time_before={date_filter_val}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        names = {item['name'] for item in response.data}
        self.assertIn(self.event_by_organizer.name, names)
        self.assertIn(self.event3.name, names)

    # test_update_event_organizer_or_admin is now split into more specific tests above
    # Old test_delete_event_admin is covered by admin's ability to delete any event (implicitly tested if not specifically denied)
    # or can be specific:
    def test_admin_can_delete_any_event(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.delete(reverse('event-detail', kwargs={'pk': self.event_by_organizer.pk}))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Event.objects.filter(pk=self.event_by_organizer.pk).exists())

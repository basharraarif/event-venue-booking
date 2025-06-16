from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from mixer.backend.django import mixer
from decimal import Decimal

from events.models import Event, Category
from venues.models import Venue
from core.models import Role # For creating users with specific roles

User = get_user_model()

class EventFilterSetTests(APITestCase):
    def setUp(self):
        # Users
        self.organizer1 = User.objects.create_user(username='event_org1_filter', password='password')
        self.organizer2 = User.objects.create_user(username='event_org2_filter', password='password')
        self.viewer_user = User.objects.create_user(username='event_viewer_filter', password='password')

        # Roles (optional here if not testing role-specific filter access, but good for consistency)
        # organizer_role, _ = Role.objects.get_or_create(name='EVENT_ORGANIZER')
        # self.organizer1.roles.add(organizer_role)
        # self.organizer2.roles.add(organizer_role)

        # Venue
        self.venue1 = mixer.blend(Venue, name="Venue Alpha for Events", capacity=100, owner=self.organizer1)
        self.venue2 = mixer.blend(Venue, name="Venue Beta for Events", capacity=200, owner=self.organizer2)

        # Categories
        self.cat_music = mixer.blend(Category, name="Music")
        self.cat_tech = mixer.blend(Category, name="Technology")
        self.cat_sports = mixer.blend(Category, name="Sports")

        # Events
        self.event1 = Event.objects.create(
            name="Tech Conference 2024", venue=self.venue1, organizer=self.organizer1,
            start_time=timezone.make_aware(timezone.datetime(2024, 10, 15, 9, 0)),
            end_time=timezone.make_aware(timezone.datetime(2024, 10, 17, 17, 0)),
            status='upcoming', ticket_price=Decimal('299.99')
        )
        self.event1.categories.add(self.cat_tech)

        self.event2 = Event.objects.create(
            name="Music Fest Weekend", venue=self.venue2, organizer=self.organizer2,
            start_time=timezone.make_aware(timezone.datetime(2024, 11, 1, 18, 0)),
            end_time=timezone.make_aware(timezone.datetime(2024, 11, 3, 23, 0)),
            status='upcoming', ticket_price=Decimal('150.00')
        )
        self.event2.categories.add(self.cat_music)

        self.event3 = Event.objects.create(
            name="Old Tech Meetup", venue=self.venue1, organizer=self.organizer1,
            start_time=timezone.make_aware(timezone.datetime(2023, 5, 10, 14, 0)),
            end_time=timezone.make_aware(timezone.datetime(2023, 5, 10, 16, 0)),
            status='past', ticket_price=Decimal('25.00')
        )
        self.event3.categories.add(self.cat_tech)

        self.event4_ongoing = Event.objects.create(
            name="Ongoing Workshop", venue=self.venue2, organizer=self.organizer2,
            start_time=timezone.now() - timezone.timedelta(hours=2),
            end_time=timezone.now() + timezone.timedelta(hours=2),
            status='ongoing', ticket_price=Decimal('75.50')
        )
        self.event4_ongoing.categories.add(self.cat_tech, self.cat_music)


        self.list_url = reverse("event-list")
        self.client.force_authenticate(user=self.viewer_user) # Default user for requests

    def test_filter_name(self):
        response = self.client.get(self.list_url, {'name': 'Tech'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2) # Tech Conference 2024, Old Tech Meetup
        names = {item['name'] for item in response.data}
        self.assertIn("Tech Conference 2024", names)
        self.assertIn("Old Tech Meetup", names)

    def test_filter_venue_id(self):
        response = self.client.get(self.list_url, {'venue': self.venue1.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2) # Tech Conference, Old Tech Meetup
        for item in response.data:
            self.assertEqual(item['venue'], self.venue1.pk)

    def test_filter_organizer_id(self):
        response = self.client.get(self.list_url, {'organizer': self.organizer1.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2) # Tech Conference, Old Tech Meetup
        for item in response.data:
            self.assertEqual(item['organizer'], self.organizer1.pk)

    def test_filter_status(self):
        response = self.client.get(self.list_url, {'status': 'past'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], "Old Tech Meetup")

        response_ongoing = self.client.get(self.list_url, {'status': 'ongoing'})
        self.assertEqual(response_ongoing.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response_ongoing.data), 1)
        self.assertEqual(response_ongoing.data[0]['name'], "Ongoing Workshop")


    def test_filter_category_name(self):
        # Filter by 'Technology' category
        response = self.client.get(self.list_url, {'category_name': 'Technology'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Tech Conference 2024, Old Tech Meetup, Ongoing Workshop
        self.assertEqual(len(response.data), 3)
        names = {item['name'] for item in response.data}
        self.assertIn("Tech Conference 2024", names)
        self.assertIn("Old Tech Meetup", names)
        self.assertIn("Ongoing Workshop", names)


    def test_filter_start_time_after(self):
        # Events starting after Oct 16, 2024
        response = self.client.get(self.list_url, {'start_time_after': '2024-10-16T00:00:00Z'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1) # Music Fest Weekend (Nov 1)
        self.assertEqual(response.data[0]['name'], "Music Fest Weekend")

    def test_filter_start_time_before(self):
        # Events starting before Oct 16, 2024 (includes ongoing if its start is before)
        response = self.client.get(self.list_url, {'start_time_before': '2024-10-16T00:00:00Z'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Expected: Tech Conference (Oct 15), Old Tech Meetup (May 10, 2023), Ongoing Workshop (Now-2hrs)
        names = {item['name'] for item in response.data}
        self.assertIn("Tech Conference 2024", names)
        self.assertIn("Old Tech Meetup", names)
        self.assertIn("Ongoing Workshop", names)
        self.assertEqual(len(names), 3)


    def test_filter_ticket_price_min_and_max(self):
        # Price >= 100
        response_min = self.client.get(self.list_url, {'ticket_price_min': '100.00'})
        self.assertEqual(response_min.status_code, status.HTTP_200_OK)
        names_min = {item['name'] for item in response_min.data}
        self.assertIn("Tech Conference 2024", names_min) # 299.99
        self.assertIn("Music Fest Weekend", names_min)   # 150.00
        self.assertEqual(len(names_min), 2)

        # Price <= 80
        response_max = self.client.get(self.list_url, {'ticket_price_max': '80.00'})
        self.assertEqual(response_max.status_code, status.HTTP_200_OK)
        names_max = {item['name'] for item in response_max.data}
        self.assertIn("Old Tech Meetup", names_max)    # 25.00
        self.assertIn("Ongoing Workshop", names_max) # 75.50
        self.assertEqual(len(names_max), 2)

        # Price between 70 and 200
        response_range = self.client.get(self.list_url, {'ticket_price_min': '70.00', 'ticket_price_max': '200.00'})
        self.assertEqual(response_range.status_code, status.HTTP_200_OK)
        names_range = {item['name'] for item in response_range.data}
        self.assertIn("Music Fest Weekend", names_range) # 150.00
        self.assertIn("Ongoing Workshop", names_range) # 75.50
        self.assertEqual(len(names_range), 2)

    def test_filter_combined(self):
        # Filter by status 'upcoming' AND category 'Technology'
        response = self.client.get(self.list_url, {'status': 'upcoming', 'category_name': 'Technology'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Expected: Tech Conference 2024
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], "Tech Conference 2024")

        # Filter by name 'Fest' AND venue ID of venue2
        response_name_venue = self.client.get(self.list_url, {'name': 'Fest', 'venue': self.venue2.pk})
        self.assertEqual(response_name_venue.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response_name_venue.data), 1)
        self.assertEqual(response_name_venue.data[0]['name'], "Music Fest Weekend")

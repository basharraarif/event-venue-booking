from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from mixer.backend.django import mixer # For quick object creation
from decimal import Decimal

from bookings.models import Booking
from events.models import Event
from venues.models import Venue
from core.models import Role # For creating users with specific roles

User = get_user_model()

class BookingFilterSetTests(APITestCase):
    def setUp(self):
        # Users
        self.admin_user = User.objects.create_superuser('admin_booking_filter', 'admin_bf@example.com', 'adminpass')
        self.user1 = User.objects.create_user('user1_booking_filter', 'u1_bf@example.com', 'userpass')
        self.user2 = User.objects.create_user('user2_booking_filter', 'u2_bf@example.com', 'userpass')

        # Venue and Events
        self.venue = mixer.blend(Venue, owner=self.admin_user)
        self.event1 = mixer.blend(Event, venue=self.venue, organizer=self.admin_user,
                                  start_time=timezone.now() + timezone.timedelta(days=10),
                                  ticket_price=Decimal('50.00'))
        self.event2 = mixer.blend(Event, venue=self.venue, organizer=self.admin_user,
                                  start_time=timezone.now() + timezone.timedelta(days=20),
                                  ticket_price=Decimal('30.00'))

        # Bookings
        self.booking1_user1_event1_pending = Booking.objects.create(
            event=self.event1, user=self.user1, number_of_tickets=1,
            status=Booking.BookingStatus.PENDING,
            booking_time=timezone.now() - timezone.timedelta(days=5)
        )
        self.booking2_user1_event2_confirmed = Booking.objects.create(
            event=self.event2, user=self.user1, number_of_tickets=2,
            status=Booking.BookingStatus.CONFIRMED,
            booking_time=timezone.now() - timezone.timedelta(days=2)
        )
        self.booking3_user2_event1_cancelled = Booking.objects.create(
            event=self.event1, user=self.user2, number_of_tickets=3,
            status=Booking.BookingStatus.CANCELLED,
            booking_time=timezone.now() - timezone.timedelta(days=10)
        )
        self.booking4_user2_event2_pending = Booking.objects.create(
            event=self.event2, user=self.user2, number_of_tickets=4,
            status=Booking.BookingStatus.PENDING,
            booking_time=timezone.now() - timezone.timedelta(days=1)
        )

        self.list_url = reverse("booking-list") # Assuming 'booking-list' is the name for BookingViewSet list action

    # --- Admin User Tests ---
    def test_admin_filter_by_user_id(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.list_url, {'user': self.user1.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2) # booking1, booking2 for user1
        for booking_data in response.data:
            self.assertEqual(booking_data['user_details']['id'], self.user1.pk)

    def test_admin_filter_by_event_id(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.list_url, {'event': self.event1.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2) # booking1, booking3 for event1
        for booking_data in response.data:
            self.assertEqual(booking_data['event_details']['id'], self.event1.pk)

    def test_admin_filter_by_status(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.list_url, {'status': Booking.BookingStatus.PENDING})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2) # booking1, booking4 are pending
        for booking_data in response.data:
            self.assertEqual(booking_data['status'], Booking.BookingStatus.PENDING)

    def test_admin_filter_booking_time_after(self):
        self.client.force_authenticate(user=self.admin_user)
        # Filter bookings made after 3 days ago (should include booking2 and booking4)
        time_threshold = timezone.now() - timezone.timedelta(days=3)
        response = self.client.get(self.list_url, {'booking_time_after': time_threshold.isoformat()})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        booking_ids = {b['id'] for b in response.data}
        self.assertIn(self.booking2_user1_event2_confirmed.id, booking_ids)
        self.assertIn(self.booking4_user2_event2_pending.id, booking_ids)

    def test_admin_filter_booking_time_before(self):
        self.client.force_authenticate(user=self.admin_user)
        # Filter bookings made before 3 days ago (should include booking1 and booking3)
        time_threshold = timezone.now() - timezone.timedelta(days=3)
        response = self.client.get(self.list_url, {'booking_time_before': time_threshold.isoformat()})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        booking_ids = {b['id'] for b in response.data}
        self.assertIn(self.booking1_user1_event1_pending.id, booking_ids)
        self.assertIn(self.booking3_user2_event1_cancelled.id, booking_ids)

    # --- Regular User Tests (user1) ---
    def test_regular_user_sees_only_own_bookings(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2) # booking1, booking2 for user1
        for booking_data in response.data:
            self.assertEqual(booking_data['user_details']['id'], self.user1.pk)

    def test_regular_user_cannot_filter_by_other_user_id(self):
        self.client.force_authenticate(user=self.user1)
        # Attempting to filter by user2's ID should still only return user1's bookings
        response = self.client.get(self.list_url, {'user': self.user2.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2) # Still only user1's bookings
        for booking_data in response.data:
            self.assertEqual(booking_data['user_details']['id'], self.user1.pk)


    def test_regular_user_filter_by_event_id(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.list_url, {'event': self.event1.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1) # Only booking1_user1_event1
        self.assertEqual(response.data[0]['id'], self.booking1_user1_event1_pending.id)

    def test_regular_user_filter_by_status(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.list_url, {'status': Booking.BookingStatus.CONFIRMED})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1) # Only booking2_user1_event2_confirmed
        self.assertEqual(response.data[0]['id'], self.booking2_user1_event2_confirmed.id)

    def test_regular_user_filter_booking_time_after(self):
        self.client.force_authenticate(user=self.user1)
        # booking_time for user1: booking1 (5 days ago), booking2 (2 days ago)
        time_threshold = timezone.now() - timezone.timedelta(days=3) # After 3 days ago -> booking2
        response = self.client.get(self.list_url, {'booking_time_after': time_threshold.isoformat()})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.booking2_user1_event2_confirmed.id)

    def test_regular_user_filter_booking_time_before(self):
        self.client.force_authenticate(user=self.user1)
        time_threshold = timezone.now() - timezone.timedelta(days=3) # Before 3 days ago -> booking1
        response = self.client.get(self.list_url, {'booking_time_before': time_threshold.isoformat()})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.booking1_user1_event1_pending.id)

from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from .models import Booking
from events.models import Event, Category
from venues.models import Venue
from .serializers import BookingSerializer

User = get_user_model()

class BookingModelTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testbooker', password='password123')
        self.venue = Venue.objects.create(name='Test Venue for Booking', address='123 Booking St', capacity=100)
        self.event = Event.objects.create(
            name="Test Event for Booking",
            venue=self.venue,
            organizer=self.user, # Assuming an event needs an organizer
            start_time=timezone.now() + timezone.timedelta(days=10),
            end_time=timezone.now() + timezone.timedelta(days=11),
            ticket_price=Decimal('25.00')
        )

    def test_create_booking_calculates_total_price(self):
        booking = Booking.objects.create(
            event=self.event,
            user=self.user,
            number_of_tickets=3
        )
        self.assertEqual(booking.total_price, Decimal('75.00')) # 3 * 25.00
        self.assertEqual(str(booking), f"Booking for {self.event.name} by {self.user.username} (3 tickets)")

    def test_booking_number_of_tickets_validation(self):
        with self.assertRaises(ValidationError) as context:
            booking = Booking(
                event=self.event,
                user=self.user,
                number_of_tickets=0
            )
            booking.full_clean() # This calls the model's clean() method
        self.assertIn('number_of_tickets', context.exception.message_dict)

    def test_total_price_recalculation_on_update(self):
        booking = Booking.objects.create(event=self.event, user=self.user, number_of_tickets=2)
        self.assertEqual(booking.total_price, Decimal('50.00'))

        booking.number_of_tickets = 4
        booking.save()
        self.assertEqual(booking.total_price, Decimal('100.00'))

        # Test if event price changes, existing booking price does NOT change unless explicitly recalculated
        # This depends on desired behavior. Current save method recalculates based on current event price.
        self.event.ticket_price = Decimal('30.00')
        self.event.save()
        booking.save() # Re-saving booking will use new event price.
        self.assertEqual(booking.total_price, Decimal('120.00')) # 4 * 30.00


class BookingSerializerTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='booking_serializer_user', password='password')
        self.venue = Venue.objects.create(name='Booking Serializer Venue', address='1 Test Rd', capacity=50)
        self.event = Event.objects.create(
            name='Event for BookingSerializer', venue=self.venue, organizer=self.user,
            start_time=timezone.now() + timezone.timedelta(days=5),
            end_time=timezone.now() + timezone.timedelta(days=6),
            ticket_price=Decimal('10.00'), status='upcoming'
        )
        self.booking_attributes = {
            'event': self.event,
            'user': self.user,
            'number_of_tickets': 2,
        }
        self.booking = Booking.objects.create(**self.booking_attributes)

    def test_serialize_booking(self):
        serializer = BookingSerializer(instance=self.booking)
        data = serializer.data
        self.assertEqual(data['id'], self.booking.id)
        self.assertEqual(data['number_of_tickets'], 2)
        self.assertEqual(Decimal(data['total_price']), Decimal('20.00'))
        self.assertIsNotNone(data['booking_time'])
        self.assertEqual(data['status'], 'pending') # Default status
        self.assertEqual(data['event'], self.event.id) # Writable field
        self.assertEqual(data['event_details']['name'], self.event.name) # Read-only nested
        self.assertEqual(data['user'], self.user.id) # Writable field
        self.assertEqual(data['user_details']['username'], self.user.username) # Read-only nested

    def test_deserialize_booking_creation(self):
        other_user = User.objects.create_user(username='otherbooker', password='pwd')
        data = {
            'event': self.event.id,
            # 'user' field will be set by perform_create in ViewSet, not passed directly for create
            'number_of_tickets': 4,
            'status': 'confirmed' # User might try to set this, but view might override/ignore
        }
        # When testing serializer directly, 'user' must be provided if not read_only in serializer itself
        # However, BookingViewSet.perform_create sets it.
        # For direct serializer test for create, 'user' is read-only in the serializer input,
        # so it must be passed to the save() method, similar to how perform_create works.

        data_for_input = {
            'event': self.event.id,
            'number_of_tickets': 4,
            'status': 'confirmed'
        }
        create_serializer = BookingSerializer(data=data_for_input)

        if not create_serializer.is_valid():
            print("Serializer errors for test_deserialize_booking_creation:", create_serializer.errors) # Debugging
        self.assertTrue(create_serializer.is_valid())

        # Mimic perform_create: pass user to serializer's save method
        booking = create_serializer.save(user=other_user)
        self.assertEqual(booking.user, other_user)
        self.assertEqual(booking.number_of_tickets, 4)
        self.assertEqual(booking.total_price, Decimal('40.00')) # 4 * 10.00
        self.assertEqual(booking.status, 'confirmed') # Serializer allows setting status

    def test_booking_serializer_validation(self):
        # Test number_of_tickets validation
        data_invalid_tickets = {'event': self.event.id, 'user': self.user.id, 'number_of_tickets': 0}
        serializer_invalid_tickets = BookingSerializer(data=data_invalid_tickets)
        self.assertFalse(serializer_invalid_tickets.is_valid())
        self.assertIn('number_of_tickets', serializer_invalid_tickets.errors)

        # Test event status validation (e.g. cannot book for 'past' events)
        self.event.status = 'past'
        self.event.save()
        data_past_event = {'event': self.event.id, 'user': self.user.id, 'number_of_tickets': 1}
        serializer_past_event = BookingSerializer(data=data_past_event)
        self.assertFalse(serializer_past_event.is_valid())
        self.assertIn('non_field_errors', serializer_past_event.errors) # From validate() method
        self.event.status = 'upcoming' # Reset for other tests
        self.event.save()


class BookingViewSetTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_superuser('admin_bookings', 'adminbookings@example.com', 'adminpass')
        self.user1 = User.objects.create_user('booker1', 'booker1@example.com', 'userpass1')
        self.user2 = User.objects.create_user('booker2', 'booker2@example.com', 'userpass2')

        self.venue = Venue.objects.create(name='Booking ViewSet Venue', address='Addr', capacity=100)
        self.event1 = Event.objects.create(
            name='Event One Booking', venue=self.venue, organizer=self.admin_user,
            start_time=timezone.now() + timezone.timedelta(days=1),
            end_time=timezone.now() + timezone.timedelta(days=2),
            ticket_price=Decimal('50.00'), status='upcoming'
        )
        self.event2 = Event.objects.create(
            name='Event Two Booking', venue=self.venue, organizer=self.admin_user,
            start_time=timezone.now() + timezone.timedelta(days=3),
            end_time=timezone.now() + timezone.timedelta(days=4),
            ticket_price=Decimal('20.00'), status='upcoming'
        )

        self.booking1_user1 = Booking.objects.create(event=self.event1, user=self.user1, number_of_tickets=1) # 50.00
        self.booking2_user1 = Booking.objects.create(event=self.event2, user=self.user1, number_of_tickets=2) # 40.00
        self.booking3_user2 = Booking.objects.create(event=self.event1, user=self.user2, number_of_tickets=3) # 150.00

        self.list_create_url = reverse('booking-list')

    def test_list_bookings_unauthenticated(self):
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_own_bookings_authenticated_user(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2) # booking1_user1, booking2_user1
        booking_ids = {b['id'] for b in response.data}
        self.assertIn(self.booking1_user1.id, booking_ids)
        self.assertIn(self.booking2_user1.id, booking_ids)

    def test_list_all_bookings_admin(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

    def test_retrieve_own_booking_authenticated_user(self):
        self.client.force_authenticate(user=self.user1)
        detail_url = reverse('booking-detail', kwargs={'pk': self.booking1_user1.pk})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.booking1_user1.id)

    def test_retrieve_other_users_booking_forbidden(self):
        self.client.force_authenticate(user=self.user1)
        detail_url = reverse('booking-detail', kwargs={'pk': self.booking3_user2.pk}) # booking of user2
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND) # Due to get_queryset filtering + IsOwnerOrAdmin

    def test_retrieve_any_booking_admin(self):
        self.client.force_authenticate(user=self.admin_user)
        detail_url = reverse('booking-detail', kwargs={'pk': self.booking3_user2.pk})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.booking3_user2.id)

    def test_create_booking_authenticated_user(self):
        self.client.force_authenticate(user=self.user1)
        data = {'event': self.event1.id, 'number_of_tickets': 2}
        response = self.client.post(self.list_create_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Booking.objects.count(), 4)
        new_booking = Booking.objects.get(id=response.data['id'])
        self.assertEqual(new_booking.user, self.user1) # Check user auto-assignment
        self.assertEqual(new_booking.total_price, self.event1.ticket_price * 2)

    def test_update_own_booking_user(self): # e.g. change number_of_tickets or status to 'cancelled'
        self.client.force_authenticate(user=self.user1)
        detail_url = reverse('booking-detail', kwargs={'pk': self.booking1_user1.pk})
        # Users might only be allowed to cancel, or not update confirmed bookings.
        # Current IsOwnerOrAdmin allows update of any field by owner.
        data = {'number_of_tickets': 5, 'status': 'pending'} # Assuming status can be changed by user
        response = self.client.patch(detail_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.booking1_user1.refresh_from_db()
        self.assertEqual(self.booking1_user1.number_of_tickets, 5)
        self.assertEqual(self.booking1_user1.total_price, self.event1.ticket_price * 5)

    def test_update_other_users_booking_forbidden(self):
        self.client.force_authenticate(user=self.user1)
        detail_url = reverse('booking-detail', kwargs={'pk': self.booking3_user2.pk})
        data = {'number_of_tickets': 10}
        response = self.client.patch(detail_url, data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND) # or 403 if get_object didn't use filtered queryset

    def test_delete_own_booking_user(self):
        # Assuming users can delete their 'pending' bookings
        self.booking1_user1.status = 'pending'
        self.booking1_user1.save()
        self.client.force_authenticate(user=self.user1)
        detail_url = reverse('booking-detail', kwargs={'pk': self.booking1_user1.pk})
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Booking.objects.filter(pk=self.booking1_user1.pk).exists())

    def test_delete_other_users_booking_forbidden(self):
        self.client.force_authenticate(user=self.user1)
        detail_url = reverse('booking-detail', kwargs={'pk': self.booking3_user2.pk})
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # Filtering Tests
    def test_filter_bookings_by_event_admin(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.list_create_url + f'?event={self.event1.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2) # booking1_user1, booking3_user2
        for booking_data in response.data:
            self.assertEqual(booking_data['event_details']['id'], self.event1.id)

    def test_filter_bookings_by_user_admin(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.list_create_url + f'?user={self.user1.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2) # booking1_user1, booking2_user1
        for booking_data in response.data:
            self.assertEqual(booking_data['user_details']['id'], self.user1.id)

    def test_filter_bookings_by_status_user(self): # User filters their own bookings
        self.client.force_authenticate(user=self.user1)
        self.booking1_user1.status = 'confirmed'
        self.booking1_user1.save()
        self.booking2_user1.status = 'pending'
        self.booking2_user1.save()
        response = self.client.get(self.list_create_url + '?status=confirmed')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.booking1_user1.id)

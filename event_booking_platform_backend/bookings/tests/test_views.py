from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from decimal import Decimal
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.core import mail

from bookings.models import Booking
from events.models import Event, Category
from venues.models import Venue
from payments.models import Payment # Import Payment model

User = get_user_model()

class BookingViewSetPriceSnapshottingTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user('booker_snapshot', 'snap@example.com', 'userpass1')
        self.admin_user = User.objects.create_superuser('admin_snapshot', 'adminsnap@example.com', 'adminpass')

        self.venue_owner = User.objects.create_user('venue_owner_snap', 'vos@example.com', 'vopass')
        self.venue = Venue.objects.create(name='Snapshot Test Venue', address='Addr Snap', capacity=100, owner=self.venue_owner)

        self.initial_ticket_price = Decimal('50.00')
        self.event1 = Event.objects.create(
            name='Event for Snapshot', venue=self.venue, organizer=self.admin_user,
            start_time=timezone.now() + timezone.timedelta(days=10),
            end_time=timezone.now() + timezone.timedelta(days=11),
            ticket_price=self.initial_ticket_price,
            status='upcoming',
            currency_code='USD' # Ensure event has currency for payment creation
        )
        self.list_create_url = reverse('booking-list')
        self.client.force_authenticate(user=self.user1)

    def test_create_booking_snapshots_price_and_creates_payment(self):
        data = {'event': self.event1.id, 'number_of_tickets': 2}
        response = self.client.post(self.list_create_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        new_booking = Booking.objects.get(id=response.data['id'])

        # Verify price snapshotting
        self.assertEqual(new_booking.price_per_ticket_at_booking, self.initial_ticket_price)
        self.assertEqual(new_booking.total_price, self.initial_ticket_price * 2)

        # Verify associated payment
        self.assertTrue(hasattr(new_booking, 'payment'))
        payment = new_booking.payment
        self.assertEqual(payment.amount, new_booking.total_price)
        self.assertEqual(payment.status, 'pending') # Assuming PENDING is 'pending'
        self.assertEqual(payment.currency, self.event1.currency_code)

        # Verify email (assuming booking pending email is sent on creation)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Booking Pending', mail.outbox[0].subject)

    def test_event_price_change_does_not_affect_existing_booking_price(self):
        # Create an initial booking
        booking = Booking.objects.create(
            event=self.event1, user=self.user1, number_of_tickets=1,
            price_per_ticket_at_booking=self.initial_ticket_price
        )
        # Payment would also be created by viewset, simulate it here for consistency if needed for later checks
        Payment.objects.create(booking=booking, amount=booking.total_price, status='pending')


        # Change event's ticket price
        new_event_price = Decimal('100.00')
        self.event1.ticket_price = new_event_price
        self.event1.save()

        # Retrieve the booking via API
        detail_url = reverse('booking-detail', kwargs={'pk': booking.id})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check that snapshotted price and total_price in response are unchanged
        self.assertEqual(Decimal(response.data['price_per_ticket_at_booking']), self.initial_ticket_price)
        self.assertEqual(Decimal(response.data['total_price']), self.initial_ticket_price * 1) # Original number of tickets

        # Also check model instance directly
        booking.refresh_from_db()
        self.assertEqual(booking.price_per_ticket_at_booking, self.initial_ticket_price)
        self.assertEqual(booking.total_price, self.initial_ticket_price * 1)


    def test_update_number_of_tickets_pending_payment(self):
        # Create booking and associated pending payment
        booking = Booking.objects.create(
            event=self.event1, user=self.user1, number_of_tickets=2,
            price_per_ticket_at_booking=self.initial_ticket_price
        )
        payment = Payment.objects.create(booking=booking, amount=booking.total_price, status='pending', currency=self.event1.currency_code)

        original_total_price = booking.total_price

        detail_url = reverse('booking-detail', kwargs={'pk': booking.id})
        update_data = {'number_of_tickets': 3}
        response = self.client.patch(detail_url, update_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        booking.refresh_from_db()
        payment.refresh_from_db()

        # Verify total_price is recalculated using original snapshotted price
        expected_new_total_price = self.initial_ticket_price * 3
        self.assertEqual(booking.total_price, expected_new_total_price)
        self.assertEqual(booking.price_per_ticket_at_booking, self.initial_ticket_price) # Snapshot unchanged

        # Verify Payment amount is updated
        self.assertEqual(payment.amount, expected_new_total_price)
        self.assertEqual(payment.status, 'pending') # Status should remain pending

    def test_update_number_of_tickets_confirmed_payment_fails(self):
        booking = Booking.objects.create(
            event=self.event1, user=self.user1, number_of_tickets=2,
            price_per_ticket_at_booking=self.initial_ticket_price,
            status=Booking.BookingStatus.CONFIRMED # Booking is confirmed
        )
        # Simulate a confirmed payment
        Payment.objects.create(booking=booking, amount=booking.total_price, status='successful', currency=self.event1.currency_code)

        detail_url = reverse('booking-detail', kwargs={'pk': booking.id})
        update_data = {'number_of_tickets': 3}
        response = self.client.patch(detail_url, update_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('number_of_tickets', response.data)
        self.assertIn("Cannot change number of tickets once payment is successful", response.data['number_of_tickets'][0])

    def test_update_number_of_tickets_failed_payment_fails(self):
        booking = Booking.objects.create(
            event=self.event1, user=self.user1, number_of_tickets=2,
            price_per_ticket_at_booking=self.initial_ticket_price,
            status=Booking.BookingStatus.PENDING # Booking might still be pending
        )
        Payment.objects.create(booking=booking, amount=booking.total_price, status='failed', currency=self.event1.currency_code)

        detail_url = reverse('booking-detail', kwargs={'pk': booking.id})
        update_data = {'number_of_tickets': 3}
        response = self.client.patch(detail_url, update_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('number_of_tickets', response.data)
        self.assertIn("Cannot change number of tickets once payment is failed", response.data['number_of_tickets'][0])

    # We can reuse tests from the previous subtask for booking creation email and cancellation if they are in this file.
    # For brevity, assuming those tests for email sending upon creation/cancellation are covered elsewhere or
    # would be added here following similar patterns (checking mail.outbox).
    # The test_create_booking_snapshots_price_and_creates_payment already checks for one email.

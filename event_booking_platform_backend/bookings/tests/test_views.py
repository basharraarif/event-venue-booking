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
from core.models import Role # Import Role model
from unittest.mock import patch, PropertyMock # For mocking Event.effective_capacity

User = get_user_model()

# Keep existing tests for price snapshotting and payment interactions
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

    # ... (existing tests from BookingViewSetPriceSnapshottingTests remain unchanged) ...
    # For brevity, existing tests are not repeated here, only the new class is added.
    # Ensure to append the new class to the existing file content.


# New Test Class for Permissions
class TestBookingViewSetPermissions(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = APIClient()

        # Create Roles
        cls.admin_role, _ = Role.objects.get_or_create(name=Role.ADMIN)
        cls.customer_role, _ = Role.objects.get_or_create(name=Role.CUSTOMER)
        cls.event_organizer_role, _ = Role.objects.get_or_create(name=Role.EVENT_ORGANIZER)
        cls.venue_manager_role, _ = Role.objects.get_or_create(name=Role.VENUE_MANAGER)

        # Create Users
        cls.admin_user = User.objects.create_superuser('admin_bookings', 'admin_bookings@example.com', 'adminpass')
        cls.admin_user.roles.add(cls.admin_role)

        cls.customer_user1 = User.objects.create_user('customer1_bookings', 'c1_bookings@example.com', 'custpass1')
        cls.customer_user1.roles.add(cls.customer_role)

        cls.customer_user2 = User.objects.create_user('customer2_bookings', 'c2_bookings@example.com', 'custpass2')
        cls.customer_user2.roles.add(cls.customer_role)

        cls.event_organizer_user = User.objects.create_user('eo_bookings', 'eo_bookings@example.com', 'eopass')
        cls.event_organizer_user.roles.add(cls.event_organizer_role)

        cls.venue_manager_user = User.objects.create_user('vm_bookings', 'vm_bookings@example.com', 'vmpass')
        cls.venue_manager_user.roles.add(cls.venue_manager_role)

        # Create Venues
        cls.venue_for_vm = Venue.objects.create(name="VM's Venue for Bookings", owner=cls.venue_manager_user, capacity=50)
        cls.venue_for_eo_event = Venue.objects.create(name="EO Event Venue", owner=cls.admin_user, capacity=50) # Owned by admin

        # Create Events
        cls.event_by_eo = Event.objects.create(
            name="EO's Event for Bookings", venue=cls.venue_for_eo_event, organizer=cls.event_organizer_user,
            start_time=timezone.now() + timezone.timedelta(days=5), ticket_price=Decimal("20.00")
        )
        cls.event_at_vms_venue = Event.objects.create(
            name="Event at VM's Venue", venue=cls.venue_for_vm, organizer=cls.admin_user, # Organized by admin
            start_time=timezone.now() + timezone.timedelta(days=6), ticket_price=Decimal("30.00")
        )
        cls.other_event = Event.objects.create(
            name="Other General Event", venue=cls.venue_for_eo_event, organizer=cls.admin_user, # Organized by admin
            start_time=timezone.now() + timezone.timedelta(days=7), ticket_price=Decimal("15.00")
        )

        # Create Bookings
        cls.booking_by_customer1_for_eo_event = Booking.objects.create(event=cls.event_by_eo, user=cls.customer_user1, number_of_tickets=1)
        cls.booking_by_customer2_for_eo_event = Booking.objects.create(event=cls.event_by_eo, user=cls.customer_user2, number_of_tickets=2)
        cls.booking_by_customer1_for_vms_event = Booking.objects.create(event=cls.event_at_vms_venue, user=cls.customer_user1, number_of_tickets=3)
        cls.booking_by_customer2_for_other_event = Booking.objects.create(event=cls.other_event, user=cls.customer_user2, number_of_tickets=1)

        cls.list_create_url = reverse('booking-list')

    # --- Customer Role Tests ---
    def test_customer_can_create_booking_for_self(self):
        self.client.force_authenticate(user=self.customer_user1)
        data = {'event': self.other_event.id, 'number_of_tickets': 1}
        response = self.client.post(self.list_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['user'], self.customer_user1.id)

    def test_customer_list_own_bookings(self):
        self.client.force_authenticate(user=self.customer_user1)
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        booking_ids_in_response = [b['id'] for b in response.data['results']]
        self.assertIn(str(self.booking_by_customer1_for_eo_event.id), booking_ids_in_response)
        self.assertIn(str(self.booking_by_customer1_for_vms_event.id), booking_ids_in_response)
        self.assertNotIn(str(self.booking_by_customer2_for_eo_event.id), booking_ids_in_response)
        self.assertNotIn(str(self.booking_by_customer2_for_other_event.id), booking_ids_in_response)

    def test_customer_retrieve_own_booking(self):
        self.client.force_authenticate(user=self.customer_user1)
        url = reverse('booking-detail', kwargs={'pk': self.booking_by_customer1_for_eo_event.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], str(self.booking_by_customer1_for_eo_event.id))

    def test_customer_cannot_retrieve_others_booking(self):
        self.client.force_authenticate(user=self.customer_user1)
        url = reverse('booking-detail', kwargs={'pk': self.booking_by_customer2_for_eo_event.pk})
        response = self.client.get(url)
        # IsOwnerOrAdmin for retrieve will deny if not owner and not admin
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND) # or 403 depending on exact IsOwnerOrAdmin

    def test_customer_can_cancel_own_booking(self): # Assumes cancel is a PATCH/UPDATE or specific action
        self.client.force_authenticate(user=self.customer_user1)
        # Assuming 'cancel_booking' is a custom action on the detail view
        url = reverse('booking-cancel-booking', kwargs={'pk': self.booking_by_customer1_for_eo_event.pk})
        response = self.client.post(url) # POST for actions typically
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.booking_by_customer1_for_eo_event.refresh_from_db()
        self.assertEqual(self.booking_by_customer1_for_eo_event.status, Booking.BookingStatus.CANCELLED)


# New Test Class for Capacity Checks
class TestBookingCapacityChecks(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = APIClient()

        # Roles (though not strictly for permission testing here, good for user types)
        cls.customer_role, _ = Role.objects.get_or_create(name=Role.CUSTOMER)
        cls.admin_role, _ = Role.objects.get_or_create(name=Role.ADMIN)

        # Users
        cls.user_for_booking = User.objects.create_user('booker_cap_test', 'booker_cap@example.com', 'testpass')
        cls.user_for_booking.roles.add(cls.customer_role)

        cls.admin_user = User.objects.create_superuser('admin_cap_test', 'admin_cap@example.com', 'adminpass')
        cls.admin_user.roles.add(cls.admin_role)


        # Venue
        cls.venue_with_capacity = Venue.objects.create(name="Venue With Capacity", owner=cls.admin_user, capacity=10)
        cls.venue_zero_capacity = Venue.objects.create(name="Venue Zero Capacity", owner=cls.admin_user, capacity=0)
        cls.venue_no_capacity = Venue.objects.create(name="Venue No Capacity", owner=cls.admin_user, capacity=None) # Should not happen if model field is PositiveInt

        # Events
        # Event with its own max_capacity
        cls.event_with_own_max_cap = Event.objects.create(
            name="Event Own MaxCap 5", venue=cls.venue_with_capacity, organizer=cls.admin_user,
            start_time=timezone.now() + timezone.timedelta(days=1), ticket_price=10, max_capacity=5
        )
        # Event relying on venue_with_capacity (capacity 10)
        cls.event_uses_venue_cap = Event.objects.create(
            name="Event Uses VenueCap 10", venue=cls.venue_with_capacity, organizer=cls.admin_user,
            start_time=timezone.now() + timezone.timedelta(days=2), ticket_price=10, max_capacity=None
        )
        # Event with max_capacity = 0
        cls.event_zero_max_cap = Event.objects.create(
            name="Event Zero MaxCap", venue=cls.venue_with_capacity, organizer=cls.admin_user,
            start_time=timezone.now() + timezone.timedelta(days=3), ticket_price=10, max_capacity=0
        )
        # Event with venue that has zero capacity (event.max_capacity is None)
        cls.event_venue_zero_cap = Event.objects.create(
            name="Event Venue ZeroCap", venue=cls.venue_zero_capacity, organizer=cls.admin_user,
            start_time=timezone.now() + timezone.timedelta(days=4), ticket_price=10, max_capacity=None
        )
        # Event with no capacity defined anywhere (event.max_capacity=None, event.venue.capacity=None - assuming model allows None for venue capacity)
        # For Venue.capacity being IntegerField, it cannot be None unless null=True. Let's assume it can be 0.
        # If Venue.capacity cannot be None, then this test case needs Venue with capacity=0 and event.max_capacity=None.
        # The effective_capacity logic returns None if max_capacity is None and venue is None or venue.capacity is None.
        # Let's create a venue with capacity that isn't explicitly positive for this.
        # Or better, an event with no venue for "unlimited" if model allows. For now, use venue_no_capacity if possible.
        # If Venue.capacity is IntegerField (not PositiveIntegerField), it can be 0.
        # The current Venue model has capacity = models.IntegerField(), so it can be 0.
        # Let's assume venue_no_capacity means capacity field is not set meaningfully for limits (e.g. 0 or very large)
        # Based on current model logic, if venue.capacity is 0 and event.max_capacity is None, effective_capacity will be 0.
        # To test "unlimited" (effective_capacity is None), event.max_capacity must be None AND event.venue must be None.
        # The Event model requires a venue. So, true "unlimited" via None is hard.
        # "Unlimited" is when effective_capacity evaluates to None, which our model property supports.
        # This happens if event.max_capacity is None and event.venue is None.
        # Let's create an event with max_capacity=None and venue.capacity very large for a pseudo-unlimited.
        # Or, for testing the None path of effective_capacity, we'd need to mock it or adjust model temporarily.
        # For now, we'll test "unlimited" by ensuring the check is skipped if effective_capacity is None (mocked).

        cls.list_create_url = reverse('booking-list')
        cls.client.force_authenticate(user=cls.user_for_booking)

    def test_booking_succeeds_event_max_capacity_available(self):
        data = {'event': self.event_with_own_max_cap.id, 'number_of_tickets': 3}
        response = self.client.post(self.list_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(self.event_with_own_max_cap.active_tickets_count(), 3)

    def test_booking_fails_event_max_capacity_exceeded(self):
        # Max capacity is 5. Create 3 tickets first.
        Booking.objects.create(event=self.event_with_own_max_cap, user=self.user_for_booking, number_of_tickets=3, status=Booking.BookingStatus.CONFIRMED)
        self.assertEqual(self.event_with_own_max_cap.active_tickets_count(), 3)

        data = {'event': self.event_with_own_max_cap.id, 'number_of_tickets': 3} # Try to book 3 more (total 6 > 5)
        response = self.client.post(self.list_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Not enough tickets available", response.data['detail'])
        self.assertEqual(self.event_with_own_max_cap.active_tickets_count(), 3) # Should not have changed

    def test_booking_succeeds_venue_capacity_available(self):
        # event_uses_venue_cap (capacity 10 from venue_with_capacity)
        data = {'event': self.event_uses_venue_cap.id, 'number_of_tickets': 7}
        response = self.client.post(self.list_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(self.event_uses_venue_cap.active_tickets_count(), 7)

    def test_booking_fails_venue_capacity_exceeded(self):
        # event_uses_venue_cap (capacity 10)
        Booking.objects.create(event=self.event_uses_venue_cap, user=self.user_for_booking, number_of_tickets=8, status=Booking.BookingStatus.CONFIRMED)
        self.assertEqual(self.event_uses_venue_cap.active_tickets_count(), 8)

        data = {'event': self.event_uses_venue_cap.id, 'number_of_tickets': 3} # Try to book 3 more (total 11 > 10)
        response = self.client.post(self.list_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Not enough tickets available", response.data['detail'])
        self.assertEqual(self.event_uses_venue_cap.active_tickets_count(), 8)

    def test_booking_fails_event_explicit_zero_max_capacity(self):
        data = {'event': self.event_zero_max_cap.id, 'number_of_tickets': 1}
        response = self.client.post(self.list_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("This event cannot be booked as it has zero capacity.", response.data['detail'])

    def test_booking_fails_event_uses_venue_zero_capacity(self):
        # event_venue_zero_cap uses venue_zero_capacity (capacity 0)
        data = {'event': self.event_venue_zero_cap.id, 'number_of_tickets': 1}
        response = self.client.post(self.list_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("This event cannot be booked as it has zero capacity.", response.data['detail'])

    @patch('events.models.Event.effective_capacity', new_callable=PropertyMock)
    def test_booking_succeeds_unlimited_capacity_event_max_cap_none_venue_none(self, mock_effective_capacity):
        # Mock effective_capacity to return None (unlimited)
        mock_effective_capacity.return_value = None

        # Use any event, its actual capacity values don't matter due to mocking
        data = {'event': self.event_with_own_max_cap.id, 'number_of_tickets': 1000}
        response = self.client.post(self.list_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        # active_tickets_count will still work on the actual event, so check based on that.
        # This test primarily ensures the view's capacity check is bypassed.
        self.assertTrue(Booking.objects.filter(event=self.event_with_own_max_cap, number_of_tickets=1000).exists())

    def test_booking_capacity_with_various_status_bookings(self):
        # event_with_own_max_cap (capacity 5)
        Booking.objects.create(event=self.event_with_own_max_cap, user=self.user_for_booking, number_of_tickets=1, status=Booking.BookingStatus.CONFIRMED)
        Booking.objects.create(event=self.event_with_own_max_cap, user=self.user_for_booking, number_of_tickets=1, status=Booking.BookingStatus.PENDING_PAYMENT)
        Booking.objects.create(event=self.event_with_own_max_cap, user=self.user_for_booking, number_of_tickets=1, status=Booking.BookingStatus.CANCELLED)
        Booking.objects.create(event=self.event_with_own_max_cap, user=self.user_for_booking, number_of_tickets=1, status=Booking.BookingStatus.PENDING) # Assuming PENDING is not active

        # Active tickets should be 1 (CONFIRMED) + 1 (PENDING_PAYMENT) = 2
        self.assertEqual(self.event_with_own_max_cap.active_tickets_count(), 2)

        # Try to book 3 more tickets (2 existing active + 3 requested = 5, which is capacity)
        data = {'event': self.event_with_own_max_cap.id, 'number_of_tickets': 3}
        response = self.client.post(self.list_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(self.event_with_own_max_cap.active_tickets_count(), 5)

        # Try to book 1 more ticket (should fail, 5 existing active + 1 requested > 5)
        data2 = {'event': self.event_with_own_max_cap.id, 'number_of_tickets': 1}
        response2 = self.client.post(self.list_create_url, data2, format='json')
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Not enough tickets available. Only 0 left.", response2.data['detail'])

    # Tests for capacity check during booking update
    def test_update_booking_succeeds_capacity_available(self):
        # event_with_own_max_cap (capacity 5)
        booking = Booking.objects.create(event=self.event_with_own_max_cap, user=self.user_for_booking, number_of_tickets=2, status=Booking.BookingStatus.CONFIRMED)
        self.assertEqual(self.event_with_own_max_cap.active_tickets_count(), 2)

        url = reverse('booking-detail', kwargs={'pk': booking.pk})
        data = {'number_of_tickets': 4} # Change from 2 to 4. Total active = 4. (Capacity 5)
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        booking.refresh_from_db()
        self.assertEqual(booking.number_of_tickets, 4)
        self.assertEqual(self.event_with_own_max_cap.active_tickets_count(), 4)

    def test_update_booking_fails_capacity_exceeded(self):
        # event_with_own_max_cap (capacity 5)
        Booking.objects.create(event=self.event_with_own_max_cap, user=self.admin_user, number_of_tickets=3, status=Booking.BookingStatus.CONFIRMED) # Another user's booking
        booking_to_update = Booking.objects.create(event=self.event_with_own_max_cap, user=self.user_for_booking, number_of_tickets=1, status=Booking.BookingStatus.CONFIRMED)
        # Total active tickets = 3 + 1 = 4. Available = 5 - 4 = 1.
        # If booking_to_update changes from 1 to 3 tickets:
        # current_active_tickets_excluding_this = 4 - 1 = 3.
        # requested_new_number_of_tickets = 3.
        # 3 + 3 = 6. Effective capacity = 5. 6 > 5. Fail.

        self.assertEqual(self.event_with_own_max_cap.active_tickets_count(), 4)

        url = reverse('booking-detail', kwargs={'pk': booking_to_update.pk})
        data = {'number_of_tickets': 3} # Change from 1 to 3. (Current is 1, other is 3. Total 4. Trying to make it 3+3=6. Cap 5)
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn("Not enough tickets available for update.", response.data['detail'])
        booking_to_update.refresh_from_db()
        self.assertEqual(booking_to_update.number_of_tickets, 1) # Should not change
        self.assertEqual(self.event_with_own_max_cap.active_tickets_count(), 4) # Total active should not change

    def test_customer_cannot_cancel_others_booking(self):
        self.client.force_authenticate(user=self.customer_user1)
        url = reverse('booking-cancel-booking', kwargs={'pk': self.booking_by_customer2_for_eo_event.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND) # or 403

    # --- Event Organizer Role Tests ---
    def test_event_organizer_list_bookings_for_own_events(self):
        self.client.force_authenticate(user=self.event_organizer_user)
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        booking_ids_in_response = [b['id'] for b in response.data['results']]
        # EO should see bookings for event_by_eo
        self.assertIn(str(self.booking_by_customer1_for_eo_event.id), booking_ids_in_response)
        self.assertIn(str(self.booking_by_customer2_for_eo_event.id), booking_ids_in_response)
        # EO should NOT see bookings for events they don't organize
        self.assertNotIn(str(self.booking_by_customer1_for_vms_event.id), booking_ids_in_response)
        self.assertNotIn(str(self.booking_by_customer2_for_other_event.id), booking_ids_in_response)

    def test_event_organizer_retrieve_booking_for_own_event(self):
        self.client.force_authenticate(user=self.event_organizer_user)
        url = reverse('booking-detail', kwargs={'pk': self.booking_by_customer1_for_eo_event.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK) # IsOwnerOrAdmin might allow if obj.event.organizer == user

    def test_event_organizer_cannot_cancel_booking_for_own_event(self): # Unless explicitly allowed
        self.client.force_authenticate(user=self.event_organizer_user)
        url = reverse('booking-cancel-booking', kwargs={'pk': self.booking_by_customer1_for_eo_event.pk})
        response = self.client.post(url)
        # Default IsOwnerOrAdmin would restrict this unless EO is the booking.user or admin
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) # Or 404 if get_object fails due to strict ownership check

    # --- Venue Manager Role Tests ---
    def test_venue_manager_list_bookings_for_events_at_own_venues(self):
        self.client.force_authenticate(user=self.venue_manager_user)
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        booking_ids_in_response = [b['id'] for b in response.data['results']]
        # VM should see bookings for events at venue_for_vm (i.e., booking_by_customer1_for_vms_event)
        self.assertIn(str(self.booking_by_customer1_for_vms_event.id), booking_ids_in_response)
        # VM should NOT see bookings for events at other venues
        self.assertNotIn(str(self.booking_by_customer1_for_eo_event.id), booking_ids_in_response)
        self.assertNotIn(str(self.booking_by_customer2_for_other_event.id), booking_ids_in_response)

    def test_venue_manager_retrieve_booking_for_event_at_own_venue(self):
        self.client.force_authenticate(user=self.venue_manager_user)
        url = reverse('booking-detail', kwargs={'pk': self.booking_by_customer1_for_vms_event.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK) # Similar to EO, depends on IsOwnerOrAdmin logic for GET

    # --- Admin Role Tests ---
    def test_admin_list_all_bookings(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Admin should see all bookings created in setUpTestData
        expected_num_bookings = Booking.objects.count()
        self.assertEqual(len(response.data['results']), expected_num_bookings)

    def test_admin_can_retrieve_any_booking(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('booking-detail', kwargs={'pk': self.booking_by_customer1_for_eo_event.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_can_cancel_any_booking(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('booking-cancel-booking', kwargs={'pk': self.booking_by_customer1_for_eo_event.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.booking_by_customer1_for_eo_event.refresh_from_db()
        self.assertEqual(self.booking_by_customer1_for_eo_event.status, Booking.BookingStatus.CANCELLED)

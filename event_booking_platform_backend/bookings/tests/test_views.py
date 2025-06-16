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

        # Verify booking status and payment_intent_id
        self.assertEqual(new_booking.status, Booking.BookingStatus.PENDING_PAYMENT)
        self.assertIsNone(new_booking.payment_intent_id, "Payment Intent ID should be None on initial booking creation")

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

    @patch('event_booking_platform_backend.bookings.views.send_booking_related_email')
    def test_customer_can_cancel_own_booking_sends_email(self, mock_send_email):
        self.client.force_authenticate(user=self.customer_user1)
        booking_to_cancel = self.booking_by_customer1_for_eo_event
        # Ensure booking is not already cancelled for a clean test
        booking_to_cancel.status = Booking.BookingStatus.CONFIRMED
        booking_to_cancel.save()

        url = reverse('booking-cancel-booking', kwargs={'pk': booking_to_cancel.pk})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        booking_to_cancel.refresh_from_db()
        self.assertEqual(booking_to_cancel.status, Booking.BookingStatus.CANCELLED)

        mock_send_email.assert_called_once_with(
            booking=booking_to_cancel,
            subject_template_name='emails/booking_cancelled_subject.txt',
            body_html_template_name='emails/booking_cancelled_body.html',
            body_text_template_name='emails/booking_cancelled_body.txt'
        )


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
        self.assertIn("Booking exceeds event capacity. Only 2 tickets available.", response.data['detail']) # 5 cap - 3 confirmed = 2 left
        self.assertEqual(Booking.objects.filter(event=self.event_with_own_max_cap, status=Booking.BookingStatus.CONFIRMED).aggregate(Sum('number_of_tickets'))['number_of_tickets__sum'] or 0, 3) # Confirm no new confirmed bookings

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

    def test_booking_succeeds_unlimited_capacity_event(self):
        # Event with max_capacity = None (unlimited)
        # Create a new event for this test to avoid interference
        unlimited_event = Event.objects.create(
            name="Unlimited Capacity Event", venue=self.venue_with_capacity, organizer=self.admin_user,
            start_time=timezone.now() + timezone.timedelta(days=1), ticket_price=10, max_capacity=None
        )
        data = {'event': unlimited_event.id, 'number_of_tickets': 1000}
        response = self.client.post(self.list_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertTrue(Booking.objects.filter(event=unlimited_event, number_of_tickets=1000).exists())

    def test_booking_exactly_up_to_capacity(self):
        # Event max_capacity = 5
        exact_cap_event = Event.objects.create(
            name="Exact Cap Event", venue=self.venue_with_capacity, organizer=self.admin_user,
            start_time=timezone.now() + timezone.timedelta(days=1), ticket_price=10, max_capacity=5
        )
        # Book 5 tickets
        data_book_5 = {'event': exact_cap_event.id, 'number_of_tickets': 5}
        response_book_5 = self.client.post(self.list_create_url, data_book_5, format='json')
        self.assertEqual(response_book_5.status_code, status.HTTP_201_CREATED, response_book_5.data)

        # Confirm the booking to count against capacity
        booking1 = Booking.objects.get(event=exact_cap_event, number_of_tickets=5)
        booking1.status = Booking.BookingStatus.CONFIRMED
        booking1.save()

        # Attempt to book 1 more ticket
        data_book_1_more = {'event': exact_cap_event.id, 'number_of_tickets': 1}
        response_book_1_more = self.client.post(self.list_create_url, data_book_1_more, format='json')
        self.assertEqual(response_book_1_more.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Booking exceeds event capacity. Only 0 tickets available.", response_book_1_more.data['detail'])


    def test_booking_capacity_with_various_status_bookings(self):
        # event_with_own_max_cap (capacity 5)
        Booking.objects.create(event=self.event_with_own_max_cap, user=self.user_for_booking, number_of_tickets=1, status=Booking.BookingStatus.CONFIRMED)
        Booking.objects.create(event=self.event_with_own_max_cap, user=self.user_for_booking, number_of_tickets=1, status=Booking.BookingStatus.PENDING_PAYMENT)
        Booking.objects.create(event=self.event_with_own_max_cap, user=self.user_for_booking, number_of_tickets=1, status=Booking.BookingStatus.CANCELLED)
        Booking.objects.create(event=self.event_with_own_max_cap, user=self.user_for_booking, number_of_tickets=1, status=Booking.BookingStatus.PENDING) # Assuming PENDING is not active

        # Active tickets based on CONFIRMED only should be 1.
        # self.assertEqual(self.event_with_own_max_cap.active_tickets_count(), 2) # This line uses old logic

        # Test: PENDING_PAYMENT bookings do not block capacity initially
        # Event max_capacity = 5. Confirmed = 1. Pending Payment = 1. Pending = 1. Cancelled = 1.
        # Available capacity = 5 - 1 (CONFIRMED) = 4.
        data = {'event': self.event_with_own_max_cap.id, 'number_of_tickets': 3} # Try to book 3. (1 + 3 = 4 <= 5)
        response = self.client.post(self.list_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        # New booking will be PENDING_PAYMENT, so confirmed count is still 1 + the new one if it were confirmed,
        # but it's not confirmed yet. The check is against current DB state of CONFIRMED.
        # After this booking, CONFIRMED = 1. PENDING_PAYMENT = 1 (original) + 1 (new).

        # Check that we can book up to remaining capacity based on CONFIRMED bookings
        data2 = {'event': self.event_with_own_max_cap.id, 'number_of_tickets': 1} # Book 1 more. (1 + 3 + 1 = 5 <= 5)
        response2 = self.client.post(self.list_create_url, data2, format='json')
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED, response2.data)
        # Total CONFIRMED = 1. Total PENDING_PAYMENT = 1 (original) + 1 (from data) + 1 (from data2).

        # Try to book 1 more ticket (should fail, current confirmed is 1, so 4 available. But we booked 3+1=4 PENDING_PAYMENT tickets already)
        # If we try to book 1 more, it would be 1(confirmed) + 4(pending_payment from this test) + 1(new) > 5 if they all became confirmed
        # The check is: requested_tickets > (effective_capacity - current_booked_tickets_CONFIRMED)
        # effective_capacity = 5. current_booked_tickets_CONFIRMED = 1.
        # requested_tickets (1) > (5 - 1 = 4) is false. So this should pass based on current confirmed.
        # This means the test name "test_booking_capacity_with_various_status_bookings" and its setup
        # needs to be re-evaluated for clarity against the new logic in perform_create.

        # Let's refine this test to be more specific:
        # "test_pending_payment_bookings_do_not_block_capacity_until_confirmed"

        # Setup for the specific test:
        # Event max_capacity = 5
        booking_confirmed = Booking.objects.get(event=self.event_with_own_max_cap, status=Booking.BookingStatus.CONFIRMED)
        booking_pending_payment = Booking.objects.get(event=self.event_with_own_max_cap, status=Booking.BookingStatus.PENDING_PAYMENT)

        # Current state: 1 CONFIRMED ticket. Available = 5 - 1 = 4.
        # Book 4 tickets for another user (self.admin_user for simplicity for now)
        self.client.force_authenticate(user=self.admin_user) # Different user
        data_fill_capacity = {'event': self.event_with_own_max_cap.id, 'number_of_tickets': 4}
        response_fill = self.client.post(self.list_create_url, data_fill_capacity, format='json')
        self.assertEqual(response_fill.status_code, status.HTTP_201_CREATED, response_fill.data)
        # Now, 1 CONFIRMED, 1 PENDING_PAYMENT (original), 1 PENDING_PAYMENT (new by admin_user for 4 tickets).

        # Try to book 1 more ticket (should fail, as 1 confirmed + 4 pending_payment (new) = 5 if confirmed.
        # But check is against current CONFIRMED only: 5 - 1 = 4 available. So 1 should be bookable.
        # This means the previous test logic was subtly different.
        # The error message should be "Booking exceeds event capacity. Only 0 tickets available." if 5 confirmed.
        # If 1 confirmed, then 4 available. Booking 1 more should be fine.
        self.client.force_authenticate(user=self.user_for_booking) # Switch back
        data_one_more = {'event': self.event_with_own_max_cap.id, 'number_of_tickets': 1}
        response_one_more = self.client.post(self.list_create_url, data_one_more, format='json')
        # This should fail if the previous 4-ticket booking by admin was confirmed.
        # But it's PENDING_PAYMENT. So current confirmed is still 1. 5-1=4 available. Booking 1 is OK.
        self.assertEqual(response_one_more.status_code, status.HTTP_201_CREATED, response_one_more.data)


        # Now, confirm the admin's 4-ticket booking
        admin_booking = Booking.objects.get(user=self.admin_user, event=self.event_with_own_max_cap)
        admin_booking.status = Booking.BookingStatus.CONFIRMED
        admin_booking.save()
        # Now CONFIRMED tickets = 1 (original by user_for_booking) + 4 (by admin_user) = 5.
        # Remaining capacity = 5 - 5 = 0.

        # Attempt to book 1 more ticket by original user
        self.client.force_authenticate(user=self.user_for_booking)
        data_after_confirm = {'event': self.event_with_own_max_cap.id, 'number_of_tickets': 1}
        response_after_confirm = self.client.post(self.list_create_url, data_after_confirm, format='json')
        self.assertEqual(response_after_confirm.status_code, status.HTTP_400_BAD_REQUEST)
        # Expected message: "Booking exceeds event capacity. Only 0 tickets available."
        self.assertIn("Booking exceeds event capacity. Only 0 tickets available.", response_after_confirm.data['detail'])


    # Tests for capacity check during booking update
    def test_update_booking_succeeds_capacity_available(self):
        # event_with_own_max_cap (capacity 5)
        # User U1 books 2 tickets, CONFIRMED. (Confirmed: 2, Available: 3)
        booking = Booking.objects.create(event=self.event_with_own_max_cap, user=self.user_for_booking, number_of_tickets=2, status=Booking.BookingStatus.CONFIRMED)

        url = reverse('booking-detail', kwargs={'pk': booking.pk})
        # U1 wants to change their booking from 2 to 4 tickets.
        # Other confirmed tickets = 0. Requested = 4. 0 + 4 <= 5. Should succeed.
        data = {'number_of_tickets': 4}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        booking.refresh_from_db()
        self.assertEqual(booking.number_of_tickets, 4)
        # Total confirmed for event = 4.

    def test_update_booking_fails_capacity_exceeded(self):
        # event_with_own_max_cap (capacity 5)
        # User Admin books 3 tickets, CONFIRMED. (Confirmed: 3, Available: 2)
        other_booking = Booking.objects.create(event=self.event_with_own_max_cap, user=self.admin_user, number_of_tickets=3, status=Booking.BookingStatus.CONFIRMED)

        # User U1 books 1 ticket, CONFIRMED. (Total Confirmed: 3+1=4, Available: 1)
        booking_to_update = Booking.objects.create(event=self.event_with_own_max_cap, user=self.user_for_booking, number_of_tickets=1, status=Booking.BookingStatus.CONFIRMED)

        url = reverse('booking-detail', kwargs={'pk': booking_to_update.pk})
        # U1 wants to change their booking from 1 to 3 tickets.
        # Other confirmed tickets (by Admin) = 3. Requested by U1 = 3.
        # 3 (other) + 3 (requested) = 6. Capacity is 5. Should fail.
        # Available for U1's update, considering others: 5 (cap) - 3 (other_confirmed) = 2. U1 requests 3.
        data = {'number_of_tickets': 3}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        # Expected error: "Update exceeds event capacity. Only 2 tickets available for others or for increase."
        self.assertIn("Update exceeds event capacity. Only 2 tickets available for others or for increase.", response.data['detail'])

        booking_to_update.refresh_from_db()
        self.assertEqual(booking_to_update.number_of_tickets, 1) # Should not change

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

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from django.contrib.auth import get_user_model
from core.models import Role
from events.models import Event, Venue, Category
from bookings.models import Booking

User = get_user_model()

@pytest.mark.django_db
class TestCrossAppPermissions:

    @pytest.fixture
    def api_client(self):
        return APIClient()

    @pytest.fixture
    def common_roles(self):
        customer, _ = Role.objects.get_or_create(name=Role.CUSTOMER)
        organizer, _ = Role.objects.get_or_create(name=Role.EVENT_ORGANIZER)
        manager, _ = Role.objects.get_or_create(name=Role.VENUE_MANAGER)
        admin, _ = Role.objects.get_or_create(name=Role.ADMIN)
        return {'customer': customer, 'organizer': organizer, 'manager': manager, 'admin': admin}

    @pytest.fixture
    def customer_user(self, common_roles):
        user = User.objects.create_user(username='customer_only', email='customer@perm.test', password='password')
        user.roles.add(common_roles['customer'])
        return user

    @pytest.fixture
    def event_organizer_user_C(self, common_roles): # User C
        user = User.objects.create_user(username='organizer_C', email='organizer_C@perm.test', password='password')
        user.roles.add(common_roles['organizer'])
        return user

    @pytest.fixture
    def event_organizer_user_D(self, common_roles): # User D
        user = User.objects.create_user(username='organizer_D', email='organizer_D@perm.test', password='password')
        user.roles.add(common_roles['organizer'])
        return user

    @pytest.fixture
    def venue_manager_user_A(self, common_roles): # User A
        user = User.objects.create_user(username='manager_A', email='manager_A@perm.test', password='password')
        user.roles.add(common_roles['manager'])
        return user

    @pytest.fixture
    def venue_manager_user_B(self, common_roles): # User B (another Venue Manager)
        user = User.objects.create_user(username='manager_B', email='manager_B@perm.test', password='password')
        user.roles.add(common_roles['manager'])
        return user

    @pytest.fixture
    def admin_user(self, common_roles):
        user = User.objects.create_user(username='admin_perm', email='admin@perm.test', password='password', is_staff=True)
        user.roles.add(common_roles['admin'])
        return user

    @pytest.fixture
    def sample_category(self):
        return Category.objects.create(name="Test Category Global")

    # --- Scenario 1: Venue Manager Access Control ---
    def test_venue_manager_permissions_on_own_and_others_venues(self, api_client, venue_manager_user_A, venue_manager_user_B, customer_user, admin_user):
        # User A (Venue Manager) creates a Venue
        api_client.force_authenticate(user=venue_manager_user_A)
        venue_create_url = reverse('venue-list')
        venue_data_A = {'name': 'Venue by A', 'address': 'A Address', 'capacity': 100}
        response = api_client.post(venue_create_url, venue_data_A, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        venue_A_id = response.data['id']
        venue_A_url = reverse('venue-detail', kwargs={'pk': venue_A_id})

        # User A can retrieve their own Venue
        response = api_client.get(venue_A_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Venue by A'

        # User A can update their own Venue
        response = api_client.patch(venue_A_url, {'name': 'Venue by A Updated'}, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Venue by A Updated'

        # User B (another Venue Manager) cannot update User A's Venue
        api_client.force_authenticate(user=venue_manager_user_B)
        response = api_client.patch(venue_A_url, {'name': 'Attempt Update by B'}, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Customer User cannot update User A's Venue
        api_client.force_authenticate(user=customer_user)
        response = api_client.patch(venue_A_url, {'name': 'Attempt Update by Customer'}, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Admin user can update User A's Venue
        api_client.force_authenticate(user=admin_user)
        response = api_client.patch(venue_A_url, {'name': 'Venue by A Updated by Admin'}, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Venue by A Updated by Admin'

        # User B (another Venue Manager) cannot delete User A's Venue
        api_client.force_authenticate(user=venue_manager_user_B)
        response = api_client.delete(venue_A_url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Customer User cannot delete User A's Venue
        api_client.force_authenticate(user=customer_user)
        response = api_client.delete(venue_A_url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # User A can delete their own Venue
        api_client.force_authenticate(user=venue_manager_user_A)
        response = api_client.delete(venue_A_url)
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify it's deleted
        response = api_client.get(venue_A_url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Admin can delete any venue (re-create for this test)
        response = api_client.post(venue_create_url, venue_data_A, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        venue_A_id_admin_del = response.data['id']
        venue_A_url_admin_del = reverse('venue-detail', kwargs={'pk': venue_A_id_admin_del})
        api_client.force_authenticate(user=admin_user)
        response = api_client.delete(venue_A_url_admin_del)
        assert response.status_code == status.HTTP_204_NO_CONTENT


    # --- Scenario 2: Event Organizer Access Control ---
    def test_event_organizer_permissions_on_own_and_others_events(self, api_client, event_organizer_user_C, event_organizer_user_D, customer_user, admin_user, venue_manager_user_A, sample_category):
        # Venue needs to be created first, by a Venue Manager or Admin
        api_client.force_authenticate(user=venue_manager_user_A)
        venue_url = reverse('venue-list')
        venue_data = {'name': 'Venue for Events', 'address': 'Event Venue St', 'capacity': 150}
        response = api_client.post(venue_url, venue_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        created_venue_id = response.data['id']

        # User C (Event Organizer) creates an Event
        api_client.force_authenticate(user=event_organizer_user_C)
        event_create_url = reverse('event-list')
        event_data_C = {
            'name': 'Event by C', 'venue': created_venue_id, 'ticket_price': 30,
            'start_time': "2030-01-01T10:00:00Z", 'end_time': "2030-01-01T12:00:00Z",
            'categories': [sample_category.name]
        }
        response = api_client.post(event_create_url, event_data_C, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        event_C_id = response.data['id']
        event_C_url = reverse('event-detail', kwargs={'pk': event_C_id})

        # User C can retrieve their own Event
        response = api_client.get(event_C_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Event by C'

        # User C can update their own Event
        response = api_client.patch(event_C_url, {'name': 'Event by C Updated'}, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Event by C Updated'

        # User D (another Event Organizer) cannot update User C's Event
        api_client.force_authenticate(user=event_organizer_user_D)
        response = api_client.patch(event_C_url, {'name': 'Attempt Update by D'}, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Customer User cannot update User C's Event
        api_client.force_authenticate(user=customer_user)
        response = api_client.patch(event_C_url, {'name': 'Attempt Update by Customer'}, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Admin user can update User C's Event
        api_client.force_authenticate(user=admin_user)
        response = api_client.patch(event_C_url, {'name': 'Event by C Updated by Admin'}, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Event by C Updated by Admin'

        # User D (another Event Organizer) cannot delete User C's Event
        api_client.force_authenticate(user=event_organizer_user_D)
        response = api_client.delete(event_C_url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Customer User cannot delete User C's Event
        api_client.force_authenticate(user=customer_user)
        response = api_client.delete(event_C_url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # User C can delete their own Event
        api_client.force_authenticate(user=event_organizer_user_C)
        response = api_client.delete(event_C_url)
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify it's deleted
        response = api_client.get(event_C_url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Admin can delete any event (re-create for this test)
        response = api_client.post(event_create_url, event_data_C, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        event_C_id_admin_del = response.data['id']
        event_C_url_admin_del = reverse('event-detail', kwargs={'pk': event_C_id_admin_del})
        api_client.force_authenticate(user=admin_user)
        response = api_client.delete(event_C_url_admin_del)
        assert response.status_code == status.HTTP_204_NO_CONTENT

    # --- Scenario 3: Cross-Role Restrictions ---
    def test_venue_manager_cannot_create_event(self, api_client, venue_manager_user_A, sample_category):
        # Setup: Venue Manager needs a venue to try to create an event for
        api_client.force_authenticate(user=venue_manager_user_A)
        venue_url = reverse('venue-list')
        venue_data = {'name': 'VM Venue for Event Test', 'address': 'VM Event Test St', 'capacity': 50}
        response = api_client.post(venue_url, venue_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        vm_venue_id = response.data['id']

        # Venue Manager (User A, not an Event Organizer) attempts to create an Event
        event_create_url = reverse('event-list')
        event_data = {
            'name': 'Event by VM A', 'venue': vm_venue_id, 'ticket_price': 10,
            'start_time': "2030-02-01T10:00:00Z", 'end_time': "2030-02-01T12:00:00Z",
            'categories': [sample_category.name]
            # Organizer is set by perform_create in viewset, which will be venue_manager_user_A
            # The permission check IsAdminUser | IsEventOrganizer should deny this.
        }
        response = api_client.post(event_create_url, event_data, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_event_organizer_cannot_create_venue(self, api_client, event_organizer_user_C):
        # Event Organizer (User C, not a Venue Manager) attempts to create a Venue
        api_client.force_authenticate(user=event_organizer_user_C)
        venue_create_url = reverse('venue-list')
        venue_data = {'name': 'Venue by EO C', 'address': 'EO C Address', 'capacity': 70}
        # Owner is set by perform_create in viewset to event_organizer_user_C
        # The permission check IsAdminUser | IsVenueManager should deny this.
        response = api_client.post(venue_create_url, venue_data, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN


    # --- Test Admin full access (covered implicitly, but one explicit check) ---
    def test_admin_can_manage_any_venue_and_event(self, api_client, admin_user, venue_manager_user_A, event_organizer_user_C, sample_category):
        # VM User A creates a venue
        api_client.force_authenticate(user=venue_manager_user_A)
        venue_data_A = {'name': 'Venue by A for Admin Test', 'address': 'A Address Admin', 'capacity': 100}
        response = api_client.post(reverse('venue-list'), venue_data_A, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        venue_A_id = response.data['id']
        venue_A_url = reverse('venue-detail', kwargs={'pk': venue_A_id})

        # EO User C creates an event in Venue A
        api_client.force_authenticate(user=event_organizer_user_C)
        event_data_C = {
            'name': 'Event by C for Admin Test', 'venue': venue_A_id, 'ticket_price': 30,
            'start_time': "2030-03-01T10:00:00Z", 'end_time': "2030-03-01T12:00:00Z",
            'categories': [sample_category.name]
        }
        response = api_client.post(reverse('event-list'), event_data_C, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        event_C_id = response.data['id']
        event_C_url = reverse('event-detail', kwargs={'pk': event_C_id})

        # Admin logs in
        api_client.force_authenticate(user=admin_user)

        # Admin can retrieve Venue A
        response = api_client.get(venue_A_url)
        assert response.status_code == status.HTTP_200_OK
        # Admin can update Venue A
        response = api_client.patch(venue_A_url, {'name': 'Venue A Updated by Admin'}, format='json')
        assert response.status_code == status.HTTP_200_OK

        # Admin can retrieve Event C
        response = api_client.get(event_C_url)
        assert response.status_code == status.HTTP_200_OK
        # Admin can update Event C
        response = api_client.patch(event_C_url, {'name': 'Event C Updated by Admin'}, format='json')
        assert response.status_code == status.HTTP_200_OK

        # Admin can delete Event C
        response = api_client.delete(event_C_url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        # Admin can delete Venue A
        response = api_client.delete(venue_A_url)
        assert response.status_code == status.HTTP_204_NO_CONTENT

    # --- Booking Access (already partially covered in original test file, enhanced here) ---
    # Test if Event Organizer can view bookings for their events
    def test_event_organizer_booking_list_and_retrieve_access(self, api_client, event_organizer_user_C, customer_user, venue_manager_user_A, sample_category):
        # Venue setup
        api_client.force_authenticate(user=venue_manager_user_A)
        venue_resp = api_client.post(reverse('venue-list'), {'name': 'Venue for Booking Test EO', 'address': 'EO Booking St', 'capacity': 50}, format='json')
        assert venue_resp.status_code == status.HTTP_201_CREATED
        venue_id = venue_resp.data['id']

        # Event Organizer C creates an event
        api_client.force_authenticate(user=event_organizer_user_C)
        event_data = {'name': 'EO C Event for Bookings', 'venue': venue_id, 'ticket_price': 10, 'start_time': "2030-04-01T10:00:00Z", 'end_time': "2030-04-01T12:00:00Z", 'categories': [sample_category.name]}
        event_resp = api_client.post(reverse('event-list'), event_data, format='json')
        assert event_resp.status_code == status.HTTP_201_CREATED
        event_id = event_resp.data['id']

        # Customer books the event
        api_client.force_authenticate(user=customer_user)
        booking_data = {'event': event_id, 'number_of_tickets': 1}
        booking_resp = api_client.post(reverse('booking-list'), booking_data, format='json')
        assert booking_resp.status_code == status.HTTP_201_CREATED
        booking_id = booking_resp.data['id']

        # Event Organizer C lists bookings, should see the booking for their event
        api_client.force_authenticate(user=event_organizer_user_C)
        response = api_client.get(reverse('booking-list'))
        assert response.status_code == status.HTTP_200_OK
        assert any(b['id'] == booking_id for b in response.data.get('results', [])), "Booking for EO's event not found"

        # Event Organizer C retrieves the booking for their event
        # According to BookingViewSet.get_queryset, this should be allowed.
        response = api_client.get(reverse('booking-detail', kwargs={'pk': booking_id}))
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == booking_id

    # Test if Venue Manager can view bookings for events at their venues
    def test_venue_manager_booking_list_and_retrieve_access(self, api_client, venue_manager_user_A, event_organizer_user_C, customer_user, sample_category):
        # Venue Manager A creates a venue
        api_client.force_authenticate(user=venue_manager_user_A)
        venue_resp = api_client.post(reverse('venue-list'), {'name': 'VM A Venue for Bookings', 'address': 'VM A Booking St', 'capacity': 60}, format='json')
        assert venue_resp.status_code == status.HTTP_201_CREATED
        venue_id = venue_resp.data['id']

        # Event Organizer C creates an event at VM A's venue
        api_client.force_authenticate(user=event_organizer_user_C)
        event_data = {'name': 'Event at VM A Venue', 'venue': venue_id, 'ticket_price': 12, 'start_time': "2030-05-01T10:00:00Z", 'end_time': "2030-05-01T12:00:00Z", 'categories': [sample_category.name]}
        event_resp = api_client.post(reverse('event-list'), event_data, format='json')
        assert event_resp.status_code == status.HTTP_201_CREATED
        event_id = event_resp.data['id']

        # Customer books this event
        api_client.force_authenticate(user=customer_user)
        booking_data = {'event': event_id, 'number_of_tickets': 2}
        booking_resp = api_client.post(reverse('booking-list'), booking_data, format='json')
        assert booking_resp.status_code == status.HTTP_201_CREATED
        booking_id = booking_resp.data['id']

        # Venue Manager A lists bookings, should see the booking for event at their venue
        api_client.force_authenticate(user=venue_manager_user_A)
        response = api_client.get(reverse('booking-list'))
        assert response.status_code == status.HTTP_200_OK
        assert any(b['id'] == booking_id for b in response.data.get('results', [])), "Booking for event at VM's venue not found"

        # Venue Manager A retrieves the booking for event at their venue
        # According to BookingViewSet.get_queryset, this should be allowed.
        response = api_client.get(reverse('booking-detail', kwargs={'pk': booking_id}))
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == booking_id
```python
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from django.contrib.auth import get_user_model
from core.models import Role
from events.models import Event, Venue, Category
from bookings.models import Booking

User = get_user_model()

@pytest.mark.django_db
class TestCrossAppPermissions:

    @pytest.fixture
    def api_client(self):
        return APIClient()

    @pytest.fixture
    def common_roles(self):
        customer, _ = Role.objects.get_or_create(name=Role.CUSTOMER)
        organizer, _ = Role.objects.get_or_create(name=Role.EVENT_ORGANIZER)
        manager, _ = Role.objects.get_or_create(name=Role.VENUE_MANAGER)
        admin, _ = Role.objects.get_or_create(name=Role.ADMIN)
        return {'customer': customer, 'organizer': organizer, 'manager': manager, 'admin': admin}

    @pytest.fixture
    def customer_user(self, common_roles):
        user = User.objects.create_user(username='customer_only', email='customer@perm.test', password='password')
        user.roles.add(common_roles['customer'])
        return user

    @pytest.fixture
    def event_organizer_user_C(self, common_roles): # User C
        user = User.objects.create_user(username='organizer_C', email='organizer_C@perm.test', password='password')
        user.roles.add(common_roles['organizer'])
        return user

    @pytest.fixture
    def event_organizer_user_D(self, common_roles): # User D
        user = User.objects.create_user(username='organizer_D', email='organizer_D@perm.test', password='password')
        user.roles.add(common_roles['organizer'])
        return user

    @pytest.fixture
    def venue_manager_user_A(self, common_roles): # User A
        user = User.objects.create_user(username='manager_A', email='manager_A@perm.test', password='password')
        user.roles.add(common_roles['manager'])
        return user

    @pytest.fixture
    def venue_manager_user_B(self, common_roles): # User B (another Venue Manager)
        user = User.objects.create_user(username='manager_B', email='manager_B@perm.test', password='password')
        user.roles.add(common_roles['manager'])
        return user

    @pytest.fixture
    def admin_user(self, common_roles):
        user = User.objects.create_user(username='admin_perm', email='admin@perm.test', password='password', is_staff=True)
        user.roles.add(common_roles['admin'])
        return user

    @pytest.fixture
    def sample_category(self):
        return Category.objects.create(name="Test Category Global")

    # --- Scenario 1: Venue Manager Access Control ---
    def test_venue_manager_permissions_on_own_and_others_venues(self, api_client, venue_manager_user_A, venue_manager_user_B, customer_user, admin_user):
        # User A (Venue Manager) creates a Venue
        api_client.force_authenticate(user=venue_manager_user_A)
        venue_create_url = reverse('venue-list')
        venue_data_A = {'name': 'Venue by A', 'address': 'A Address', 'capacity': 100}
        response = api_client.post(venue_create_url, venue_data_A, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        venue_A_id = response.data['id']
        venue_A_url = reverse('venue-detail', kwargs={'pk': venue_A_id})

        # User A can retrieve their own Venue
        response = api_client.get(venue_A_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Venue by A'

        # User A can update their own Venue
        response = api_client.patch(venue_A_url, {'name': 'Venue by A Updated'}, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Venue by A Updated'

        # User B (another Venue Manager) cannot update User A's Venue
        api_client.force_authenticate(user=venue_manager_user_B)
        response = api_client.patch(venue_A_url, {'name': 'Attempt Update by B'}, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Customer User cannot update User A's Venue
        api_client.force_authenticate(user=customer_user)
        response = api_client.patch(venue_A_url, {'name': 'Attempt Update by Customer'}, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Admin user can update User A's Venue
        api_client.force_authenticate(user=admin_user)
        response = api_client.patch(venue_A_url, {'name': 'Venue by A Updated by Admin'}, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Venue by A Updated by Admin'

        # User B (another Venue Manager) cannot delete User A's Venue
        api_client.force_authenticate(user=venue_manager_user_B)
        response = api_client.delete(venue_A_url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Customer User cannot delete User A's Venue
        api_client.force_authenticate(user=customer_user)
        response = api_client.delete(venue_A_url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # User A can delete their own Venue
        api_client.force_authenticate(user=venue_manager_user_A)
        response = api_client.delete(venue_A_url)
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify it's deleted
        response = api_client.get(venue_A_url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Admin can delete any venue (re-create for this test)
        response = api_client.post(venue_create_url, venue_data_A, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        venue_A_id_admin_del = response.data['id']
        venue_A_url_admin_del = reverse('venue-detail', kwargs={'pk': venue_A_id_admin_del})
        api_client.force_authenticate(user=admin_user)
        response = api_client.delete(venue_A_url_admin_del)
        assert response.status_code == status.HTTP_204_NO_CONTENT


    # --- Scenario 2: Event Organizer Access Control ---
    def test_event_organizer_permissions_on_own_and_others_events(self, api_client, event_organizer_user_C, event_organizer_user_D, customer_user, admin_user, venue_manager_user_A, sample_category):
        # Venue needs to be created first, by a Venue Manager or Admin
        api_client.force_authenticate(user=venue_manager_user_A)
        venue_url = reverse('venue-list')
        venue_data = {'name': 'Venue for Events', 'address': 'Event Venue St', 'capacity': 150}
        response = api_client.post(venue_url, venue_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        created_venue_id = response.data['id']

        # User C (Event Organizer) creates an Event
        api_client.force_authenticate(user=event_organizer_user_C)
        event_create_url = reverse('event-list')
        event_data_C = {
            'name': 'Event by C', 'venue': created_venue_id, 'ticket_price': 30,
            'start_time': "2030-01-01T10:00:00Z", 'end_time': "2030-01-01T12:00:00Z",
            'categories': [sample_category.name]
        }
        response = api_client.post(event_create_url, event_data_C, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        event_C_id = response.data['id']
        event_C_url = reverse('event-detail', kwargs={'pk': event_C_id})

        # User C can retrieve their own Event
        response = api_client.get(event_C_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Event by C'

        # User C can update their own Event
        response = api_client.patch(event_C_url, {'name': 'Event by C Updated'}, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Event by C Updated'

        # User D (another Event Organizer) cannot update User C's Event
        api_client.force_authenticate(user=event_organizer_user_D)
        response = api_client.patch(event_C_url, {'name': 'Attempt Update by D'}, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Customer User cannot update User C's Event
        api_client.force_authenticate(user=customer_user)
        response = api_client.patch(event_C_url, {'name': 'Attempt Update by Customer'}, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Admin user can update User C's Event
        api_client.force_authenticate(user=admin_user)
        response = api_client.patch(event_C_url, {'name': 'Event by C Updated by Admin'}, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Event by C Updated by Admin'

        # User D (another Event Organizer) cannot delete User C's Event
        api_client.force_authenticate(user=event_organizer_user_D)
        response = api_client.delete(event_C_url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Customer User cannot delete User C's Event
        api_client.force_authenticate(user=customer_user)
        response = api_client.delete(event_C_url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # User C can delete their own Event
        api_client.force_authenticate(user=event_organizer_user_C)
        response = api_client.delete(event_C_url)
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify it's deleted
        response = api_client.get(event_C_url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Admin can delete any event (re-create for this test)
        response = api_client.post(event_create_url, event_data_C, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        event_C_id_admin_del = response.data['id']
        event_C_url_admin_del = reverse('event-detail', kwargs={'pk': event_C_id_admin_del})
        api_client.force_authenticate(user=admin_user)
        response = api_client.delete(event_C_url_admin_del)
        assert response.status_code == status.HTTP_204_NO_CONTENT

    # --- Scenario 3: Cross-Role Restrictions ---
    def test_venue_manager_cannot_create_event(self, api_client, venue_manager_user_A, sample_category):
        # Setup: Venue Manager needs a venue to try to create an event for
        api_client.force_authenticate(user=venue_manager_user_A)
        venue_url = reverse('venue-list')
        venue_data = {'name': 'VM Venue for Event Test', 'address': 'VM Event Test St', 'capacity': 50}
        response = api_client.post(venue_url, venue_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        vm_venue_id = response.data['id']

        # Venue Manager (User A, not an Event Organizer) attempts to create an Event
        event_create_url = reverse('event-list')
        event_data = {
            'name': 'Event by VM A', 'venue': vm_venue_id, 'ticket_price': 10,
            'start_time': "2030-02-01T10:00:00Z", 'end_time': "2030-02-01T12:00:00Z",
            'categories': [sample_category.name]
            # Organizer is set by perform_create in viewset, which will be venue_manager_user_A
            # The permission check IsAdminUser | IsEventOrganizer should deny this.
        }
        response = api_client.post(event_create_url, event_data, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_event_organizer_cannot_create_venue(self, api_client, event_organizer_user_C):
        # Event Organizer (User C, not a Venue Manager) attempts to create a Venue
        api_client.force_authenticate(user=event_organizer_user_C)
        venue_create_url = reverse('venue-list')
        venue_data = {'name': 'Venue by EO C', 'address': 'EO C Address', 'capacity': 70}
        # Owner is set by perform_create in viewset to event_organizer_user_C
        # The permission check IsAdminUser | IsVenueManager should deny this.
        response = api_client.post(venue_create_url, venue_data, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN


    # --- Test Admin full access (covered implicitly, but one explicit check) ---
    def test_admin_can_manage_any_venue_and_event(self, api_client, admin_user, venue_manager_user_A, event_organizer_user_C, sample_category):
        # VM User A creates a venue
        api_client.force_authenticate(user=venue_manager_user_A)
        venue_data_A = {'name': 'Venue by A for Admin Test', 'address': 'A Address Admin', 'capacity': 100}
        response = api_client.post(reverse('venue-list'), venue_data_A, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        venue_A_id = response.data['id']
        venue_A_url = reverse('venue-detail', kwargs={'pk': venue_A_id})

        # EO User C creates an event in Venue A
        api_client.force_authenticate(user=event_organizer_user_C)
        event_data_C = {
            'name': 'Event by C for Admin Test', 'venue': venue_A_id, 'ticket_price': 30,
            'start_time': "2030-03-01T10:00:00Z", 'end_time': "2030-03-01T12:00:00Z",
            'categories': [sample_category.name]
        }
        response = api_client.post(reverse('event-list'), event_data_C, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        event_C_id = response.data['id']
        event_C_url = reverse('event-detail', kwargs={'pk': event_C_id})

        # Admin logs in
        api_client.force_authenticate(user=admin_user)

        # Admin can retrieve Venue A
        response = api_client.get(venue_A_url)
        assert response.status_code == status.HTTP_200_OK
        # Admin can update Venue A
        response = api_client.patch(venue_A_url, {'name': 'Venue A Updated by Admin'}, format='json')
        assert response.status_code == status.HTTP_200_OK

        # Admin can retrieve Event C
        response = api_client.get(event_C_url)
        assert response.status_code == status.HTTP_200_OK
        # Admin can update Event C
        response = api_client.patch(event_C_url, {'name': 'Event C Updated by Admin'}, format='json')
        assert response.status_code == status.HTTP_200_OK

        # Admin can delete Event C
        response = api_client.delete(event_C_url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        # Admin can delete Venue A
        response = api_client.delete(venue_A_url)
        assert response.status_code == status.HTTP_204_NO_CONTENT

    # --- Booking Access (already partially covered in original test file, enhanced here) ---
    # Test if Event Organizer can view bookings for their events
    def test_event_organizer_booking_list_and_retrieve_access(self, api_client, event_organizer_user_C, customer_user, venue_manager_user_A, sample_category):
        # Venue setup
        api_client.force_authenticate(user=venue_manager_user_A)
        venue_resp = api_client.post(reverse('venue-list'), {'name': 'Venue for Booking Test EO', 'address': 'EO Booking St', 'capacity': 50}, format='json')
        assert venue_resp.status_code == status.HTTP_201_CREATED
        venue_id = venue_resp.data['id']

        # Event Organizer C creates an event
        api_client.force_authenticate(user=event_organizer_user_C)
        event_data = {'name': 'EO C Event for Bookings', 'venue': venue_id, 'ticket_price': 10, 'start_time': "2030-04-01T10:00:00Z", 'end_time': "2030-04-01T12:00:00Z", 'categories': [sample_category.name]}
        event_resp = api_client.post(reverse('event-list'), event_data, format='json')
        assert event_resp.status_code == status.HTTP_201_CREATED
        event_id = event_resp.data['id']

        # Customer books the event
        api_client.force_authenticate(user=customer_user)
        booking_data = {'event': event_id, 'number_of_tickets': 1}
        booking_resp = api_client.post(reverse('booking-list'), booking_data, format='json')
        assert booking_resp.status_code == status.HTTP_201_CREATED
        booking_id = booking_resp.data['id']

        # Event Organizer C lists bookings, should see the booking for their event
        api_client.force_authenticate(user=event_organizer_user_C)
        response = api_client.get(reverse('booking-list'))
        assert response.status_code == status.HTTP_200_OK
        assert any(b['id'] == booking_id for b in response.data.get('results', [])), "Booking for EO's event not found"

        # Event Organizer C retrieves the booking for their event
        # According to BookingViewSet.get_queryset, this should be allowed.
        response = api_client.get(reverse('booking-detail', kwargs={'pk': booking_id}))
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == booking_id

    # Test if Venue Manager can view bookings for events at their venues
    def test_venue_manager_booking_list_and_retrieve_access(self, api_client, venue_manager_user_A, event_organizer_user_C, customer_user, sample_category):
        # Venue Manager A creates a venue
        api_client.force_authenticate(user=venue_manager_user_A)
        venue_resp = api_client.post(reverse('venue-list'), {'name': 'VM A Venue for Bookings', 'address': 'VM A Booking St', 'capacity': 60}, format='json')
        assert venue_resp.status_code == status.HTTP_201_CREATED
        venue_id = venue_resp.data['id']

        # Event Organizer C creates an event at VM A's venue
        api_client.force_authenticate(user=event_organizer_user_C)
        event_data = {'name': 'Event at VM A Venue', 'venue': venue_id, 'ticket_price': 12, 'start_time': "2030-05-01T10:00:00Z", 'end_time': "2030-05-01T12:00:00Z", 'categories': [sample_category.name]}
        event_resp = api_client.post(reverse('event-list'), event_data, format='json')
        assert event_resp.status_code == status.HTTP_201_CREATED
        event_id = event_resp.data['id']

        # Customer books this event
        api_client.force_authenticate(user=customer_user)
        booking_data = {'event': event_id, 'number_of_tickets': 2}
        booking_resp = api_client.post(reverse('booking-list'), booking_data, format='json')
        assert booking_resp.status_code == status.HTTP_201_CREATED
        booking_id = booking_resp.data['id']

        # Venue Manager A lists bookings, should see the booking for event at their venue
        api_client.force_authenticate(user=venue_manager_user_A)
        response = api_client.get(reverse('booking-list'))
        assert response.status_code == status.HTTP_200_OK
        assert any(b['id'] == booking_id for b in response.data.get('results', [])), "Booking for event at VM's venue not found"

        # Venue Manager A retrieves the booking for event at their venue
        # According to BookingViewSet.get_queryset, this should be allowed.
        response = api_client.get(reverse('booking-detail', kwargs={'pk': booking_id}))
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == booking_id

    # Test for customer listing/retrieving only their own bookings (already in original test, ensure it's robust)
    def test_customer_can_only_access_own_bookings(self, api_client, customer_user, admin_user, venue_manager_user_A, event_organizer_user_C, sample_category):
        # Setup a venue and an event by admin/organizer
        api_client.force_authenticate(user=venue_manager_user_A)
        venue_resp = api_client.post(reverse('venue-list'), {'name': 'Venue for Customer Booking Test', 'address': 'Cust Booking St', 'capacity': 50}, format='json')
        venue_id = venue_resp.data['id']

        api_client.force_authenticate(user=event_organizer_user_C)
        event_data = {'name': 'Event for Customer Booking', 'venue': venue_id, 'ticket_price': 5, 'start_time': "2030-06-01T10:00:00Z", 'end_time': "2030-06-01T12:00:00Z", 'categories': [sample_category.name]}
        event_resp = api_client.post(reverse('event-list'), event_data, format='json')
        event_id = event_resp.data['id']

        # Customer creates their booking
        api_client.force_authenticate(user=customer_user)
        booking_data_own = {'event': event_id, 'number_of_tickets': 1}
        own_booking_resp = api_client.post(reverse('booking-list'), booking_data_own, format='json')
        assert own_booking_resp.status_code == status.HTTP_201_CREATED
        own_booking_id = own_booking_resp.data['id']

        # Admin creates another booking for the same event (or a different one)
        api_client.force_authenticate(user=admin_user)
        booking_data_other = {'event': event_id, 'number_of_tickets': 2} # Admin books for themselves
        other_booking_resp = api_client.post(reverse('booking-list'), booking_data_other, format='json')
        assert other_booking_resp.status_code == status.HTTP_201_CREATED
        other_booking_id = other_booking_resp.data['id']

        # Customer lists bookings
        api_client.force_authenticate(user=customer_user)
        response = api_client.get(reverse('booking-list'))
        assert response.status_code == status.HTTP_200_OK
        booking_ids_in_list = [b['id'] for b in response.data.get('results', [])]
        assert own_booking_id in booking_ids_in_list
        assert other_booking_id not in booking_ids_in_list
        assert len(booking_ids_in_list) == 1

        # Customer retrieves their own booking
        response = api_client.get(reverse('booking-detail', kwargs={'pk': own_booking_id}))
        assert response.status_code == status.HTTP_200_OK

        # Customer attempts to retrieve other user's booking
        response = api_client.get(reverse('booking-detail', kwargs={'pk': other_booking_id}))
        # This should be denied by IsOwnerOrAdmin or result in 404 due to queryset filtering
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]

    # Test that read-only access is allowed for unauthenticated users for Venues and Events
    def test_unauthenticated_user_readonly_access_to_venues_and_events(self, api_client, venue_manager_user_A, event_organizer_user_C, sample_category):
        # Setup: Create a venue and an event
        api_client.force_authenticate(user=venue_manager_user_A)
        venue_resp = api_client.post(reverse('venue-list'), {'name': 'Public Venue', 'address': 'Public St', 'capacity': 100}, format='json')
        venue_id = venue_resp.data['id']

        api_client.force_authenticate(user=event_organizer_user_C)
        event_data = {'name': 'Public Event', 'venue': venue_id, 'ticket_price': 20, 'start_time': "2030-07-01T10:00:00Z", 'end_time': "2030-07-01T12:00:00Z", 'categories': [sample_category.name]}
        event_resp = api_client.post(reverse('event-list'), event_data, format='json')
        event_id = event_resp.data['id']

        # Unauthenticate client
        api_client.force_authenticate(user=None)

        # List Venues
        response = api_client.get(reverse('venue-list'))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data.get('results', [])) > 0

        # Retrieve Venue
        response = api_client.get(reverse('venue-detail', kwargs={'pk': venue_id}))
        assert response.status_code == status.HTTP_200_OK

        # List Events
        response = api_client.get(reverse('event-list'))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data.get('results', [])) > 0

        # Retrieve Event
        response = api_client.get(reverse('event-detail', kwargs={'pk': event_id}))
        assert response.status_code == status.HTTP_200_OK

        # Attempt to create, update, delete (should be denied)
        response = api_client.post(reverse('venue-list'), {'name': 'Attempt Create', 'address': 'Attempt', 'capacity': 10}, format='json')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED # Or 403 if IsAuthenticatedOrReadOnly is structured differently

        response = api_client.patch(reverse('venue-detail', kwargs={'pk': venue_id}), {'name': 'Attempt Update'}, format='json')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        response = api_client.delete(reverse('venue-detail', kwargs={'pk': venue_id}))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
```

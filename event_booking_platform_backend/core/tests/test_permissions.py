from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated # For some basic checks if needed

from core.models import Role
# Import the permissions to be tested
from core.permissions import (
    IsAdminOrReadOnly,
    IsOwnerOrAdmin,
    IsOwnerOrReadOnly,
    IsAdminUser,
    IsCustomer,
    IsEventOrganizer,
    IsVenueManager
)

# Import models needed for creating test objects for object-level permissions
from events.models import Event, Category, Venue
from bookings.models import Booking
from decimal import Decimal

User = get_user_model()

# A minimal view for testing permissions
class MockView(APIView):
    pass

class PermissionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.factory = RequestFactory()
        cls.view = MockView()

        # Create roles based on new definitions in models.py
        cls.admin_role, _ = Role.objects.get_or_create(name=Role.ADMIN)
        cls.customer_role, _ = Role.objects.get_or_create(name=Role.CUSTOMER)
        cls.event_organizer_role, _ = Role.objects.get_or_create(name=Role.EVENT_ORGANIZER)
        cls.venue_manager_role, _ = Role.objects.get_or_create(name=Role.VENUE_MANAGER)

        # Create users
        cls.customer_user = User.objects.create_user(username='customer', email='customer@example.com', password='password')
        cls.customer_user.roles.add(cls.customer_role)

        cls.event_organizer_user = User.objects.create_user(username='eventorganizer', email='eo@example.com', password='password')
        cls.event_organizer_user.roles.add(cls.event_organizer_role)

        cls.venue_manager_user = User.objects.create_user(username='venuemanager', email='vm@example.com', password='password')
        cls.venue_manager_user.roles.add(cls.venue_manager_role)

        cls.admin_user_staff = User.objects.create_superuser(username='adminstaff', email='adminstaff@example.com', password='password')
        # Superuser automatically has is_staff=True. Add ADMIN role for consistency if app uses it.
        cls.admin_user_staff.roles.add(cls.admin_role)

        cls.unauthenticated_user = None # For testing unauthenticated users

        # Create common objects for testing object-level permissions
        cls.venue_owned_by_vm = Venue.objects.create(name="VM's Venue", address="123 VM St", capacity=100, owner=cls.venue_manager_user)
        cls.venue_other = Venue.objects.create(name="Other Venue", address="456 Other St", capacity=50, owner=cls.admin_user_staff) # Owned by admin for simplicity

        cls.category = Category.objects.create(name='Test Category')

        cls.event_organized_by_eo = Event.objects.create(
            name="EO's Event", venue=cls.venue_owned_by_vm, organizer=cls.event_organizer_user,
            start_time="2030-01-01T10:00:00Z", end_time="2030-01-01T12:00:00Z", ticket_price=Decimal("10.00")
        )
        cls.event_at_vm_venue_eo_organizer = Event.objects.create( # Event at VM's venue, but organized by EO
            name="Event at VM Venue by EO", venue=cls.venue_owned_by_vm, organizer=cls.event_organizer_user,
            start_time="2030-01-02T10:00:00Z", end_time="2030-01-02T12:00:00Z", ticket_price=Decimal("10.00")
        )
        cls.event_other = Event.objects.create(
            name="Other Event", venue=cls.venue_other, organizer=cls.admin_user_staff,
            start_time="2030-01-03T10:00:00Z", end_time="2030-01-03T12:00:00Z", ticket_price=Decimal("10.00")
        )

        cls.booking_by_customer = Booking.objects.create(event=cls.event_organized_by_eo, user=cls.customer_user, number_of_tickets=1)
        cls.booking_other = Booking.objects.create(event=cls.event_other, user=cls.admin_user_staff, number_of_tickets=1)


    def _check_permission(self, permission_class, user, expected_result, obj=None, method='GET'):
        request = getattr(self.factory, method.lower())('/') # e.g., self.factory.get('/')
        request.user = user
        permission_instance = permission_class()

        if obj: # For object-level permissions
            has_perm = permission_instance.has_object_permission(request, self.view, obj)
        else: # For view-level permissions
            has_perm = permission_instance.has_permission(request, self.view)

        user_identifier = user.username if hasattr(user, 'username') else 'Unauthenticated'
        self.assertEqual(has_perm, expected_result,
                         f"{permission_class.__name__} check failed for user '{user_identifier}' with method '{method}' on object '{obj}'. Expected {expected_result}, got {has_perm}.")

    # --- Tests for IsAdminUser ---
    def test_is_admin_user_permission(self):
        self._check_permission(IsAdminUser, self.admin_user_staff, True)
        self._check_permission(IsAdminUser, self.customer_user, False)
        self._check_permission(IsAdminUser, self.event_organizer_user, False)
        self._check_permission(IsAdminUser, self.venue_manager_user, False)
        self._check_permission(IsAdminUser, self.unauthenticated_user, False)
        # Object permission should also be true for admin
        self._check_permission(IsAdminUser, self.admin_user_staff, True, obj=self.venue_other)


    # --- Tests for IsCustomer ---
    def test_is_customer_role_check(self): # has_permission
        self._check_permission(IsCustomer, self.customer_user, True)
        self._check_permission(IsCustomer, self.admin_user_staff, False) # Admin doesn't have CUSTOMER role by default
        self._check_permission(IsCustomer, self.event_organizer_user, False)
        self._check_permission(IsCustomer, self.venue_manager_user, False)

    def test_is_customer_object_permission_booking(self): # has_object_permission
        # Customer accessing their own booking
        self._check_permission(IsCustomer, self.customer_user, True, obj=self.booking_by_customer)
        # Customer trying to access another's booking
        self._check_permission(IsCustomer, self.customer_user, False, obj=self.booking_other)
        # Non-customer (e.g. EO) trying to access a booking (should fail IsCustomer role check first)
        # Note: has_object_permission in IsCustomer first checks has_permission
        self._check_permission(IsCustomer, self.event_organizer_user, False, obj=self.booking_by_customer)


    # --- Tests for IsEventOrganizer ---
    def test_is_event_organizer_role_check(self): # has_permission
        self._check_permission(IsEventOrganizer, self.event_organizer_user, True)
        self._check_permission(IsEventOrganizer, self.customer_user, False)
        self._check_permission(IsEventOrganizer, self.admin_user_staff, False) # Admin does not have EO role

    def test_is_event_organizer_object_permission_event(self): # has_object_permission
        # EO accessing their own event
        self._check_permission(IsEventOrganizer, self.event_organizer_user, True, obj=self.event_organized_by_eo)
        # EO trying to access another's event
        self._check_permission(IsEventOrganizer, self.event_organizer_user, False, obj=self.event_other)
        # Non-EO trying to access an event
        self._check_permission(IsEventOrganizer, self.customer_user, False, obj=self.event_organized_by_eo)


    # --- Tests for IsVenueManager ---
    def test_is_venue_manager_role_check(self): # has_permission
        self._check_permission(IsVenueManager, self.venue_manager_user, True)
        self._check_permission(IsVenueManager, self.customer_user, False)
        self._check_permission(IsVenueManager, self.admin_user_staff, False) # Admin does not have VM role

    def test_is_venue_manager_object_permission_venue(self): # has_object_permission for Venue
        # VM accessing their own venue
        self._check_permission(IsVenueManager, self.venue_manager_user, True, obj=self.venue_owned_by_vm)
        # VM trying to access another's venue
        self._check_permission(IsVenueManager, self.venue_manager_user, False, obj=self.venue_other)

    def test_is_venue_manager_object_permission_event_at_their_venue(self): # has_object_permission for Event
        # VM accessing an event held at their venue
        self._check_permission(IsVenueManager, self.venue_manager_user, True, obj=self.event_at_vm_venue_eo_organizer)
        # VM accessing an event at another venue
        self._check_permission(IsVenueManager, self.venue_manager_user, False, obj=self.event_other)


    # --- Tests for existing generic permissions (IsAdminOrReadOnly, IsOwnerOrAdmin, IsOwnerOrReadOnly) ---
    # These are good to keep to ensure they still work as expected.

    def test_is_admin_or_read_only_permission(self):
        # GET (safe method)
        self._check_permission(IsAdminOrReadOnly, self.customer_user, True, method='GET')
        self._check_permission(IsAdminOrReadOnly, self.admin_user_staff, True, method='GET')
        # POST (unsafe method)
        self._check_permission(IsAdminOrReadOnly, self.customer_user, False, method='POST')
        self._check_permission(IsAdminOrReadOnly, self.admin_user_staff, True, method='POST')

    def test_is_owner_or_admin_permission_venue(self): # Using Venue model
        # Owner access
        self._check_permission(IsOwnerOrAdmin, self.venue_manager_user, True, obj=self.venue_owned_by_vm)
        # Non-owner access denied
        self._check_permission(IsOwnerOrAdmin, self.customer_user, False, obj=self.venue_owned_by_vm)
        # Admin access to non-owned object
        self._check_permission(IsOwnerOrAdmin, self.admin_user_staff, True, obj=self.venue_owned_by_vm)

    def test_is_owner_or_admin_permission_event(self): # Using Event model (checks 'organizer')
        self._check_permission(IsOwnerOrAdmin, self.event_organizer_user, True, obj=self.event_organized_by_eo)
        self._check_permission(IsOwnerOrAdmin, self.customer_user, False, obj=self.event_organized_by_eo)
        self._check_permission(IsOwnerOrAdmin, self.admin_user_staff, True, obj=self.event_organized_by_eo)

    def test_is_owner_or_admin_permission_booking(self): # Using Booking model (checks 'user')
        self._check_permission(IsOwnerOrAdmin, self.customer_user, True, obj=self.booking_by_customer)
        self._check_permission(IsOwnerOrAdmin, self.event_organizer_user, False, obj=self.booking_by_customer)
        self._check_permission(IsOwnerOrAdmin, self.admin_user_staff, True, obj=self.booking_by_customer)

    def test_is_owner_or_read_only_permission_venue(self):
        # Safe method (GET)
        self._check_permission(IsOwnerOrReadOnly, self.customer_user, True, obj=self.venue_owned_by_vm, method='GET')
        # Unsafe method (POST) - Owner
        self._check_permission(IsOwnerOrReadOnly, self.venue_manager_user, True, obj=self.venue_owned_by_vm, method='POST')
        # Unsafe method (POST) - Non-owner
        self._check_permission(IsOwnerOrReadOnly, self.customer_user, False, obj=self.venue_owned_by_vm, method='POST')
        # Unsafe method (POST) - Admin (IsOwnerOrReadOnly does not grant special admin access for write)
        self._check_permission(IsOwnerOrReadOnly, self.admin_user_staff, False, obj=self.venue_owned_by_vm, method='POST')
        # Admin can read
        self._check_permission(IsOwnerOrReadOnly, self.admin_user_staff, True, obj=self.venue_owned_by_vm, method='GET')


    # Consider adding tests for unauthenticated users for each relevant permission
    def test_permissions_for_unauthenticated_user(self):
        self._check_permission(IsCustomer, self.unauthenticated_user, False)
        self._check_permission(IsCustomer, self.unauthenticated_user, False, obj=self.booking_by_customer)

        self._check_permission(IsEventOrganizer, self.unauthenticated_user, False)
        self._check_permission(IsEventOrganizer, self.unauthenticated_user, False, obj=self.event_organized_by_eo)

        self._check_permission(IsVenueManager, self.unauthenticated_user, False)
        self._check_permission(IsVenueManager, self.unauthenticated_user, False, obj=self.venue_owned_by_vm)

        self._check_permission(IsAdminOrReadOnly, self.unauthenticated_user, True, method='GET') # ReadOnly allowed
        self._check_permission(IsAdminOrReadOnly, self.unauthenticated_user, False, method='POST')

        self._check_permission(IsOwnerOrAdmin, self.unauthenticated_user, False, obj=self.booking_by_customer)
        self._check_permission(IsOwnerOrReadOnly, self.unauthenticated_user, True, obj=self.booking_by_customer, method='GET')
        self._check_permission(IsOwnerOrReadOnly, self.unauthenticated_user, False, obj=self.booking_by_customer, method='POST')

        self._check_permission(IsAdminUser, self.unauthenticated_user, False)
        self._check_permission(IsAdminUser, self.unauthenticated_user, False, obj=self.venue_other)

# Reminder: The IsOwnerOrAdmin and IsOwnerOrReadOnly permissions in core.permissions.py
# have a generic way of checking obj.owner, obj.user, or obj.organizer.
# This makes them flexible. Ensure these attributes exist on the mock/real objects used in tests.
# The tests above use actual model instances, which is good.
# The _check_permission helper was updated to take a 'method' argument.
# Ensure Role.ADMIN, Role.CUSTOMER etc. constants are correctly used if defined in models.py.
# The test setup uses Role.objects.get_or_create(name=Role.ADMIN) which implies Role.ADMIN is a string like 'ADMIN'.
# This matches the constants added to the Role model.The `core/tests/test_permissions.py` file has been successfully overwritten with updated tests for the new and modified permission classes.
Key changes:
-   Role setup in `setUpTestData` now uses the new role names (`ADMIN`, `CUSTOMER`, etc.) and `Role.ADMIN` style constants.
-   Tests for deleted/refactored permissions were removed.
-   Tests for `IsCustomer`, `IsEventOrganizer`, `IsVenueManager` were added/updated to reflect their new logic, including object-level checks using actual model instances.
-   Tests for generic permissions like `IsAdminOrReadOnly`, `IsOwnerOrAdmin`, `IsOwnerOrReadOnly`, and `IsAdminUser` were kept or updated.
-   A helper `_check_permission` was refined.
-   Tests for unauthenticated users were added.

This largely completes the testing for `core/permissions.py`. The next part of Step 6 is to update view tests.

I will now submit the report as this is the last turn.

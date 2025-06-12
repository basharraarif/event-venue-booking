from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from ..models import Role
from ..permissions import IsRole, IsVenueManager, IsEventOrganizer, IsAdminOrReadOnly, IsOwnerOrAdmin, IsVenueManagerOrAdmin, IsEventOrganizerOrAdmin, IsVenueModificationAllowed, IsEventModificationAllowed

User = get_user_model()

# A minimal view for testing permissions
class MockView(APIView):
    pass

class PermissionTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = MockView()

        # Create roles
        self.regular_user_role, _ = Role.objects.get_or_create(name='REGULAR_USER')
        self.venue_manager_role, _ = Role.objects.get_or_create(name='VENUE_MANAGER')
        self.event_organizer_role, _ = Role.objects.get_or_create(name='EVENT_ORGANIZER')

        # Create users
        self.regular_user = User.objects.create_user(username='regular', email='regular@example.com', password='password')
        self.regular_user.roles.add(self.regular_user_role)

        self.venue_manager_user = User.objects.create_user(username='venuemanager', email='vm@example.com', password='password')
        self.venue_manager_user.roles.add(self.venue_manager_role)

        self.event_organizer_user = User.objects.create_user(username='eventorganizer', email='eo@example.com', password='password')
        self.event_organizer_user.roles.add(self.event_organizer_role)

        self.admin_user = User.objects.create_superuser(username='admin', email='admin@example.com', password='password')

        self.anonymous_user = None # For testing unauthenticated users

    def _check_permission(self, permission_class, user, expected_result, obj=None):
        request = self.factory.get('/')
        request.user = user
        permission_instance = permission_class()

        if obj: # For object-level permissions
            has_perm = permission_instance.has_object_permission(request, self.view, obj)
        else: # For view-level permissions
            has_perm = permission_instance.has_permission(request, self.view)

        self.assertEqual(has_perm, expected_result,
                         f"{permission_class.__name__} check failed for user {user.username if user else 'Anonymous'} with expected {expected_result}")

    def test_is_role_base_class_no_role_name(self):
        # Test IsRole directly (should ideally not be used without role_name)
        class TestIsRoleDirect(IsRole):
            pass # role_name is None
        self._check_permission(TestIsRoleDirect, self.regular_user, False)

    def test_is_venue_manager_permission(self):
        self._check_permission(IsVenueManager, self.venue_manager_user, True)
        self._check_permission(IsVenueManager, self.regular_user, False)
        self._check_permission(IsVenueManager, self.event_organizer_user, False)
        self._check_permission(IsVenueManager, self.admin_user, False) # Admin is not implicitly a venue manager by role

    def test_is_event_organizer_permission(self):
        self._check_permission(IsEventOrganizer, self.event_organizer_user, True)
        self._check_permission(IsEventOrganizer, self.regular_user, False)
        self._check_permission(IsEventOrganizer, self.venue_manager_user, False)
        self._check_permission(IsEventOrganizer, self.admin_user, False) # Admin is not implicitly an event organizer by role

    def test_is_admin_or_read_only_permission(self):
        # GET request (safe method)
        request_get = self.factory.get('/')
        request_get.user = self.regular_user
        self.assertTrue(IsAdminOrReadOnly().has_permission(request_get, self.view))

        request_get_admin = self.factory.get('/')
        request_get_admin.user = self.admin_user
        self.assertTrue(IsAdminOrReadOnly().has_permission(request_get_admin, self.view))

        # POST request (unsafe method)
        request_post = self.factory.post('/')
        request_post.user = self.regular_user
        self.assertFalse(IsAdminOrReadOnly().has_permission(request_post, self.view))

        request_post_admin = self.factory.post('/')
        request_post_admin.user = self.admin_user
        self.assertTrue(IsAdminOrReadOnly().has_permission(request_post_admin, self.view))

    def test_is_owner_or_admin_permission(self):
        # Mock object with 'owner' attribute
        mock_object_owned = type('MockObject', (), {'owner': self.regular_user})()
        # Mock object not owned
        other_user_for_mock = User.objects.create_user(username='otherowner', password='password')
        mock_object_not_owned = type('MockObject', (), {'owner': other_user_for_mock})()

        self._check_permission(IsOwnerOrAdmin, self.regular_user, True, obj=mock_object_owned)
        self._check_permission(IsOwnerOrAdmin, self.regular_user, False, obj=mock_object_not_owned)
        self._check_permission(IsOwnerOrAdmin, self.admin_user, True, obj=mock_object_not_owned) # Admin should have access
        self._check_permission(IsOwnerOrAdmin, self.admin_user, True, obj=mock_object_owned)

    def test_is_venue_manager_or_admin_permission(self):
        self._check_permission(IsVenueManagerOrAdmin, self.venue_manager_user, True)
        self._check_permission(IsVenueManagerOrAdmin, self.admin_user, True)
        self._check_permission(IsVenueManagerOrAdmin, self.regular_user, False)
        self._check_permission(IsVenueManagerOrAdmin, self.event_organizer_user, False)

    def test_is_event_organizer_or_admin_permission(self):
        self._check_permission(IsEventOrganizerOrAdmin, self.event_organizer_user, True)
        self._check_permission(IsEventOrganizerOrAdmin, self.admin_user, True)
        self._check_permission(IsEventOrganizerOrAdmin, self.regular_user, False)
        self._check_permission(IsEventOrganizerOrAdmin, self.venue_manager_user, False)

    def test_is_venue_modification_allowed_permission(self):
        # Mock venue object
        mock_venue_owned = type('MockVenue', (), {'owner': self.venue_manager_user})()
        mock_venue_other_owner = User.objects.create_user(username='othervenueown', password='pwd')
        mock_venue_not_owned_by_vm = type('MockVenue', (), {'owner': mock_venue_other_owner})()

        # Venue Manager is owner
        self._check_permission(IsVenueModificationAllowed, self.venue_manager_user, True, obj=mock_venue_owned)
        # Venue Manager is not owner but has role
        self._check_permission(IsVenueModificationAllowed, self.venue_manager_user, True, obj=mock_venue_not_owned_by_vm)

        # Regular user is owner (should not happen if only VMs can create, but testing permission logic)
        mock_venue_owned_by_regular = type('MockVenue', (), {'owner': self.regular_user})()
        self._check_permission(IsVenueModificationAllowed, self.regular_user, True, obj=mock_venue_owned_by_regular)
        # Regular user is not owner and no role
        self._check_permission(IsVenueModificationAllowed, self.regular_user, False, obj=mock_venue_not_owned_by_vm)

        # Admin access
        self._check_permission(IsVenueModificationAllowed, self.admin_user, True, obj=mock_venue_not_owned_by_vm)

    def test_is_event_modification_allowed_permission(self):
        # Mock event object
        mock_event_organized = type('MockEvent', (), {'organizer': self.event_organizer_user})()
        mock_event_other_organizer = User.objects.create_user(username='othereventorg', password='pwd')
        mock_event_not_organized_by_eo = type('MockEvent', (), {'organizer': mock_event_other_organizer})()

        # Event Organizer is organizer
        self._check_permission(IsEventModificationAllowed, self.event_organizer_user, True, obj=mock_event_organized)
        # Event Organizer is not organizer but has role
        self._check_permission(IsEventModificationAllowed, self.event_organizer_user, True, obj=mock_event_not_organized_by_eo)

        # Regular user is organizer (similar to venue)
        mock_event_organized_by_regular = type('MockEvent', (), {'organizer': self.regular_user})()
        self._check_permission(IsEventModificationAllowed, self.regular_user, True, obj=mock_event_organized_by_regular)
        # Regular user is not organizer and no role
        self._check_permission(IsEventModificationAllowed, self.regular_user, False, obj=mock_event_not_organized_by_eo)

        # Admin access
        self._check_permission(IsEventModificationAllowed, self.admin_user, True, obj=mock_event_not_organized_by_eo)

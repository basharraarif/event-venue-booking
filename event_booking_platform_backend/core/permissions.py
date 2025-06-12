from rest_framework import permissions
from .models import Role # Import Role model

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Allows full access to admin users, read-only access to others.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff

class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object or admins to edit it.
    Assumes the model instance has an 'owner' (for Venues) or 'organizer' (for Events) or 'user' (for Bookings) attribute.
    Admins are always allowed.
    """
    def has_object_permission(self, request, view, obj):
        if request.user and request.user.is_staff:
            return True
        # Check for 'owner', 'organizer', or 'user'
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        if hasattr(obj, 'organizer'): # Specific for Event model
            return obj.organizer == request.user
        if hasattr(obj, 'user'): # Common for objects like Bookings
            return obj.user == request.user
        return False

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it, otherwise read-only.
    Assumes the model instance has an 'owner', 'user', or 'organizer' attribute.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        # Check for 'owner', 'user', 'organizer'
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        if hasattr(obj, 'user'):
            return obj.user == request.user
        if hasattr(obj, 'organizer'):
            return obj.organizer == request.user
        return False

class IsRole(permissions.BasePermission):
    """
    Base permission class to check if a user has a specific role.
    `role_name` attribute must be set on the subclass.
    """
    role_name = None

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if self.role_name is None:
            # This should not happen if subclasses are defined correctly
            return False
        try:
            # Check if the user has the required role through the ManyToManyField
            return request.user.roles.filter(name=self.role_name).exists()
        except Role.DoesNotExist: # Should not happen if roles are pre-populated
            return False
        except Exception: # Catch any other potential errors during role check
            return False

class IsVenueManager(IsRole):
    role_name = 'VENUE_MANAGER'

class IsEventOrganizer(IsRole):
    role_name = 'EVENT_ORGANIZER'

# Example of a combined permission for Venue modification:
# This would be used in VenueViewSet like:
# permission_classes = [IsAuthenticated, (IsVenueOwnerOrManagerOrAdmin)]
# where IsVenueOwnerOrManagerOrAdmin is a composite permission.
# For simplicity in this step, we will apply permissions directly in views using logical OR.
# Example: permission_classes = [IsAuthenticated, (IsOwnerOrAdmin | IsVenueManager)]
# DRF's default behavior with a list of permissions is AND. To achieve OR,
# you typically use bitwise operators with custom permission classes that support it,
# or structure has_permission to handle OR logic if it's a single complex permission class.
# For this task, we'll use DRF's default ANDing of permissions listed in permission_classes
# and rely on combining them appropriately in the viewsets.
# For example, for VenueViewSet update/partial_update/destroy:
# permission_classes = [IsAuthenticated, (IsOwnerOrAdmin | IsVenueManager)]
# This requires IsOwnerOrAdmin and IsVenueManager to be composable with OR,
# or we create a specific permission class like IsVenueOwnerOrManagerOrAdmin.

# Let's define a more specific one for clarity in views for now.
class IsVenueOwnerOrManager(permissions.BasePermission):
    """
    Allows access if the user is the owner of the venue OR has the VENUE_MANAGER role.
    This is for object-level permissions.
    """
    def has_object_permission(self, request, view, obj):
        is_owner = False
        if hasattr(obj, 'owner'):
            is_owner = obj.owner == request.user

        is_venue_manager_role = False
        if request.user and request.user.is_authenticated:
            is_venue_manager_role = request.user.roles.filter(name='VENUE_MANAGER').exists()

        return is_owner or is_venue_manager_role

class IsEventOwnerOrOrganizer(permissions.BasePermission):
    """
    Allows access if the user is the organizer of the event OR has the EVENT_ORGANIZER role.
    This is for object-level permissions.
    """
    def has_object_permission(self, request, view, obj):
        is_organizer_field = False
        if hasattr(obj, 'organizer'):
            is_organizer_field = obj.organizer == request.user

        is_event_organizer_role = False
        if request.user and request.user.is_authenticated:
            is_event_organizer_role = request.user.roles.filter(name='EVENT_ORGANIZER').exists()

        return is_organizer_field or is_event_organizer_role

class IsVenueManagerOrAdmin(permissions.BasePermission):
    """
    Allows access if the user has the VENUE_MANAGER role OR is an admin.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            (request.user.roles.filter(name='VENUE_MANAGER').exists() or request.user.is_staff)
        )

class IsEventOrganizerOrAdmin(permissions.BasePermission):
    """
    Allows access if the user has the EVENT_ORGANIZER role OR is an admin.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            (request.user.roles.filter(name='EVENT_ORGANIZER').exists() or request.user.is_staff)
        )

class IsVenueModificationAllowed(permissions.BasePermission):
    """
    Allows object modification if the user is the owner, an admin, or a venue manager.
    """
    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated):
            return False

        is_owner = False
        if hasattr(obj, 'owner'): # Ensure obj has 'owner' attribute
            is_owner = obj.owner == request.user

        is_admin = request.user.is_staff
        is_venue_manager = request.user.roles.filter(name='VENUE_MANAGER').exists()

        return is_owner or is_admin or is_venue_manager

class IsEventModificationAllowed(permissions.BasePermission):
    """
    Allows object modification if the user is the organizer, an admin, or an event organizer.
    """
    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated):
            return False

        is_organizer_field = False
        if hasattr(obj, 'organizer'): # Ensure obj has 'organizer' attribute
            is_organizer_field = obj.organizer == request.user

        is_admin = request.user.is_staff
        is_event_organizer_role = request.user.roles.filter(name='EVENT_ORGANIZER').exists()

        return is_organizer_field or is_admin or is_event_organizer_role

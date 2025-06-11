from rest_framework import permissions

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Allows full access to admin users, read-only access to others.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    Assumes the model instance has an 'owner' or 'user' attribute.
    For Events, this might be 'organizer'. For Venues, 'manager' or 'owner'.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        # Check for 'owner', 'user', 'organizer', 'manager'
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        if hasattr(obj, 'user'): # Common for objects directly created by a user
            return obj.user == request.user
        if hasattr(obj, 'organizer'): # Specific for Event model
            return obj.organizer == request.user
        if hasattr(obj, 'manager'): # Specific for Venue model (if 'manager' field is used)
            return obj.manager == request.user
        return False # Deny if no ownership attribute matches

class IsOrganizerOrAdmin(permissions.BasePermission):
    """
    Allows access only to users with the 'organizer' role or admin users.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_organizer or request.user.is_staff

class IsVenueManagerOrAdmin(permissions.BasePermission):
    """
    Allows access only to users with the 'venue_manager' role or admin users.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_venue_manager or request.user.is_staff

class IsOrganizerOwnerOrAdminForObject(permissions.BasePermission):
    """
    Allows full access if the user is an admin.
    For non-admins, allows access if the user is an organizer AND the owner of the object.
    Assumes obj.organizer is the field linking to the User who organized the event.
    """
    def has_object_permission(self, request, view, obj):
        if request.user and request.user.is_staff:
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        # Check if the user is an organizer and the organizer of this specific event
        return request.user.is_organizer and hasattr(obj, 'organizer') and obj.organizer == request.user

class IsVenueManagerOwnerOrAdminForObject(permissions.BasePermission):
    """
    Allows full access if the user is an admin.
    For non-admins, allows access if the user is a venue manager AND the owner/manager of the venue.
    Assumes obj.owner or obj.manager is the field linking to the User who manages the venue.
    """
    def has_object_permission(self, request, view, obj):
        if request.user and request.user.is_staff:
            return True
        if not request.user or not request.user.is_authenticated:
            return False

        is_venue_manager_role = request.user.is_venue_manager
        is_owner = False
        if hasattr(obj, 'owner'): # Check 'owner' field first
            is_owner = obj.owner == request.user
        elif hasattr(obj, 'manager'): # Fallback to 'manager' field
            is_owner = obj.manager == request.user

        return is_venue_manager_role and is_owner

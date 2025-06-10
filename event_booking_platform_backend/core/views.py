from rest_framework import viewsets, permissions
from .models import User
from .serializers import UserSerializer
from drf_spectacular.utils import extend_schema_view, extend_schema

@extend_schema_view(
    list=extend_schema(
        summary="List all users (Authentication Required)",
        description="Retrieves a list of all user accounts. Requires authentication. Access to specific user details beyond one's own may be further restricted by object-level permissions (not yet fully implemented here, e.g. admin sees all, user sees self)."
    ),
    retrieve=extend_schema(
        summary="Retrieve a user (Authentication Required)",
        description="Retrieves the details of a specific user by their ID. Requires authentication. Users might only be able to retrieve their own profiles unless they are administrators."
    ),
    create=extend_schema(
        summary="Create a new user",
        description="Creates a new user account. Requires username, email, and password. Additional fields like phone number and address are optional."
    ),
    update=extend_schema(
        summary="Update a user (full)",
        description="Updates all fields for an existing user. All fields must be provided."
    ),
    partial_update=extend_schema(
        summary="Partially update a user",
        description="Partially updates an existing user. Only the fields provided in the request will be updated."
    ),
    destroy=extend_schema(
        summary="Delete a user",
        description="Deletes an existing user account. This action is typically restricted to administrators."
    )
)
class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing user accounts.
    Provides CRUD operations for users, including custom fields like phone number and address.

    **Permissions:**
    - All actions require authentication (`IsAuthenticated`).
    - Further object-level permissions (e.g., users can only edit themselves, admins can edit anyone)
      would typically be handled by adding another permission class like `IsOwnerOrAdmin` (not implemented in this ViewSet yet).
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated] # Ensures only authenticated users can access

    # To have these docstrings picked up if methods are not explicitly defined,
    # drf-spectacular often relies on the @extend_schema_view decorator as shown above.
    # If methods were overridden, the docstring would be directly on the method.
    # e.g.:
    # def list(self, request, *args, **kwargs):
    #     """Docstring for list action."""
    #     return super().list(request, *args, **kwargs)

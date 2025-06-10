from rest_framework import viewsets, permissions
from .models import User
from .serializers import UserSerializer
from drf_spectacular.utils import extend_schema_view, extend_schema

@extend_schema_view(
    list=extend_schema(
        summary="List all users",
        description="Retrieves a list of all user accounts. Access may be restricted based on user permissions (e.g., admins see all, regular users might see a limited set or only themselves depending on configuration not yet implemented here)."
    ),
    retrieve=extend_schema(
        summary="Retrieve a user",
        description="Retrieves the details of a specific user by their ID."
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
    Permissions: Default DRF permissions are applied (e.g., `DjangoModelPermissionsOrAnonReadOnly` or as configured globally).
    Specific object-level permissions (e.g., users can only edit themselves) would typically be added via `permission_classes`.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    # Example: Add more specific permissions if needed
    # permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdminOrReadOnly] # Custom permission

    # To have these docstrings picked up if methods are not explicitly defined,
    # drf-spectacular often relies on the @extend_schema_view decorator as shown above.
    # If methods were overridden, the docstring would be directly on the method.
    # e.g.:
    # def list(self, request, *args, **kwargs):
    #     """Docstring for list action."""
    #     return super().list(request, *args, **kwargs)

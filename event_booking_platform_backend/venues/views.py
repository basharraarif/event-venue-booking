from rest_framework import viewsets, filters, permissions # Import permissions
from core.permissions import ( # Import custom permissions
    IsAdminOrReadOnly,
    IsVenueManagerOrAdmin,
    IsVenueManagerOwnerOrAdminForObject
)
from .models import Venue
from .serializers import VenueSerializer
from .filters import VenueFilter # Import VenueFilter
from drf_spectacular.utils import extend_schema_view, extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

@extend_schema_view(
    list=extend_schema(
        summary="List all venues",
        description="""Retrieves a list of all available venues.

        **Filtering Options:**
        - `name`: Filter by venue name (partial match, case-insensitive).
        - `address`: Filter by venue address (partial match, case-insensitive).
        - `min_capacity`: Filter by minimum guest capacity (e.g., `?min_capacity=100`).
        - `max_capacity`: Filter by maximum guest capacity (e.g., `?max_capacity=500`).
        - `has_parking`: Filter by availability of parking (boolean: `true` or `false`).
        - `has_public_transport`: Filter by availability of public transport access (boolean: `true` or `false`).

        **Search Fields:** (Use the `search` query parameter)
        - `name`: Search within venue names.
        - `address`: Search within venue addresses.
        - `amenities`: Search within venue amenities description (if amenities is a text field).
        """
    ),
    retrieve=extend_schema(
        summary="Retrieve a venue",
        description="Retrieves the details of a specific venue by its ID."
    ),
    create=extend_schema(
        summary="Create a new venue",
        description="Creates a new venue. All fields as defined in the serializer are available."
    ),
    update=extend_schema(
        summary="Update a venue (full)",
        description="Updates all fields for an existing venue. All fields must be provided."
    ),
    partial_update=extend_schema(
        summary="Partially update a venue",
        description="Partially updates an existing venue. Only the fields provided in the request will be updated."
    ),
    destroy=extend_schema(
        summary="Delete a venue",
        description="Deletes an existing venue. This action is typically restricted."
    )
)
class VenueViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing event venues.
    Provides CRUD operations for venues and supports filtering and searching.
    """
    queryset = Venue.objects.all().order_by('name')
    serializer_class = VenueSerializer
    filterset_class = VenueFilter # Set the filterset class

    # SearchFilter is often configured globally in DEFAULT_FILTER_BACKENDS.
    # These fields will be used by it.
    search_fields = ['name', 'address', 'amenities']

    # permission_classes = [permissions.IsAuthenticatedOrReadOnly] # To be replaced

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action == 'create':
            self.permission_classes = [IsVenueManagerOrAdmin]
        elif self.action in ['update', 'partial_update', 'destroy']:
            self.permission_classes = [IsVenueManagerOwnerOrAdminForObject]
        elif self.action in ['list', 'retrieve']:
            self.permission_classes = [permissions.IsAuthenticatedOrReadOnly]
        else:
            self.permission_classes = [permissions.IsAdminUser]
        return [permission() for permission in self.permission_classes]

from rest_framework import viewsets, permissions
from rest_framework.permissions import IsAuthenticated, IsAdminUser # Added IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from core.permissions import (
    IsEventOrganizerOrAdmin, # Use this for create
    IsEventModificationAllowed # Use this for update/delete
)
from .models import Event, Category
from .serializers import EventSerializer, CategorySerializer
from .filters import EventFilterSet
from drf_spectacular.utils import extend_schema_view, extend_schema

@extend_schema_view(
    list=extend_schema(summary="List all event categories"),
    retrieve=extend_schema(summary="Retrieve an event category"),
    create=extend_schema(summary="Create a new event category"),
    update=extend_schema(summary="Update an event category (full)"),
    partial_update=extend_schema(summary="Partially update an event category"),
    destroy=extend_schema(summary="Delete an event category")
)
class CategoryViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing event categories.
    Provides CRUD operations for categories like 'Music', 'Sports', 'Conference', etc.
    """
    queryset = Category.objects.all().order_by('name')
    serializer_class = CategorySerializer
    permission_classes = [permissions.DjangoModelPermissionsOrAnonReadOnly]

@extend_schema_view(
    list=extend_schema(
        summary="List all events",
        description="""Retrieves a list of all events.

        **Filtering Options (query parameters):**
        - `name`: Filter by event name (partial match, case-insensitive, e.g., `?name=Tech`).
        - `venue`: Filter by venue ID (e.g., `?venue=1`).
        - `organizer`: Filter by organizer (user) ID (e.g., `?organizer=2`).
        - `status`: Filter by event status. Choices: `upcoming`, `ongoing`, `past`, `cancelled` (e.g., `?status=upcoming`).
        - `category_name`: Filter by the exact name of one category associated with the event (e.g., `?category_name=Music`).
        - `start_time_after`: Filter for events starting on or after a given datetime (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS format, e.g., `?start_time_after=2024-01-01`).
        - `start_time_before`: Filter for events starting on or before a given datetime (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS format, e.g., `?start_time_before=2024-12-31`).
        """
    ),
    retrieve=extend_schema(summary="Retrieve an event"),
    create=extend_schema(summary="Create a new event"),
    update=extend_schema(summary="Update an event (full)"),
    partial_update=extend_schema(summary="Partially update an event"),
    destroy=extend_schema(summary="Delete an event")
)
class EventViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing events.
    Provides CRUD operations and supports filtering.
    The `ticket_price` for the event is defined here.
    """
    queryset = Event.objects.select_related('venue', 'organizer').all().order_by('-start_time')
    serializer_class = EventSerializer
    # permission_classes = [permissions.DjangoModelPermissionsOrAnonReadOnly] # To be replaced
    filter_backends = [DjangoFilterBackend]
    filterset_class = EventFilterSet

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action == 'create':
            # User must be Authenticated AND (IsEventOrganizer OR IsAdminUser)
            self.permission_classes = [IsAuthenticated, IsEventOrganizerOrAdmin]
        elif self.action in ['update', 'partial_update', 'destroy']:
            # User must be Authenticated AND (IsOrganizerFieldOwner OR IsEventOrganizerRole OR IsAdmin)
            self.permission_classes = [IsAuthenticated, IsEventModificationAllowed]
        elif self.action in ['list', 'retrieve']:
            # Read-only access for anyone.
            self.permission_classes = [permissions.AllowAny] # Or IsAuthenticatedOrReadOnly / IsAuthenticated
        else:
            # Default to deny, or admin only for other actions
            self.permission_classes = [IsAdminUser] # Or permissions.DenyAll
        return [permission() for permission in self.permission_classes]

    # If search functionality is desired (distinct from filtering):
    # search_fields = ['name', 'description', 'venue__name', 'categories__name']
    # Would need to add 'rest_framework.filters.SearchFilter' to filter_backends.
    # For now, relying on detailed filtering via EventFilterSet.
    # ordering_fields = ['start_time', 'name', 'status', 'venue__name'] # For ordering
    # Would need to add 'rest_framework.filters.OrderingFilter' to filter_backends.

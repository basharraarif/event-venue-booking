from rest_framework import viewsets, permissions
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from core.permissions import IsEventOrganizer # Using the updated IsEventOrganizer
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
        - Create: Authenticated Admin or EventOrganizer.
        - Update/Delete: Authenticated Admin or EventOrganizer (who is the event's organizer).
        - List/Retrieve: AllowAny.
        """
        if self.action == 'create':
            # IsAuthenticated is implicitly handled if other permissions require authentication.
            # (IsAdminUser | IsEventOrganizer) handles the OR logic.
            # IsEventOrganizer for 'create' checks role only (has_permission).
            self.permission_classes = [IsAuthenticated, (IsAdminUser | IsEventOrganizer)]
        elif self.action in ['update', 'partial_update', 'destroy']:
            # IsEventOrganizer for these actions will also use its has_object_permission.
            self.permission_classes = [IsAuthenticated, (IsAdminUser | IsEventOrganizer)]
        elif self.action in ['list', 'retrieve']:
            self.permission_classes = [permissions.IsAuthenticatedOrReadOnly]
        else:
            # Default to deny for any other actions.
            self.permission_classes = [permissions.DenyAll]
        return [permission() for permission in self.permission_classes]

    def perform_create(self, serializer):
        """
        Set the organizer to the current user if they are not an admin choosing another organizer.
        (Admins might be able to set any organizer - this logic is not yet implemented here,
        defaulting to request.user if serializer doesn't set it).
        If the user is an Event Organizer but not Admin, they are the organizer.
        """
        # If an EventOrganizer is creating, they are the organizer.
        # If Admin is creating, they could potentially set another organizer via serializer field.
        # For now, default to request.user if not provided.
        # This logic might be better in the serializer's validate or create.
        # serializer.save(organizer=self.request.user)
        # Let's assume serializer handles setting organizer, or it defaults if field is read-only / not provided.
        # If 'organizer' is a writeable field in serializer, admin can set it.
        # If 'organizer' is read-only and defaults to current user, then EventOrganizer role is key.
        # The current EventSerializer likely has 'organizer' as read-only or default to current user.
        # For now, let's assume current user is the organizer.
        # If an admin needs to set a different organizer, the serializer should allow it.
        serializer.save(organizer=self.request.user)


    # If search functionality is desired (distinct from filtering):
    # search_fields = ['name', 'description', 'venue__name', 'categories__name']
    # Would need to add 'rest_framework.filters.SearchFilter' to filter_backends.
    # For now, relying on detailed filtering via EventFilterSet.
    # ordering_fields = ['start_time', 'name', 'status', 'venue__name'] # For ordering
    # Would need to add 'rest_framework.filters.OrderingFilter' to filter_backends.

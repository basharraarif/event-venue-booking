from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Booking
from .serializers import BookingSerializer
from .filters import BookingFilterSet
from drf_spectacular.utils import extend_schema_view, extend_schema

class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object or admins to edit/delete it.
    Assumes the model instance has a 'user' attribute.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions (GET, HEAD, OPTIONS) are granted if the user is the owner or an admin.
        # This works in conjunction with get_queryset, which already filters for ownership for non-admins.
        if request.method in permissions.SAFE_METHODS:
            return obj.user == request.user or request.user.is_staff

        # Write permissions (PUT, PATCH, DELETE) are only allowed to the owner or an admin.
        return obj.user == request.user or request.user.is_staff

@extend_schema_view(
    list=extend_schema(
        summary="List bookings",
        description="""Retrieves a list of bookings.
        - Regular users will see only their own bookings.
        - Admin users will see all bookings.

        **Filtering Options (query parameters):**
        - `event`: Filter by event ID (e.g., `?event=1`).
        - `user`: (Admins only) Filter by user ID (e.g., `?user=2`).
        - `status`: Filter by booking status. Choices: `pending`, `confirmed`, `cancelled` (e.g., `?status=confirmed`).
        """
    ),
    retrieve=extend_schema(
        summary="Retrieve a booking",
        description="Retrieves details of a specific booking. Regular users can only retrieve their own bookings. Admins can retrieve any booking."
    ),
    create=extend_schema(
        summary="Create a new booking",
        description="Creates a new booking for an event. The 'user' field is automatically set to the currently authenticated user. The 'total_price' is calculated based on the event's ticket price and number of tickets."
    ),
    update=extend_schema(
        summary="Update a booking (full)",
        description="Updates all fields for an existing booking. Regular users can only update their own bookings. Admins can update any booking. Some fields like 'event' might be restricted from update after creation depending on business logic (not enforced by default)."
    ),
    partial_update=extend_schema(
        summary="Partially update a booking",
        description="Partially updates an existing booking. Only the fields provided in the request will be updated. Regular users can only update their own bookings. Admins can update any booking."
    ),
    destroy=extend_schema(
        summary="Delete a booking",
        description="Deletes an existing booking. Regular users can only delete their own bookings (potentially restricted by status, e.g., cannot delete 'confirmed' bookings - not enforced by default). Admins can delete any booking."
    )
)
class BookingViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing event bookings.

    **Permissions:**
    - All actions require authentication (`IsAuthenticated`).
    - Users can only list, retrieve, update, or delete their own bookings.
    - Administrator users have full access to all bookings.

    **Automatic Fields:**
    - `user`: Automatically set to the request user upon creation.
    - `booking_time`: Automatically set to the current time upon creation.
    - `total_price`: Automatically calculated based on event ticket price and number of tickets.
    """
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_class = BookingFilterSet

    def get_queryset(self):
        """
        This view returns a list of all bookings for the currently authenticated user (if not admin).
        Admins can see all bookings.
        Uses `select_related` for performance optimization on related fields.
        Handles schema generation context by returning a base queryset or none.
        """
        # Handle schema generation context for drf-spectacular
        if getattr(self, 'swagger_fake_view', False):
            # Return a base queryset, or none() if model/serializer can be inferred otherwise
            # For drf-spectacular to correctly infer model and serializer from the viewset,
            # it's often better to provide Booking.objects.all() here, or ensure
            # serializer_class is enough. Booking.objects.none() is safest if introspection issues occur.
            return Booking.objects.none()

        user = self.request.user
        # Ensure user is authenticated before attempting to filter by them
        # IsAuthenticated permission class should handle this, but an explicit check is safer.
        if not user.is_authenticated:
             # This part should ideally not be reached if IsAuthenticated permission is active.
             # If it is reached, it means an unauthenticated user is somehow bypassing permissions.
            return Booking.objects.none()

        if user.is_staff:
            return Booking.objects.all().select_related('user', 'event').order_by('-booking_time')
        return Booking.objects.filter(user=user).select_related('user', 'event').order_by('-booking_time')

    def perform_create(self, serializer):
        """
        Automatically set the user for the booking to `request.user`.
        The `total_price` is calculated by the Booking model's `save()` method.
        """
        serializer.save(user=self.request.user)

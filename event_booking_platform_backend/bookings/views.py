from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Booking
from .serializers import BookingSerializer
from .filters import BookingFilterSet

class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object or admins to edit/delete it.
    Assumes the model instance has a 'user' attribute.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed for any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            # For retrieve, the get_queryset method should have already filtered.
            # This check is an additional safeguard for direct object access if get_object is called.
            return obj.user == request.user or request.user.is_staff

        # Write permissions are only allowed to the owner of the booking or admin.
        return obj.user == request.user or request.user.is_staff

class BookingViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows bookings to be viewed or managed.
    - Users can manage their own bookings.
    - Admins can manage all bookings.
    - Filters available for 'event', 'user' (admin only), 'status'.
    """
    serializer_class = BookingSerializer
    # Permission classes will be IsAuthenticated and then IsOwnerOrAdmin for object-level
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_class = BookingFilterSet

    def get_queryset(self):
        """
        This view should return a list of all bookings
        for the currently authenticated user if they are not an admin.
        Admins can see all bookings.
        """
        user = self.request.user
        if user.is_staff: # or user.is_superuser
            return Booking.objects.all().select_related('user', 'event').order_by('-booking_time')
        return Booking.objects.filter(user=user).select_related('user', 'event').order_by('-booking_time')

    def perform_create(self, serializer):
        """
        Automatically set the user for the booking to the request.user.
        """
        serializer.save(user=self.request.user)

    # Optional: Customize update/destroy if more specific logic than IsOwnerOrAdmin is needed
    # For instance, preventing update of 'event' or 'number_of_tickets' after booking is 'confirmed'.
    # The IsOwnerOrAdmin permission and get_queryset already handle most security.

    # Example: Disallow deletion of confirmed bookings by non-admins
    # def destroy(self, request, *args, **kwargs):
    #     instance = self.get_object()
    #     if instance.status == 'confirmed' and not request.user.is_staff:
    #         return Response(
    #             {'detail': 'Confirmed bookings cannot be deleted by users.'},
    #             status=status.HTTP_403_FORBIDDEN
    #         )
    #     return super().destroy(request, *args, **kwargs)

    # Example: Non-admins can only change status to 'cancelled'
    # def partial_update(self, request, *args, **kwargs):
    #     instance = self.get_object()
    #     if not request.user.is_staff:
    #         allowed_updates = {'status': 'cancelled'}
    #         for key in request.data:
    #             if key not in allowed_updates or (key == 'status' and request.data[key] != 'cancelled'):
    #                 return Response(
    #                     {'detail': f'User can only update status to "cancelled". Attempted to change {key}.'},
    #                     status=status.HTTP_403_FORBIDDEN
    #                 )
    #     return super().partial_update(request, *args, **kwargs)

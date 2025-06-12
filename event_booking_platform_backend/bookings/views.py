from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action # Added action import
from django_filters.rest_framework import DjangoFilterBackend
from .models import Booking
from .serializers import BookingSerializer
from .filters import BookingFilterSet
from drf_spectacular.utils import extend_schema_view, extend_schema
from core.email_utils import send_booking_related_email # Import the generic email function

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
            return Booking.objects.select_related('user', 'event', 'event__venue').all().order_by('-booking_time') # Changed to -booking_time from -created_at
        return Booking.objects.filter(user=user).select_related('user', 'event', 'event__venue').order_by('-booking_time') # Changed to -booking_time

    def perform_create(self, serializer):
        """
        Automatically set the user for the booking to `request.user`.
        The `total_price` is calculated by the Booking model's `save()` method.
        Creates an associated Payment record with 'pending' status.
        Snapshots `price_per_ticket_at_booking`.
        """
        event = serializer.validated_data['event']
        # number_of_tickets = serializer.validated_data['number_of_tickets'] # Not directly needed here for price snapshotting
        price_at_booking = event.ticket_price # Snapshot the event's current ticket price

        # Pass price_per_ticket_at_booking to serializer's save method, which passes to model instance
        booking = serializer.save(
            user=self.request.user,
            price_per_ticket_at_booking=price_at_booking
        )
        # The booking.total_price is now calculated by the model's save() method using the snapshotted price.

        # Automatically create a Payment record for the new booking
        from payments.models import Payment  # Import here to avoid circular dependency issues at module level

        # Determine currency, default to USD if not on event
        currency = 'USD'
        if hasattr(event, 'currency_code') and event.currency_code: # Assuming Event model has 'currency_code'
            currency = event.currency_code
        elif hasattr(event, 'currency') and event.currency: # Fallback to 'currency' attribute
             currency = event.currency

        Payment.objects.create(
            booking=booking,
            amount=booking.total_price, # Use the calculated total_price from booking instance
            currency=currency,
            status=Booking.BookingStatus.PENDING, # Use enum/choices for status consistently
            payment_method='simulated_card' # Default payment method
        )
        # Send booking pending email
        try:
            send_booking_related_email(
                booking=booking,
                subject_template_name='emails/booking_pending_subject.txt',
                body_html_template_name='emails/booking_pending_body.html',
                body_text_template_name='emails/booking_pending_body.txt'
            )
        except Exception as e:
            # Log error but don't fail the booking creation
            print(f"Failed to send booking pending email for Booking ID {booking.id}: {e}")

    def perform_update(self, serializer):
        """
        Handle updates to a booking.
        If number_of_tickets changes for a PENDING booking, update the associated Payment amount.
        """
        original_booking = self.get_object() # Get the booking instance before update
        original_number_of_tickets = original_booking.number_of_tickets

        updated_booking = serializer.save() # This will call model's save(), recalculating total_price

        if 'number_of_tickets' in serializer.validated_data and \
           serializer.validated_data['number_of_tickets'] != original_number_of_tickets:

            # Payment status check is now handled in BookingSerializer.validate()
            # Here, we just need to update the payment amount if it's still pending.
            try:
                payment = updated_booking.payment
                if payment.status == Booking.BookingStatus.PENDING: # Check against BookingStatus.PENDING
                    payment.amount = updated_booking.total_price
                    payment.save()
            except Booking.payment.RelatedObjectDoesNotExist:
                 print(f"Warning: No payment found for booking {updated_booking.id} during perform_update.")
            except Exception as e:
                print(f"Error updating payment for booking {updated_booking.id}: {e}")
                # Potentially raise a validation error or handle more gracefully if payment update fails

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsOwnerOrAdmin])
    def cancel_booking(self, request, pk=None):
        """
        Cancels a booking.
        """
        booking = self.get_object()
        if booking.status == 'cancelled':
            return Response({'detail': 'Booking is already cancelled.'}, status=status.HTTP_400_BAD_REQUEST)

        # Add any other conditions under which a booking cannot be cancelled (e.g., event already started)
        # For example:
        # if booking.event.start_time < timezone.now():
        #     return Response({'detail': 'Cannot cancel booking for an event that has already started.'}, status=status.HTTP_400_BAD_REQUEST)

        booking.status = 'cancelled'
        booking.save()

        # Also cancel the associated payment if it exists and is pending
        if hasattr(booking, 'payment') and booking.payment.status == 'pending':
            booking.payment.status = 'cancelled' # Or 'failed' depending on desired payment workflow for cancellations
            booking.payment.save()

        # Send booking cancellation email
        try:
            send_booking_related_email(
                booking=booking,
                subject_template_name='emails/booking_cancelled_subject.txt',
                body_html_template_name='emails/booking_cancelled_body.html',
                body_text_template_name='emails/booking_cancelled_body.txt'
            )
        except Exception as e:
            print(f"Failed to send booking cancellation email for Booking ID {booking.id}: {e}")

        serializer = self.get_serializer(booking)
        return Response(serializer.data)

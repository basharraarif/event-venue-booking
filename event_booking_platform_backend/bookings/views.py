from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action # Added action import
from django_filters.rest_framework import DjangoFilterBackend
from .models import Booking
from .serializers import BookingSerializer
from .filters import BookingFilterSet
from drf_spectacular.utils import extend_schema_view, extend_schema
from core.email_utils import send_booking_related_email
from core.permissions import IsOwnerOrAdmin, IsCustomer, IsEventOrganizer, IsVenueManager # Import new permissions
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from payments.models import Payment # Import Payment model
from django.db.models import Q # For complex queries
import logging

logger = logging.getLogger(__name__)

# Local IsOwnerOrAdmin removed, will use the one from core.permissions

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
    - Event Organizers can see bookings for their events.
    - Venue Managers can see bookings for events at their venues.

    **Automatic Fields:**
    - `user`: Automatically set to the request user upon creation.
    - `booking_time`: Automatically set to the current time upon creation.
    - `total_price`: Automatically calculated based on event ticket price and number of tickets.
    """
    serializer_class = BookingSerializer
    # permission_classes are set dynamically by get_permissions
    filter_backends = [DjangoFilterBackend]
    filterset_class = BookingFilterSet

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action == 'create':
            # Any authenticated user can create a booking (implicitly IsCustomer or any other role)
            self.permission_classes = [IsAuthenticated]
        elif self.action in ['update', 'partial_update', 'destroy', 'cancel_booking']:
            # Only owner or admin can modify/delete. IsOwnerOrAdmin checks obj.user vs request.user or is_staff.
            self.permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
        elif self.action in ['list', 'retrieve']:
            # Authenticated users can list/retrieve based on queryset filtering.
            # Specific object permissions (like IsCustomer for obj.user) handled by IsOwnerOrAdmin for retrieve.
            # For list, queryset is key.
            self.permission_classes = [IsAuthenticated]
        else:
            self.permission_classes = [IsAdminUser] # Default for any other actions
        return [permission() for permission in self.permission_classes]

    def get_queryset(self):
        """
        Admins see all bookings.
        Event Organizers see bookings for their events.
        Venue Managers see bookings for events at their venues.
        Customers see their own bookings.
        """
        user = self.request.user
        if not user.is_authenticated: # Should be caught by IsAuthenticated permission
            return Booking.objects.none()

        # Handle schema generation context for drf-spectacular
        if getattr(self, 'swagger_fake_view', False):
            return Booking.objects.none()

        base_queryset = Booking.objects.select_related('user', 'event', 'event__venue', 'event__organizer').all()

        if user.is_staff: # Admin sees all
            return base_queryset.order_by('-booking_time')

        # Build Q objects for filtering based on roles
        conditions = Q(user=user) # Default: Customer sees their own bookings

        if user.roles.filter(name=IsEventOrganizer.role_name).exists(): # Check actual role name string
            conditions |= Q(event__organizer=user)

        if user.roles.filter(name=IsVenueManager.role_name).exists():
            # This assumes Venue has an 'owner' field linked to the User model
            # And user (VenueManager) is the owner of the venue where the event takes place.
            conditions |= Q(event__venue__owner=user)

        return base_queryset.filter(conditions).distinct().order_by('-booking_time')

    def perform_create(self, serializer):
        """
        Automatically set the user for the booking to `request.user`.
        Calculates total_price, creates Payment record if needed, snapshots price.
        Checks event capacity before creating the booking.
        """
        event = serializer.validated_data['event']
        requested_tickets = serializer.validated_data['number_of_tickets']

        # --- Capacity Check ---
        effective_capacity = event.effective_capacity # This is a property on Event model

        # If effective_capacity is None, it means unlimited capacity (as per model property logic)
        if effective_capacity is not None: # Only check if capacity is defined
            if effective_capacity == 0: # Explicitly set to zero capacity
                 raise serializers.ValidationError(
                    {"detail": "This event cannot be booked as it has zero capacity."}
                )

            current_active_tickets = event.active_tickets_count()
            if current_active_tickets + requested_tickets > effective_capacity:
                available_tickets = effective_capacity - current_active_tickets
                raise serializers.ValidationError(
                    {"detail": f"Not enough tickets available. Only {available_tickets} left."}
                )
        # --- End Capacity Check ---

        price_at_booking = event.ticket_price # Snapshot the event's current ticket price

        # Pass price_per_ticket_at_booking to serializer's save method
        booking = serializer.save(
            user=self.request.user,
            price_per_ticket_at_booking=price_at_booking
        )
        # The booking.total_price is now calculated by the model's save() method using the snapshotted price.

        if booking.total_price > 0:
            # Paid event: create Payment record, set booking status to PENDING_PAYMENT
            # booking.payment_status = 'pending' # This field is removed from Booking model
            booking.status = Booking.BookingStatus.PENDING_PAYMENT
            booking.save(update_fields=['status']) # Save status field first

            # Determine currency
            currency = 'USD' # Default currency
            if hasattr(event, 'currency') and event.currency: # Assuming Event model has 'currency' field
                currency = event.currency
            elif hasattr(event, 'currency_code') and event.currency_code: # Alternative common name
                currency = event.currency_code

            Payment.objects.create(
                booking=booking,
                amount=booking.total_price,
                currency=currency,
                status='pending', # Payment model's status
                # payment_method will be handled by Stripe, not needed here
            )
            logger.info(f"Pending Payment record created for booking {booking.id} (User: {booking.user.id}). Booking status: {booking.status}") # Removed payment_status
            email_subject_template = 'emails/booking_pending_subject.txt' # Corrected template name
            email_html_template = 'emails/booking_pending_body.html'
            email_text_template = 'emails/booking_pending_body.txt'
        else:
            # Free event: set booking status to CONFIRMED
            # booking.payment_status = 'not_required' # This field is removed from Booking model
            booking.status = Booking.BookingStatus.CONFIRMED
            booking.save(update_fields=['status'])
            logger.info(f"Free booking {booking.id} confirmed (User: {booking.user.id}).") # Removed payment_status from log
            email_subject_template = 'emails/booking_confirmation_subject.txt' # Use confirmation for free events
            email_html_template = 'emails/booking_confirmation_body.html'
            email_text_template = 'emails/booking_confirmation_body.txt'

        # Send appropriate email based on whether payment is required
        logger.info(f"Attempting to send email for booking {booking.id} with subject template {email_subject_template} inside perform_create.")
        try:
            send_booking_related_email(
                booking=booking,
                subject_template_name=email_subject_template,
                body_html_template_name=email_html_template,
                body_text_template_name=email_text_template
            )
            logger.info(f"Call to send_booking_related_email completed for booking {booking.id}.")
        except Exception as e:
            logger.error(f"Failed to send booking email for Booking ID {booking.id} within perform_create: {e}")

    def perform_update(self, serializer):
        """
        Handle updates to a booking.
        Checks event capacity if number_of_tickets is changed.
        If number_of_tickets changes for a PENDING booking, update the associated Payment amount.
        """
        original_booking = self.get_object() # Get the booking instance before update
        original_number_of_tickets = original_booking.number_of_tickets
        requested_new_number_of_tickets = serializer.validated_data.get('number_of_tickets', original_number_of_tickets)

        if requested_new_number_of_tickets != original_number_of_tickets:
            event = original_booking.event # Event doesn't change during booking update

            # --- Capacity Check for Update ---
            effective_capacity = event.effective_capacity
            if effective_capacity is not None: # Only check if capacity is defined
                if effective_capacity == 0:
                    # This case is tricky. If capacity is 0, no tickets should be allowed.
                    # If user is trying to change tickets for a booking on a 0-capacity event, it's an issue.
                    # However, if requested_new_number_of_tickets is 0 (cancelling booking essentially by tickets),
                    # this might be allowed by other logic. For now, if capacity is 0, no increase.
                    if requested_new_number_of_tickets > 0 : # Allow reducing to 0.
                        raise serializers.ValidationError(
                            {"detail": "This event has zero capacity; tickets cannot be modified."}
                        )

                # Account for tickets already held by this booking
                current_active_tickets_excluding_this = event.active_tickets_count() - original_number_of_tickets

                if current_active_tickets_excluding_this + requested_new_number_of_tickets > effective_capacity:
                    available_tickets = effective_capacity - current_active_tickets_excluding_this
                    raise serializers.ValidationError(
                        {"detail": f"Not enough tickets available for update. Only {available_tickets} left (excluding your original booking)."}
                    )
            # --- End Capacity Check for Update ---

        updated_booking = serializer.save() # This will call model's save(), recalculating total_price

        if requested_new_number_of_tickets != original_number_of_tickets:

            # Payment status check is now handled in BookingSerializer.validate()
            # Here, we just need to update the payment amount if it's still pending.
            try:
                payment = updated_booking.payment # Access via related name 'payment' from Booking model
                if payment.status == 'pending': # Check against Payment model's 'pending' status
                    if payment.amount != updated_booking.total_price:
                        payment.amount = updated_booking.total_price
                        payment.save(update_fields=['amount'])
                        logger.info(f"Payment amount updated for booking {updated_booking.id} due to booking modification.")
            except Payment.DoesNotExist: # Correct exception for RelatedObjectDoesNotExist
                 logger.warning(f"No payment found for booking {updated_booking.id} during perform_update, though ticket count changed.")
            except Exception as e:
                logger.error(f"Error updating payment amount for booking {updated_booking.id}: {e}")
                # Potentially raise a validation error or handle more gracefully if payment update fails

    # The permission for cancel_booking is now set in get_permissions
    @action(detail=True, methods=['post']) # permission_classes removed from here
    def cancel_booking(self, request, pk=None):
        """
        Cancels a booking. Permissions are handled by get_permissions.
        """
        booking = self.get_object() # get_object will apply object-level permissions
        if booking.status == Booking.BookingStatus.CANCELLED: # Use enum
            return Response({'detail': 'Booking is already cancelled.'}, status=status.HTTP_400_BAD_REQUEST)

        # Example: Add check if event already started (using Django timezone if configured)
        # from django.utils import timezone
        # if booking.event.start_time < timezone.now():
        #     return Response({'detail': 'Cannot cancel booking for an event that has already started.'}, status=status.HTTP_400_BAD_REQUEST)

        booking.status = Booking.BookingStatus.CANCELLED # Use enum
        booking.save(update_fields=['status'])

        # Also cancel the associated payment if it exists and is pending
        if hasattr(booking, 'payment'): # Check if 'payment' related object exists
            try:
                payment = booking.payment
                if payment.status == 'pending':
                    payment.status = 'cancelled'
                    payment.save(update_fields=['status'])
                    logger.info(f"Associated pending payment {payment.id} for booking {booking.id} also marked as cancelled.")
            except Payment.DoesNotExist:
                logger.info(f"No payment record found for booking {booking.id} during cancellation.")
            except Exception as e: # Catch other potential errors
                logger.error(f"Error updating payment status during booking cancellation for {booking.id}: {e}")
        else:
            logger.info(f"No payment attribute on booking {booking.id}, or booking requires no payment.")

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

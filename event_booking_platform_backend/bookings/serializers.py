from rest_framework import serializers
from django.db import models # Import models for Sum
from .models import Booking
from events.models import Event
from django.contrib.auth import get_user_model # For User model reference
from core.serializers import UserSerializer
from payments.serializers import PaymentSerializer # Import PaymentSerializer
# from events.serializers import EventSerializer as FullEventSerializer # Not used here

User = get_user_model() # Get the active User model

class NestedEventSerializer(serializers.ModelSerializer):
    """
    A simplified serializer for nested event representation within bookings.
    Provides key event details without excessive nesting.
    """
    # TODO: Add currency to this serializer if needed for display consistency.
    class Meta:
        model = Event
        fields = ['id', 'name', 'start_time', 'ticket_price']
        # No help_text needed here as it's for internal representation, not direct API input schema

class BookingSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(
        source='user',
        read_only=True,
        help_text="Read-only. Detailed information about the user who made the booking."
    )
    event_details = NestedEventSerializer(
        source='event',
        read_only=True,
        help_text="Read-only. Key details of the event being booked."
    )
    payment_status = serializers.SerializerMethodField(help_text="Read-only. The status of the associated payment.")
    payment_details = PaymentSerializer(source='payment', read_only=True, help_text="Read-only. Detailed information about the associated payment.")

    # 'event' is for writing (expects Event ID).
    event = serializers.PrimaryKeyRelatedField(
        queryset=Event.objects.all(),
        help_text="ID of the event to book. Required for creating a booking."
    )
    # 'user' field for writing is handled by the ViewSet (perform_create) and is read-only here.

    # Note on Concurrency for Capacity Checks:
    # The `validate` method provides robust capacity checking at the application level.
    # However, under very high concurrency (multiple users trying to book the last few tickets
    # simultaneously), race conditions could potentially lead to overbooking.
    # True atomicity for capacity checking would typically require database-level mechanisms
    # such as `SELECT FOR UPDATE` on the related Event or Venue record within a transaction
    # when creating/updating bookings, or using database constraints if applicable.
    # This is a known area for potential improvement if the platform expects very high traffic
    # for popular events. For now, the serializer-level validation provides a strong safeguard.

    class Meta:
        model = Booking
        fields = [
            'id',
            'event',             # Write: Event ID
            'event_details',     # Read: Nested Event object
            'user',              # Read: User ID (set automatically on create, read-only for input)
            'user_details',      # Read: Nested User object
            'number_of_tickets',
            'price_per_ticket_at_booking', # Read-only, set by model logic
            'total_price',       # Read-only, calculated by model logic
            'booking_time',      # Read-only
            'status',
            'payment_status',    # Read-only property from model
            'payment_details',   # Read-only nested serializer
            'payment_intent_id', # Read-only, managed by system
        ]
        read_only_fields = [
            'booking_time',
            'total_price',
            'price_per_ticket_at_booking',
            'user', # User is set by perform_create in the ViewSet, not taken from request payload directly.
            # 'payment_status' is handled by SerializerMethodField now
            'payment_details',
            'payment_intent_id',
        ]
        extra_kwargs = {
            'number_of_tickets': {
                'help_text': "Number of tickets to book for the event. Must be a positive integer."
            },
            'status': {
                'help_text': "Status of the booking. Choices: 'pending', 'confirmed', 'cancelled'. Defaults to 'pending'."
            },
            # 'id' is implicitly read-only.
        }

    def validate_number_of_tickets(self, value):
        if value <= 0:
            raise serializers.ValidationError("Number of tickets must be greater than zero.")
        return value

    def validate(self, data):
        # This validation runs on create and update.
        # For updates (PATCH), 'event' might not be in data if not being changed.
        event = data.get('event', getattr(self.instance, 'event', None))

        if event:
            if event.status not in ['upcoming', 'ongoing']:
                raise serializers.ValidationError(
                    {'event': f"Bookings can only be made for 'upcoming' or 'ongoing' events. This event status is '{event.status}'."}
                )
        # On create, 'event' must be present. PrimaryKeyRelatedField handles this.
        # If 'event' is not in data and self.instance is None (create), it's an issue,
        # but DRF's field validation for required 'event' field should catch it first.

        # Capacity Check
        # This check is particularly important for create and when number_of_tickets is updated.
        # Ensure 'event' is available for validation. If it's an update and 'event' isn't part of `data`,
        # it means the event for the booking is not being changed, so we use `self.instance.event`.
        # The `data.get('event', ...)` already handles this.

        requested_tickets = data.get('number_of_tickets')

        # The number_of_tickets validation (must be > 0) is now handled by validate_number_of_tickets method.
        # We can remove the explicit check here if `validate_number_of_tickets` is always called first.
        # However, keeping it here or ensuring order of validation can be complex.
        # For clarity, `validate_number_of_tickets` handles the positive check.

        if event and requested_tickets is not None: # Proceed only if event and tickets are part of validation
            # Use the event's method to get currently confirmed tickets
            # On create, self.instance is None. On update, self.instance is the booking being updated.
            # The goal is to check capacity against tickets already confirmed for the event,
            # PLUS the tickets being requested in this booking operation,
            # MINUS any tickets already held by this booking if it's an update.

            # Effective capacity of the event
            effective_capacity = event.effective_capacity

            if effective_capacity is None or effective_capacity == 0:
                raise serializers.ValidationError(
                    {'event': f"This event is not available for booking (capacity: {effective_capacity})."}
                )

            # Tickets confirmed for this event, EXCLUDING the current booking instance if it's an update
            # This is tricky because confirmed_tickets_count() on event includes all confirmed.
            # We need to adjust if this is an update to an existing booking.

            # Effective capacity of the event
            # Assuming event.effective_capacity correctly gives event.max_capacity or event.venue.capacity
            effective_capacity = event.effective_capacity

            if effective_capacity is None: # None might mean unlimited capacity
                pass # No capacity check needed if unlimited
            elif effective_capacity == 0:
                raise serializers.ValidationError(
                    {'number_of_tickets': "This event is not available for booking as it has zero capacity."}
                )
            else:
                # Calculate current number of "active" tickets for the event.
                # Active bookings are those that hold a spot (e.g., Confirmed or Pending Payment).
                active_booking_statuses = [
                    Booking.BookingStatus.CONFIRMED,
                    Booking.BookingStatus.PENDING_PAYMENT
                ]

                current_active_tickets_query = Booking.objects.filter(
                    event=event,
                    status__in=active_booking_statuses
                )

                # If this is an update to an existing booking, exclude its previous ticket count from the sum.
                # The new requested_tickets will be added to this sum for the check.
                if self.instance and self.instance.pk:
                    current_active_tickets_query = current_active_tickets_query.exclude(pk=self.instance.pk)

                current_tickets_taken_by_others = current_active_tickets_query.aggregate(
                    total_tickets=models.Sum('number_of_tickets')
                )['total_tickets'] or 0

                if current_tickets_taken_by_others + requested_tickets > effective_capacity:
                    available_tickets = effective_capacity - current_tickets_taken_by_others
                    if available_tickets < 0: # Should not happen if logic is correct but as a safeguard
                        available_tickets = 0
                    raise serializers.ValidationError(
                        {'number_of_tickets': f"Booking exceeds event capacity. Only {available_tickets} ticket(s) currently available for event '{event.name}'."}
                    )

        # Validation for updating number_of_tickets based on payment status
        if self.instance and 'number_of_tickets' in data and data['number_of_tickets'] != self.instance.number_of_tickets:
            try:
                payment = self.instance.payment
                if payment.status != 'pending': # Check Payment model's status
                    raise serializers.ValidationError({
                        'number_of_tickets': f"Cannot change number of tickets once payment is {payment.status}."
                    })
            except Booking.payment.RelatedObjectDoesNotExist: # Correct exception name
                 # If no payment object, allow ticket change (e.g. free booking or admin fixing)
                pass
            except AttributeError:
                # If self.instance.payment doesn't exist (e.g. not pre-fetched or related_name issue)
                # This might indicate a setup issue if payment is expected. For now, allow.
                pass


        return data

    def get_payment_status(self, obj):
        if hasattr(obj, 'payment') and obj.payment:
            return obj.payment.status
        # Consider returning None or a specific string like 'no_payment_object' if obj.payment is None
        # For instance, if a booking is free and has no payment object.
        # The current logic implies "not_required" could mean free or no payment object.
        return "not_required" # Default if no payment object or payment field is None


        # The duplicated 'return data' and the second 'get_payment_status' were removed.
        # The validation for 'number_of_tickets' based on payment status is kept once.
        return data

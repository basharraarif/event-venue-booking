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
    payment_status = serializers.CharField(read_only=True, help_text="Read-only. The status of the associated payment.")
    payment_details = PaymentSerializer(source='payment', read_only=True, help_text="Read-only. Detailed information about the associated payment.")

    # 'event' is for writing (expects Event ID).
    event = serializers.PrimaryKeyRelatedField(
        queryset=Event.objects.all(),
        help_text="ID of the event to book. Required for creating a booking."
    )
    # 'user' field for writing is handled by the ViewSet (perform_create) and is read-only here.

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
        ]
        read_only_fields = [
            'booking_time',
            'total_price',
            'price_per_ticket_at_booking',
            'user', # User is set by perform_create in the ViewSet, not taken from request payload directly.
            'payment_status',
            'payment_details',
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

            currently_confirmed_for_event = event.confirmed_tickets_count()

            # If this is an update to an existing booking that was already 'confirmed',
            # its tickets are already in `currently_confirmed_for_event`.
            # We need to subtract them before adding the new `requested_tickets`.
            tickets_from_this_booking_pre_update = 0
            if self.instance and self.instance.pk and self.instance.status == Booking.BookingStatus.CONFIRMED:
                tickets_from_this_booking_pre_update = self.instance.number_of_tickets

            # Effective number of tickets already booked by others (or by this booking if it wasn't confirmed)
            # This logic ensures that if a user is changing the number of tickets for their *own confirmed* booking,
            # the capacity check correctly accounts for the tickets they are releasing or adding.
            other_confirmed_tickets = currently_confirmed_for_event - tickets_from_this_booking_pre_update

            if other_confirmed_tickets + requested_tickets > effective_capacity:
                available_tickets = effective_capacity - other_confirmed_tickets
                if available_tickets < 0: available_tickets = 0 # Ensure non-negative
                raise serializers.ValidationError(
                    {'number_of_tickets': f"Booking exceeds event capacity. Only {available_tickets} ticket(s) remaining for event '{event.name}'."}
                )

        # Validation for updating number_of_tickets based on payment status
        if self.instance and 'number_of_tickets' in data and data['number_of_tickets'] != self.instance.number_of_tickets:
            try:
                # Ensure related payment instance is loaded.
                # self.instance.payment might be cached; consider self.instance.payment_set.first() or Payment.objects.get(booking=self.instance)
                # For OneToOneField, self.instance.payment should be fine if correctly related and fetched.
                payment = self.instance.payment
                # Check if payment status is not PENDING (using actual values from Payment model choices)
                # from payments.models import Payment # Import locally if needed
                # Assuming Payment model has status choices like ('pending', 'successful', 'failed')
                if payment.status != 'pending': # Ideally, use Payment.PaymentStatus.PENDING if available
                    raise serializers.ValidationError({
                        'number_of_tickets': f"Cannot change number of tickets once payment is {payment.status}."
                    })
            except Booking.payment.RelatedObjectDoesNotExist: # Adjusted exception type
                 # This case implies no payment object is associated, which might be an issue
                 # or could mean booking is new and payment not yet created.
                 # However, this validation is for self.instance (updates), so payment should exist.
                print(f"Warning: Payment object not found for booking {self.instance.id} during number_of_tickets validation.")
                # Depending on business logic, this could be a pass or an error.
                # For now, let's assume if no payment, it's okay to change tickets (e.g. admin fixing things).
                pass
            except AttributeError: # If self.instance.payment doesn't exist for some reason
                print(f"Warning: Payment attribute error for booking {self.instance.id}.")
                pass


        return data

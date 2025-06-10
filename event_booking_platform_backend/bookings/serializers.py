from rest_framework import serializers
from .models import Booking # User is not in bookings.models
from events.models import Event
from django.contrib.auth import get_user_model # For User model reference
from core.serializers import UserSerializer
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
            'booking_time',      # Read-only
            'status',
            'total_price'        # Read-only
        ]
        read_only_fields = [
            'booking_time',
            'total_price',
            'user' # User is set by perform_create in the ViewSet, not taken from request payload directly.
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
        return data

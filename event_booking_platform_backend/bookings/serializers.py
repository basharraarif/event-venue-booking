from rest_framework import serializers
from .models import Booking
from events.models import Event # Needed for event_id validation
from core.serializers import UserSerializer # Assuming a simple UserSerializer exists for read-only representation
from events.serializers import EventSerializer as FullEventSerializer # For detailed event info, might be too verbose

# A simpler serializer for nested event representation if needed
class NestedEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ['id', 'name', 'start_time', 'ticket_price'] # Keep it concise

class BookingSerializer(serializers.ModelSerializer):
    # Read-only nested representations for user and event
    user_details = UserSerializer(source='user', read_only=True) # For display
    event_details = NestedEventSerializer(source='event', read_only=True) # For display

    # 'event' is needed for writing.
    event = serializers.PrimaryKeyRelatedField(
        queryset=Event.objects.all()
    )
    # 'user' field is now implicitly handled by ModelSerializer and made read-only via Meta

    class Meta:
        model = Booking
        fields = [
            'id',
            'event', 'event_details', # 'event' for writing ID, 'event_details' for reading nested
            'user', 'user_details',   # 'user' for writing ID, 'user_details' for reading nested
            'number_of_tickets',
            'booking_time',
            'status',
            'total_price'
        ]
        read_only_fields = ['booking_time', 'total_price', 'user'] # User is set by perform_create

    def validate_number_of_tickets(self, value):
        if value <= 0:
            raise serializers.ValidationError("Number of tickets must be greater than zero.")
        return value

    def validate(self, data):
        # Model's clean method isn't called by default in DRF.
        # Custom validation, e.g. event capacity check, could go here.
        # For now, ensuring event is active or upcoming if that's a business rule.
        event = data.get('event')
        if event:
            if event.status not in ['upcoming', 'ongoing']: # Example validation
                raise serializers.ValidationError(f"Bookings can only be made for 'upcoming' or 'ongoing' events. Event status is '{event.status}'.")

            # Example: Check against (hypothetical) event.max_tickets_per_booking
            # number_of_tickets = data.get('number_of_tickets')
            # if event.max_tickets_per_booking and number_of_tickets > event.max_tickets_per_booking:
            #     raise serializers.ValidationError(f"Cannot book more than {event.max_tickets_per_booking} tickets for this event.")

        return data

    # The create() method will automatically use the Booking model's save() method,
    # which calculates total_price. So, no need to override create() for that.
    # Similarly for update(), if number_of_tickets or event changes, model's save() handles total_price.
    # If event or number_of_tickets are not part of validated_data in an update,
    # the existing values on the instance will be used by the model's save method.
    # If partial update, ensure the model's save logic correctly recalculates total_price if needed.
    # The current Booking.save() calculates total_price based on instance's event and number_of_tickets.
    # This is fine for create. For update, if event or number_of_tickets changes, it will use the new values.
    # If only other fields (e.g. status) change, total_price remains based on existing event/tickets.

    # If we wanted to ensure total_price is re-calculated on *any* update,
    # we might override update, but it's tricky if event/tickets aren't in validated_data.
    # The current model save method is generally okay.
    # def update(self, instance, validated_data):
    #     # If event or number_of_tickets changes, recalculate price
    #     # The model's save method already does this.
    #     instance = super().update(instance, validated_data)
    #     return instance

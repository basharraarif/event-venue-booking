from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field # Import for schema hints
from drf_spectacular.types import OpenApiTypes # Import OpenApiTypes
from .models import Event, Category
from django.contrib.auth import get_user_model
from venues.models import Venue # Assuming this is the correct path

User = get_user_model()

# Assuming UserSerializer might be imported if we wanted deeper organizer details,
# but for now, organizer_username is a CharField.
# from core.serializers import UserSerializer

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description']
        extra_kwargs = {
            'name': {'help_text': "Name of the event category (e.g., 'Music', 'Sports'). Must be unique."},
            'description': {'help_text': "Optional. A brief description of the category."}
        }

class EventSerializer(serializers.ModelSerializer):
    categories = serializers.SlugRelatedField(
        many=True,
        queryset=Category.objects.all(),
        slug_field='name',
        help_text="List of category names associated with the event. For writing, provide a list of existing category names (e.g., [\"Music\", \"Conference\"])."
    )

    organizer_username = serializers.CharField(
        source='organizer.username',
        read_only=True,
        help_text="Username of the user who organized the event (Read-only)."
    )
    venue_name = serializers.CharField(
        source='venue.name',
        read_only=True,
        help_text="Name of the venue where the event is held (Read-only)."
    )

    # Explicitly define 'venue' and 'organizer' if we want to add help_text for the writable ID fields.
    # Otherwise, they are created by ModelSerializer automatically.
    # For clarity in documentation, making them explicit can be good.
    venue = serializers.PrimaryKeyRelatedField(
        queryset=Venue.objects.all(), # Assuming Venue model is imported or string 'venues.Venue' is used in model
        help_text="ID of the venue where the event will take place. This is required."
    )
    organizer = serializers.PrimaryKeyRelatedField(
        read_only=True, # Set by perform_create in the viewset
        help_text="ID of the user organizing the event. Set automatically on creation."
    )

    # Schema hints for properties/methods
    effective_capacity = serializers.SerializerMethodField() # Changed to SerializerMethodField
    active_tickets_count = serializers.SerializerMethodField() # Changed to SerializerMethodField

    @extend_schema_field(OpenApiTypes.INT)
    def get_effective_capacity(self, obj):
        return obj.effective_capacity

    @extend_schema_field(OpenApiTypes.INT)
    def get_active_tickets_count(self, obj):
        return obj.active_tickets_count()


    class Meta:
        model = Event
        fields = [
            'id', 'name', 'description',
            'venue', 'venue_name',
            'organizer', # Still in fields to be included in GET responses
            'organizer_username',
            'categories',
            'start_time', 'end_time', 'status', 'ticket_price',
            'max_capacity',
            'effective_capacity',
            'active_tickets_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'created_at', 'updated_at',
            'organizer', # Explicitly mark organizer as read-only here too
            'organizer_username', 'venue_name',
            # effective_capacity and active_tickets_count are read-only due to SerializerMethodField
        ]
        extra_kwargs = {
            'name': {'help_text': "Name of the event."},
            # Clarify that effective_capacity and confirmed_tickets_count are read-only in help text if needed,
            # but schema should show them as readOnly due to ReadOnlyField or @extend_schema_field on a method.
            'max_capacity': {'help_text': "Maximum capacity for this event. If blank, venue capacity will be used. Cannot exceed venue capacity or be less than confirmed tickets."},
            'description': {'help_text': "Optional. Detailed description of the event."},
            'start_time': {'help_text': "Event start date and time (YYYY-MM-DDTHH:MM:SS format)."},
            'end_time': {'help_text': "Event end date and time (YYYY-MM-DDTHH:MM:SS format). Must be after start_time."},
            'status': {
                'help_text': "Current status of the event. Choices: 'upcoming', 'ongoing', 'past', 'cancelled'. Defaults to 'upcoming'."
            },
            'ticket_price': {
                'help_text': "Price per ticket for the event. Use '0.00' for free events. (e.g., '25.50')."
            }
            # 'venue' and 'organizer' help_text is added on their explicit definitions above.
        }

    def validate(self, data):
        # model's clean method is not called by DRF serializers by default.
        # This validation ensures end_time is after start_time.
        # It considers both create (start_time and end_time in data) and partial update scenarios.
        start_time = data.get('start_time', getattr(self.instance, 'start_time', None))
        end_time = data.get('end_time', getattr(self.instance, 'end_time', None))

        if start_time and end_time and end_time <= start_time:
            raise serializers.ValidationError({'end_time': 'End time must be after start time.'})

        # Capacity Validations
        venue = data.get('venue') or (self.instance and self.instance.venue)
        max_capacity_value = data.get('max_capacity') # Use a different variable name to avoid conflict with model field

        if venue and max_capacity_value is not None: # max_capacity_value is the one from input data
            if max_capacity_value == 0: # Allow setting zero explicitly
                pass
            elif max_capacity_value > venue.capacity:
                raise serializers.ValidationError(
                    {'max_capacity': f"Event max capacity ({max_capacity_value}) cannot exceed venue capacity ({venue.capacity})."}
                )

        # Ensure max_capacity is not less than already confirmed tickets when updating
        if self.instance and max_capacity_value is not None:
            # Need to access confirmed_tickets_count via the instance method
            # This count should reflect the state *before* this update is applied.
            # If status is also being updated in the same request, this could be tricky.
            # For simplicity, assume active_tickets_count() on instance is pre-update state.
            instance_confirmed_tickets = self.instance.active_tickets_count()
            if max_capacity_value < instance_confirmed_tickets:
                raise serializers.ValidationError(
                    {'max_capacity': f"Event max capacity ({max_capacity_value}) cannot be less than already confirmed tickets ({instance_confirmed_tickets})."}
                )
        return data

# Note: EventDetailSerializer is not explicitly defined in the provided file.
# If it exists and inherits from EventSerializer, it will inherit these changes.
# If it's a separate definition, it would need similar updates.
# For now, assuming EventSerializer is the primary one used or is the base for EventDetailSerializer.

# Imports for User and Venue were moved to the top of the file.

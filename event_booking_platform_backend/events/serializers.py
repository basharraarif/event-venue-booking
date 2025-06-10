from rest_framework import serializers
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
        queryset=User.objects.all(), # Assuming User model is imported (from django.contrib.auth import get_user_model)
        help_text="ID of the user organizing the event. This is required."
    )


    class Meta:
        model = Event
        fields = [
            'id', 'name', 'description',
            'venue', 'venue_name',
            'organizer', 'organizer_username',
            'categories',
            'start_time', 'end_time', 'status', 'ticket_price',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'organizer_username', 'venue_name']
        extra_kwargs = {
            'name': {'help_text': "Name of the event."},
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

        return data

# Imports for User and Venue were moved to the top of the file.

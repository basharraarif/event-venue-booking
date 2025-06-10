from rest_framework import serializers
from .models import Event, Category
# To represent related fields like venue and organizer by their string representation or more details
# from venues.serializers import VenueSerializer # Assuming it exists
# from core.serializers import UserSerializer # Assuming it exists

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description']

class EventSerializer(serializers.ModelSerializer):
    # To provide more readable representations for FK/M2M fields,
    # you can use SlugRelatedField or StringRelatedField, or nested serializers.
    # For now, default behavior is PrimaryKeyRelatedField.

    # Example: Use names for categories in read operations
    categories = serializers.SlugRelatedField(
        many=True,
        queryset=Category.objects.all(),
        slug_field='name'
    )

    # Example: Show organizer's username
    organizer_username = serializers.CharField(source='organizer.username', read_only=True)
    # Example: Show venue's name
    venue_name = serializers.CharField(source='venue.name', read_only=True)

    class Meta:
        model = Event
        fields = [
            'id', 'name', 'description',
            'venue', 'venue_name', # venue will be ID, venue_name will be the name
            'organizer', 'organizer_username', # organizer will be ID, organizer_username the name
            'categories',
            'start_time', 'end_time', 'status',
            'created_at', 'updated_at'
        ]
        # For write operations, we want to use IDs for venue and organizer
        # read_only_fields can be used if we only want IDs for write and nested for read,
        # but that requires more complex setup (e.g. separate read/write serializers or custom fields)
        # For now, 'venue' and 'organizer' will be writable PKs.
        # 'venue_name' and 'organizer_username' are read-only.

    # Add custom validation for event timing if not fully handled by model's clean method
    def validate(self, data):
        # model's clean method is not called by DRF serializers by default
        # Call it explicitly or reimplement validation here.
        if 'start_time' in data and 'end_time' in data:
            if data['end_time'] <= data['start_time']:
                raise serializers.ValidationError({'end_time': 'End time must be after start time.'})
        # If start_time or end_time is not being updated, compare with instance values
        elif 'start_time' in data and self.instance and self.instance.end_time <= data['start_time']:
             raise serializers.ValidationError({'end_time': 'End time must be after start time.'})
        elif 'end_time' in data and self.instance and data['end_time'] <= self.instance.start_time:
             raise serializers.ValidationError({'end_time': 'End time must be after start time.'})
        return data

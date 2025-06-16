from rest_framework import serializers
from .models import Venue

from django.contrib.auth import get_user_model

User = get_user_model()

class VenueSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(
        source='owner.username',
        read_only=True,
        help_text="Username of the venue owner (Read-only)."
    )
    # owner field itself will be read-only, set by the view.
    owner = serializers.PrimaryKeyRelatedField(
        read_only=True,
        help_text="ID of the user owning the venue. Set automatically on creation."
    )

    class Meta:
        model = Venue
        fields = [
            'id', 'name', 'address', 'capacity', 'amenities',
            'contact_email', 'contact_phone', 'website', 'description',
            'is_available', 'has_parking', 'has_public_transport',
            'owner', 'owner_username',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'created_at', 'updated_at',
            'owner', 'owner_username',
        ]
        extra_kwargs = {
            'name': {
                'help_text': "The official name of the venue."
            },
            'address': {
                'help_text': "The full street address of the venue."
            },
            'capacity': {
                'help_text': "Maximum guest capacity of the venue. Must be a positive integer."
            },
            'amenities': {
                'help_text': "Description of available amenities (e.g., 'Wi-Fi, Projector, Catering services'). Can be a comma-separated list or a descriptive text."
            },
            'contact_email': {
                'help_text': "Primary email address for venue inquiries."
            },
            'contact_phone': {
                'help_text': "Primary phone number for venue inquiries (e.g., '+12125552368'). Optional."
            },
            'website': {
                'help_text': "Official website URL of the venue. Optional."
            },
            'description': {
                'help_text': "A more detailed description of the venue. Optional."
            },
            'is_available': {
                'help_text': "Indicates if the venue is currently available for booking. Defaults to True."
            },
            'has_parking': {
                'help_text': "Indicates if on-site parking is available. Optional."
            },
            'has_public_transport': {
                'help_text': "Indicates if the venue is easily accessible by public transport. Optional."
            }
            # created_at and updated_at are usually handled as read-only by default
            # and their purpose is clear.
        }

    # If specific validation is needed beyond model validation, it can be added here.
    # For example, validating the format of 'website' or 'contact_phone' more strictly.
    # def validate_website(self, value):
    #     if value and not value.startswith(('http://', 'https://')):
    #         raise serializers.ValidationError("Website URL must start with 'http://' or 'https://'.")
    #     return value

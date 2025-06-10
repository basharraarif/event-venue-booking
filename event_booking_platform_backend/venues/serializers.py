from rest_framework import serializers
from .models import Venue

class VenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Venue
        fields = '__all__' # Keeps all model fields in the serializer
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

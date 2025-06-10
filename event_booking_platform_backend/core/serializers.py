from rest_framework import serializers
from .models import User

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=False, # Not required for updates, only for creation if not provided otherwise
        style={'input_type': 'password'},
        help_text="User's password. Required for creation. Will be hashed automatically."
    )
    phone_number = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Optional. User's phone number, e.g., '+12125552368'."
    )
    address = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        style={'base_template': 'textarea.html'}, # Suggests a larger input field in DRF browsable API
        help_text="Optional. User's full address."
    )

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'password', 'phone_number', 'address']
        extra_kwargs = {
            'email': {'required': True, 'help_text': "Required. A valid email address."},
            'username': {'help_text': "Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."},
            'first_name': {'help_text': "Optional."},
            'last_name': {'help_text': "Optional."}
        }

    def create(self, validated_data):
        # Use create_user to handle password hashing
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data.get('password'), # .get() because password might not be in validated_data if not required
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            phone_number=validated_data.get('phone_number'),
            address=validated_data.get('address')
        )
        return user

    def update(self, instance, validated_data):
        # Handle password update separately
        password = validated_data.pop('password', None)

        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password) # Hashes the password

        instance.save()
        return instance

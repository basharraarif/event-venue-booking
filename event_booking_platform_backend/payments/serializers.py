from rest_framework import serializers
from .models import Payment
from bookings.models import Booking # Ensure Booking is imported for validation

class PaymentSerializer(serializers.ModelSerializer):
    """
    Serializer for the Payment model.
    """
    booking_id = serializers.UUIDField(source='booking.id', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id',
            'booking_id',
            'amount',
            'currency',
            'status',
            'transaction_id',
            'payment_method',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'status', 'transaction_id']

class CreatePaymentSerializer(serializers.Serializer): # This one is likely for direct payment creation, not intent
    """
    Serializer for creating a payment (potentially legacy or for admin use).
    Requires booking_id and optionally amount and currency.
    """
    booking_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    currency = serializers.CharField(max_length=3, required=False, default='USD')

    def validate_booking_id(self, value):
        if not Booking.objects.filter(id=value).exists():
            raise serializers.ValidationError("Booking with this ID does not exist.")
        return value

class PaymentIntentCreateSerializer(serializers.Serializer):
    """
    Serializer for requesting the creation of a payment intent.
    Frontend will send booking_id. Amount and currency are derived from the booking.
    """
    booking_id = serializers.UUIDField()

    def validate_booking_id(self, value):
        try:
            booking = Booking.objects.get(id=value)
            # Check if booking is already paid or if payment is already pending
            if hasattr(booking, 'payment') and booking.payment.status in ['succeeded', 'requires_action']:
                 raise serializers.ValidationError(f"Booking has a payment that is already {booking.payment.status}.")
            if booking.status not in ['pending', 'confirmed']: # Or whatever statuses allow payment
                 raise serializers.ValidationError(f"Booking status '{booking.status}' does not allow payment initiation.")
        except Booking.DoesNotExist:
            raise serializers.ValidationError("Booking with this ID does not exist.")
        return value

class PaymentIntentResponseSerializer(serializers.Serializer):
    """
    Serializer for responding with the PaymentIntent's client secret.
    """
    client_secret = serializers.CharField()
    payment_id = serializers.UUIDField()

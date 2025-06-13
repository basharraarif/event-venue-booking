from rest_framework import serializers
from .models import Payment
from bookings.models import Booking # For validation
import logging

logger = logging.getLogger(__name__)

class PaymentIntentCreateSerializer(serializers.Serializer):
    """
    Serializer for creating a Payment Intent.
    Validates that the booking exists and requires payment.
    """
    booking_id = serializers.UUIDField()

    def validate_booking_id(self, value):
        try:
            booking = Booking.objects.get(id=value)
            if booking.total_price <= 0:
                logger.warning(f"PaymentIntent creation attempt for booking {value} with zero or negative total price.")
                raise serializers.ValidationError("Booking does not require payment (total price is zero or less).")

            # Check if the booking payment status itself indicates it's not pending or not required
            if booking.payment_status not in ['pending', 'failed']:
                 logger.warning(f"PaymentIntent creation attempt for booking {value} with payment_status '{booking.payment_status}'.")
                 raise serializers.ValidationError(f"Booking payment status is '{booking.payment_status}'. Payment intent can only be created for 'pending' or 'failed' payments.")

            # Check the associated Payment object status
            if hasattr(booking, 'payment'):
                if booking.payment.status not in ['pending', 'failed']:
                    logger.warning(f"PaymentIntent creation attempt for booking {value} where associated Payment object status is '{booking.payment.status}'.")
                    raise serializers.ValidationError(f"Associated payment record is in status '{booking.payment.status}'. Cannot create new intent.")
            else:
                # This case should ideally be handled: if a booking requires payment, a Payment object should exist.
                # However, if it doesn't, and the booking.payment_status is 'pending', we might allow creation.
                # This depends on the logic in booking creation. For now, let's assume a Payment object might not exist yet if booking.payment_status is 'pending'.
                logger.info(f"Booking {value} requires payment (total_price: {booking.total_price}, payment_status: {booking.payment_status}) but no associated Payment object found. This might be okay if one is created during this process.")

        except Booking.DoesNotExist:
            logger.error(f"PaymentIntent creation attempt for non-existent booking {value}.")
            raise serializers.ValidationError("Booking not found.")
        return value

class PaymentSerializer(serializers.ModelSerializer):
    """
    Serializer for the Payment model.
    """
    booking_id = serializers.UUIDField(source='booking.id', read_only=True)
    user_id = serializers.CharField(source='booking.user.id', read_only=True) # Changed to CharField if user ID is not UUID

    class Meta:
        model = Payment
        fields = [
            'id',
            'booking_id',
            'user_id',
            'amount',
            'currency',
            'status',
            'stripe_payment_intent_id',
            # 'payment_method', # Removed as Stripe handles this, unless storing last4 or brand
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id',
            'booking_id',
            'user_id',
            'amount',
            'currency',
            'status',
            'created_at',
            'updated_at',
            'stripe_payment_intent_id'
        ]

# Keep PaymentIntentResponseSerializer if it's useful for the views later
class PaymentIntentResponseSerializer(serializers.Serializer):
    """
    Serializer for responding with the PaymentIntent's client secret.
    """
    client_secret = serializers.CharField()
    payment_id = serializers.UUIDField()

# If CreatePaymentSerializer is not needed for Stripe flow, it can be removed or commented out.
# For now, let it be, might be used for admin or other flows.
class CreatePaymentSerializer(serializers.Serializer):
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

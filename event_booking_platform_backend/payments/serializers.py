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

            # Check the booking's main status.
            # A payment intent should typically only be created for bookings awaiting payment.
            if booking.status != Booking.BookingStatus.PENDING_PAYMENT:
                logger.warning(f"PaymentIntent creation attempt for booking {value} with status '{booking.status}'.")
                raise serializers.ValidationError(f"Booking status is '{booking.status}'. Payment intent can only be created for bookings in '{Booking.BookingStatus.PENDING_PAYMENT}' status.")

            # Check the associated Payment object status, if it exists.
            # A Payment object is usually created when booking moves to PENDING_PAYMENT.
            if hasattr(booking, 'payment') and booking.payment:
                if booking.payment.status not in ['pending', 'failed']: # Payment model statuses
                    logger.warning(f"PaymentIntent creation attempt for booking {value} where associated Payment object status is '{booking.payment.status}'.")
                    raise serializers.ValidationError(f"Associated payment record is in status '{booking.payment.status}'. Cannot create new intent for this payment.")
            else:
                # If booking status is PENDING_PAYMENT but no Payment object, this is unusual but might be allowed if PI creation also creates Payment.
                # The current CreatePaymentIntentView does a get_or_create for Payment.
                logger.info(f"Booking {value} is PENDING_PAYMENT (total_price: {booking.total_price}) but no associated Payment object found yet. One will be created or retrieved.")

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

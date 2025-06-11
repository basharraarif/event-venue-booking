from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import generics, status, views
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
import stripe

from bookings.models import Booking
from .models import Payment
from .serializers import (
    PaymentSerializer,
    PaymentIntentCreateSerializer,
    PaymentIntentResponseSerializer
)
from core.email_utils import send_booking_confirmation_email # Added import

stripe.api_key = settings.STRIPE_SECRET_KEY

class CreatePaymentIntentView(views.APIView):
    """
    View to create a Stripe PaymentIntent for a booking.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = PaymentIntentCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        booking_id = serializer.validated_data['booking_id']

        try:
            booking = Booking.objects.get(id=booking_id, user=request.user)
        except Booking.DoesNotExist:
            return Response({'error': 'Booking not found or you do not have permission to pay for it.'}, status=status.HTTP_404_NOT_FOUND)

        # Check if booking is already paid or has an active payment intent
        if hasattr(booking, 'payment') and booking.payment.status in ['succeeded', 'requires_action']:
            return Response({'error': f'Booking already has a payment with status: {booking.payment.status}.'}, status=status.HTTP_400_BAD_REQUEST)

        # Amount should be in cents for Stripe
        amount_cents = int(booking.total_price * 100)
        currency = booking.event.currency_code.lower() if hasattr(booking.event, 'currency_code') and booking.event.currency_code else 'usd' # Assuming currency on Event model or default

        # Create or update a Payment record
        payment, created = Payment.objects.get_or_create(
            booking=booking,
            defaults={
                'amount': booking.total_price,
                'currency': currency.upper(),
                'status': 'pending' # Initial status
            }
        )

        if not created and payment.status not in ['pending', 'failed', 'cancelled']:
             # If payment exists and is not in a re-payable state, don't create a new intent
            return Response(
                {'error': f'Payment already exists with status: {payment.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update payment details if it existed but was in a re-payable state (e.g. failed)
        payment.amount = booking.total_price
        payment.currency = currency.upper()
        payment.status = 'pending' # Reset status to pending

        try:
            if payment.stripe_payment_intent_id:
                # If a payment intent ID exists, try to retrieve and update it
                # This is useful if the previous attempt failed before confirmation
                intent = stripe.PaymentIntent.modify(
                    payment.stripe_payment_intent_id,
                    amount=amount_cents,
                    currency=currency,
                    metadata={'booking_id': str(booking.id), 'payment_id': str(payment.id)},
                )
            else:
                # Create a new PaymentIntent
                intent = stripe.PaymentIntent.create(
                    amount=amount_cents,
                    currency=currency,
                    metadata={'booking_id': str(booking.id), 'payment_id': str(payment.id)},
                    # payment_method_types=['card'], # You can specify payment method types
                )

            payment.stripe_payment_intent_id = intent.id
            payment.save()

            response_serializer = PaymentIntentResponseSerializer({'client_secret': intent.client_secret, 'payment_id': payment.id})
            return Response(response_serializer.data, status=status.HTTP_200_OK)

        except stripe.error.StripeError as e:
            payment.status = 'failed' # Mark payment as failed on Stripe error
            payment.save()
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # Log unexpected errors
            payment.status = 'failed'
            payment.save()
            return Response({'error': 'An unexpected error occurred.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StripeWebhookView(views.APIView):
    """
    View to handle webhook events from Stripe.
    """
    def post(self, request, *args, **kwargs):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

        if not endpoint_secret:
            # Log this critical error: Webhook secret not configured
            return Response({'error': 'Webhook secret not configured.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
        except ValueError as e:
            # Invalid payload
            return Response({'error': 'Invalid payload.'}, status=status.HTTP_400_BAD_REQUEST)
        except stripe.error.SignatureVerificationError as e:
            # Invalid signature
            return Response({'error': 'Invalid signature.'}, status=status.HTTP_400_BAD_REQUEST)

        # Handle the event
        payment_intent = None
        if event.type == 'payment_intent.succeeded':
            payment_intent = event.data.object
            payment_id = payment_intent.metadata.get('payment_id')
            try:
                payment = Payment.objects.get(id=payment_id, stripe_payment_intent_id=payment_intent.id)
                payment.status = 'succeeded'
                payment.save()
                # Update booking status (e.g., to 'confirmed')
                booking = payment.booking
                booking.status = 'confirmed'
                booking.save()
                # Send booking confirmation email
                try:
                    send_booking_confirmation_email(booking)
                except Exception as email_exc: # Catch potential errors during email sending
                    # Log this error, but don't let it fail the webhook response
                    print(f"Error sending confirmation email for booking {booking.id}: {email_exc}")
            except Payment.DoesNotExist:
                return Response({'error': 'Payment record not found for this succeeded intent.'}, status=status.HTTP_404_NOT_FOUND)

        elif event.type == 'payment_intent.payment_failed':
            payment_intent = event.data.object
            payment_id = payment_intent.metadata.get('payment_id')
            try:
                payment = Payment.objects.get(id=payment_id, stripe_payment_intent_id=payment_intent.id)
                payment.status = 'failed'
                payment.save()
                # Optionally, update booking status
            except Payment.DoesNotExist:
                # This might happen if the payment was initiated but no local record was finalized.
                # Log this for investigation.
                return Response({'error': 'Payment record not found for this failed intent.'}, status=status.HTTP_404_NOT_FOUND)

        elif event.type == 'payment_intent.requires_action':
            payment_intent = event.data.object
            payment_id = payment_intent.metadata.get('payment_id')
            try:
                payment = Payment.objects.get(id=payment_id, stripe_payment_intent_id=payment_intent.id)
                payment.status = 'requires_action'
                payment.save()
            except Payment.DoesNotExist:
                return Response({'error': 'Payment record not found for this intent requiring action.'}, status=status.HTTP_404_NOT_FOUND)

        elif event.type == 'payment_intent.canceled':
            payment_intent = event.data.object
            payment_id = payment_intent.metadata.get('payment_id')
            try:
                payment = Payment.objects.get(id=payment_id, stripe_payment_intent_id=payment_intent.id)
                payment.status = 'cancelled'
                payment.save()
            except Payment.DoesNotExist:
                return Response({'error': 'Payment record not found for this cancelled intent.'}, status=status.HTTP_404_NOT_FOUND)
        else:
            # Unhandled event type
            print(f'Unhandled event type {event.type}')

        return Response(status=status.HTTP_200_OK)


# Placeholder for retrieving payment details if needed by authenticated user
class PaymentDetailView(generics.RetrieveAPIView):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated] # Users should only see their own payments
    lookup_field = 'id' # or 'pk'

    def get_queryset(self):
        # Ensure users can only retrieve payments related to their bookings
        return Payment.objects.filter(booking__user=self.request.user)

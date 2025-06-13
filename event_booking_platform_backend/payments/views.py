import stripe
import logging
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from bookings.models import Booking
from .models import Payment
from .serializers import (
    PaymentSerializer,
    PaymentIntentCreateSerializer,
    PaymentIntentResponseSerializer,
)
from core.email_utils import send_booking_related_email
from drf_spectacular.utils import extend_schema, OpenApiRequest, OpenApiResponse

logger = logging.getLogger(__name__)

# Initialize Stripe API
stripe.api_key = settings.STRIPE_SECRET_KEY

@extend_schema(
    request=PaymentIntentCreateSerializer,
    responses={
        201: PaymentIntentResponseSerializer,
        200: PaymentIntentResponseSerializer, # For existing PI
        400: OpenApiResponse(description="Bad Request - Invalid input, booking not payable, or already paid"),
        401: OpenApiResponse(description="Unauthorized - Authentication required"),
        404: OpenApiResponse(description="Not Found - Booking not found or permission denied"),
        500: OpenApiResponse(description="Internal Server Error - Stripe API error or other unexpected error")
    },
    summary="Create or Retrieve Stripe Payment Intent",
    description="""Given a `booking_id`, this endpoint creates a new Stripe PaymentIntent
    or retrieves an existing one if the payment is still pending.
    It returns the `client_secret` needed by the frontend to confirm the payment with Stripe.
    """
)
class CreatePaymentIntentView(APIView):
    """
    Creates a Stripe PaymentIntent for a booking or retrieves an existing one.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = PaymentIntentCreateSerializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"PaymentIntentCreateSerializer validation error: {serializer.errors} for user {request.user.id if request.user else 'Anonymous'}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        booking_id = serializer.validated_data['booking_id']
        user = request.user

        try:
            booking = Booking.objects.select_related('event', 'payment').get(id=booking_id, user=user)
        except Booking.DoesNotExist:
            logger.warn(f"User {user.id} attempted to create payment intent for non-existent or unauthorized booking {booking_id}")
            return Response({'error': 'Booking not found or you do not have permission to pay for it.'}, status=status.HTTP_404_NOT_FOUND)

        if booking.total_price <= 0:
            logger.info(f"Booking {booking_id} by user {user.id} does not require payment (total price: {booking.total_price}).")
            return Response({'error': 'This booking does not require payment.'}, status=status.HTTP_400_BAD_REQUEST)

        # Get or create a Payment object
        payment, created = Payment.objects.get_or_create(
            booking=booking,
            defaults={
                'amount': booking.total_price,
                'currency': booking.event.currency if booking.event.currency else 'USD', # Assuming event has currency, else default
                'status': 'pending', # Initial status
            }
        )

        if not created and payment.status == 'succeeded':
            logger.info(f"User {user.id} attempted to create payment intent for already paid booking {booking_id} (Payment {payment.id})")
            return Response({'error': 'This booking has already been paid.'}, status=status.HTTP_400_BAD_REQUEST)

        if not created and payment.status == 'pending' and payment.stripe_payment_intent_id:
            # If a pending payment intent already exists, try to retrieve and return it
            # This avoids creating multiple payment intents for the same payment object if user retries.
            try:
                intent = stripe.PaymentIntent.retrieve(payment.stripe_payment_intent_id)
                logger.info(f"Returning existing PaymentIntent {intent.id} for booking {booking_id} for user {user.id}")
                response_serializer = PaymentIntentResponseSerializer(data={'client_secret': intent.client_secret, 'payment_id': payment.id})
                response_serializer.is_valid(raise_exception=True)
                return Response(response_serializer.data, status=status.HTTP_200_OK)
            except stripe.error.StripeError as e:
                logger.warning(f"Failed to retrieve existing PaymentIntent {payment.stripe_payment_intent_id} for booking {booking_id}: {e}. A new one will be created.")

        # Update payment amount if it changed (e.g. booking was modified)
        # Only if payment is still pending.
        if payment.status == 'pending' and payment.amount != booking.total_price:
            payment.amount = booking.total_price
            # Potentially update currency if that can change too
            payment.currency = booking.event.currency if booking.event.currency else 'USD'


        try:
            # Ensure amount is in cents for Stripe
            amount_in_cents = int(booking.total_price * 100)

            payment_intent_params = {
                'amount': amount_in_cents,
                'currency': payment.currency.lower(), # Stripe expects lowercase currency
                'metadata': {
                    'booking_id': str(booking.id),
                    'user_id': str(user.id),
                    'payment_db_id': str(payment.id),
                },
                # 'automatic_payment_methods': {'enabled': True}, # Recommended by Stripe
            }

            if payment.stripe_payment_intent_id:
                # Try to update existing payment intent if possible and still pending
                logger.info(f"Attempting to update existing PaymentIntent {payment.stripe_payment_intent_id} for booking {booking_id}")
                intent = stripe.PaymentIntent.modify(
                    payment.stripe_payment_intent_id,
                    amount=amount_in_cents, # Update amount if it changed
                    currency=payment.currency.lower(),
                    metadata=payment_intent_params['metadata'] # Update metadata
                )
            else:
                # Create a new PaymentIntent
                logger.info(f"Creating new PaymentIntent for booking {booking_id} with amount {amount_in_cents} {payment.currency.lower()}")
                intent = stripe.PaymentIntent.create(**payment_intent_params)

            payment.stripe_payment_intent_id = intent.id
            # Status of Payment model could be 'requires_payment_method' if Stripe says so,
            # but 'pending' is fine as our internal status until webhook confirmation.
            payment.status = 'pending'
            payment.save()

            # Update booking payment_status
            booking.payment_status = 'pending'
            booking.save(update_fields=['payment_status'])

            logger.info(f"PaymentIntent {intent.id} created/updated for booking {booking_id} (Payment {payment.id}) by user {user.id}")
            response_serializer = PaymentIntentResponseSerializer(data={'client_secret': intent.client_secret, 'payment_id': payment.id})
            response_serializer.is_valid(raise_exception=True)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except stripe.error.StripeError as e:
            logger.error(f"Stripe API error while creating/updating PaymentIntent for booking {booking_id} (Payment {payment.id}): {e}")
            # Update payment status to 'failed' if PI creation fails critically
            payment.status = 'failed'
            payment.save(update_fields=['status'])
            booking.payment_status = 'failed'
            booking.save(update_fields=['payment_status'])
            return Response({'error': f'Stripe error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"Generic error while creating/updating PaymentIntent for booking {booking_id} (Payment {payment.id}): {e}")
            payment.status = 'failed'
            payment.save(update_fields=['status'])
            booking.payment_status = 'failed'
            booking.save(update_fields=['payment_status'])
            return Response({'error': 'An unexpected error occurred.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StripeWebhookView(APIView):
    """
    Handles webhook events from Stripe.
    """
    permission_classes = [AllowAny] # Webhooks come from Stripe, not a logged-in user

    @extend_schema(
        request=OpenApiRequest(request=None), # Stripe sends a JSON body, not tied to a specific serializer on our end for request schema.
        # Alternatively, could define a generic serializer if we want to show an example payload structure.
        # For now, None indicates that drf-spectacular should not try to map it to a serializer.
        # The description of the payload can be in the main summary/description of the endpoint.
        responses={
            200: OpenApiResponse(description="Webhook received and processed successfully (or acknowledged for unhandled events)."),
            400: OpenApiResponse(description="Bad Request - Invalid payload or signature."),
            500: OpenApiResponse(description="Internal Server Error - Webhook secret not configured.")
        },
        summary="Stripe Webhook Handler",
        description="""Handles incoming webhook events from Stripe to update payment statuses,
        booking statuses, and send notifications.
        This endpoint should be configured in your Stripe dashboard.
        It verifies the Stripe signature for security.
        Currently handles: `payment_intent.succeeded`, `payment_intent.payment_failed`.
        """
    )
    def post(self, request, *args, **kwargs):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        event = None

        if not settings.STRIPE_WEBHOOK_SECRET:
            logger.error("STRIPE_WEBHOOK_SECRET is not configured.")
            return Response({'error': 'Webhook secret not configured.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
            logger.info(f"Received Stripe webhook event: {event.id}, type: {event.type}")
        except ValueError as e:
            # Invalid payload
            logger.error(f"Invalid webhook payload: {e}")
            return Response({'error': 'Invalid payload'}, status=status.HTTP_400_BAD_REQUEST)
        except stripe.error.SignatureVerificationError as e:
            # Invalid signature
            logger.error(f"Webhook signature verification failed: {e}")
            return Response({'error': 'Invalid signature'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Webhook construction error: {e}")
            return Response({'error': 'Webhook error'}, status=status.HTTP_400_BAD_REQUEST)

        # Handle the event
        payment_intent = None
        if event.type == 'payment_intent.succeeded':
            payment_intent = event.data.object
            logger.info(f"PaymentIntent {payment_intent.id} succeeded.")
            self.handle_payment_success(payment_intent)
        elif event.type == 'payment_intent.payment_failed':
            payment_intent = event.data.object
            logger.error(f"PaymentIntent {payment_intent.id} failed. Reason: {payment_intent.last_payment_error.message if payment_intent.last_payment_error else 'N/A'}")
            self.handle_payment_failure(payment_intent)
        # Could handle other event types like 'payment_intent.requires_action', etc.
        else:
            logger.info(f"Received unhandled Stripe event type: {event.type}")

        return Response({'status': 'success'}, status=status.HTTP_200_OK)

    def handle_payment_success(self, payment_intent):
        payment_intent_id = payment_intent.id
        metadata = payment_intent.metadata
        payment_db_id = metadata.get('payment_db_id')
        booking_id = metadata.get('booking_id')

        try:
            # It's safer to use payment_db_id if available and unique
            if payment_db_id:
                 payment = Payment.objects.select_related('booking', 'booking__user').get(id=payment_db_id, stripe_payment_intent_id=payment_intent_id)
            else: # Fallback if payment_db_id not in metadata (older PIs or different setup)
                 payment = Payment.objects.select_related('booking', 'booking__user').get(stripe_payment_intent_id=payment_intent_id)

            if payment.status == 'succeeded':
                logger.info(f"Payment {payment.id} for PI {payment_intent_id} already marked as succeeded. Webhook possibly resent.")
                return

            payment.status = 'succeeded'
            # payment.payment_method_details = payment_intent.payment_method_details # Store if needed
            payment.save()

            booking = payment.booking
            booking.payment_status = 'paid'
            booking.status = Booking.BookingStatus.CONFIRMED # Confirm booking upon successful payment
            booking.save(update_fields=['payment_status', 'status'])

            logger.info(f"Payment {payment.id} (Booking {booking.id}) successfully processed. Booking status updated to {booking.status}.")

            # Send confirmation email
            try:
                send_booking_related_email(
                    booking=booking,
                    subject_template_name='emails/payment_confirmation_subject.txt',
                    body_html_template_name='emails/payment_confirmation_body.html',
                    body_text_template_name='emails/payment_confirmation_body.txt',
                    payment=payment # Pass payment object if template needs it
                )
                logger.info(f"Payment confirmation email sent for booking {booking.id}.")
            except Exception as e:
                logger.error(f"Error sending payment confirmation email for booking {booking.id}: {e}")

        except Payment.DoesNotExist:
            logger.error(f"Payment record not found for PaymentIntent ID {payment_intent_id} or payment_db_id {payment_db_id}. Cannot update status.")
        except Booking.DoesNotExist: # Should not happen if Payment record exists with booking FK
            logger.error(f"Booking record not found for associated PaymentIntent ID {payment_intent_id}. Critical error.")
        except Exception as e:
            logger.error(f"Error in handle_payment_success for PI {payment_intent_id}: {e}")


    def handle_payment_failure(self, payment_intent):
        payment_intent_id = payment_intent.id
        metadata = payment_intent.metadata
        payment_db_id = metadata.get('payment_db_id')
        booking_id = metadata.get('booking_id')

        try:
            if payment_db_id:
                 payment = Payment.objects.select_related('booking', 'booking__user').get(id=payment_db_id, stripe_payment_intent_id=payment_intent_id)
            else:
                 payment = Payment.objects.select_related('booking', 'booking__user').get(stripe_payment_intent_id=payment_intent_id)

            payment.status = 'failed'
            # payment.failure_reason = payment_intent.last_payment_error.message if payment_intent.last_payment_error else "Unknown" # Store if model has this field
            payment.save()

            booking = payment.booking
            booking.payment_status = 'failed'
            # Decide on booking status, e.g., back to PENDING_PAYMENT or keep as is if user can retry with same booking
            # booking.status = Booking.BookingStatus.PENDING_PAYMENT
            booking.save(update_fields=['payment_status'])

            logger.info(f"Payment {payment.id} (Booking {booking.id}) failed. Payment and Booking status updated.")

            # Send payment failure email
            try:
                send_booking_related_email(
                    booking=booking,
                    subject_template_name='emails/payment_failed_subject.txt',
                    body_html_template_name='emails/payment_failed_body.html',
                    body_text_template_name='emails/payment_failed_body.txt',
                    payment=payment # Pass payment object if template needs it
                )
                logger.info(f"Payment failure email sent for booking {booking.id}.")
            except Exception as e:
                logger.error(f"Error sending payment failure email for booking {booking.id}: {e}")

        except Payment.DoesNotExist:
            logger.error(f"Payment record not found for PaymentIntent ID {payment_intent_id} or payment_db_id {payment_db_id} on failure. Cannot update status.")
        except Exception as e:
            logger.error(f"Error in handle_payment_failure for PI {payment_intent_id}: {e}")


class PaymentViewSet(viewsets.ReadOnlyModelViewSet): # Changed to ReadOnly as creation is via PaymentIntent
    """
    ViewSet for managing Payments.
    Provides read-only access to payments for authenticated users (admins or own payments).
    """
    queryset = Payment.objects.all().select_related('booking', 'booking__user', 'booking__event')
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated] # Or custom permission for admin/owner

    def get_queryset(self):
        user = self.request.user
        if user.is_staff: # Admins can see all payments
            return super().get_queryset().order_by('-created_at')
        # Regular users can only see their own payments
        return super().get_queryset().filter(booking__user=user).order_by('-created_at')

# Note: The original PaymentViewSet had custom actions 'succeed_payment' and 'fail_payment'.
# These are removed as this functionality is now handled by the StripeWebhookView based on
# actual payment events from Stripe, which is a more robust approach.
# Direct creation of Payment objects via this ViewSet is also removed; payments are created
# or updated during the PaymentIntent flow.

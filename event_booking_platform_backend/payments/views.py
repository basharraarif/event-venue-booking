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

            # Update booking payment_status and payment_intent_id
            # booking.payment_status = 'pending' # This field was removed
            booking.payment_intent_id = intent.id # Store Stripe PaymentIntent ID on the booking
            booking.save(update_fields=['payment_intent_id']) # Removed 'payment_status'

            logger.info(f"PaymentIntent {intent.id} created/updated for booking {booking_id} (Payment {payment.id}, Booking PI ID: {booking.payment_intent_id}) by user {user.id}")
            response_serializer = PaymentIntentResponseSerializer(data={'client_secret': intent.client_secret, 'payment_id': payment.id})
            response_serializer.is_valid(raise_exception=True)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except stripe.error.StripeError as e:
            logger.error(f"Stripe API error while creating/updating PaymentIntent for booking {booking_id} (Payment {payment.id}): {e}")
            # Update payment status to 'failed' if PI creation fails critically
            payment.status = 'failed'
            payment.save(update_fields=['status'])
            # booking.payment_status = 'failed' # This field was removed
            # booking.save(update_fields=['payment_status']) # Removed 'payment_status'
            # No need to update booking.payment_intent_id here if PI creation failed before ID was known
            return Response({'error': f'Stripe error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"Generic error while creating/updating PaymentIntent for booking {booking_id} (Payment {payment.id}): {e}")
            payment.status = 'failed' # Ensure payment status is marked failed.
            payment.save(update_fields=['status'])
            # booking.payment_status = 'failed' # This field was removed
            # booking.save(update_fields=['payment_status']) # Removed 'payment_status'
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
        stripe_pi_id = payment_intent.id
        logger.info(f"Processing payment_intent.succeeded for Stripe PI ID: {stripe_pi_id}")

        try:
            booking = Booking.objects.select_related('user', 'event').get(payment_intent_id=stripe_pi_id)
            logger.info(f"Found booking {booking.id} via payment_intent_id {stripe_pi_id}")

            # Update Booking status
            if booking.status == Booking.BookingStatus.CONFIRMED:
                logger.info(f"Booking {booking.id} is already confirmed. Webhook possibly resent or status already updated.")
                # Optionally, ensure related Payment object is also consistent.
            else:
                booking.status = Booking.BookingStatus.CONFIRMED
                booking.save(update_fields=['status'])
                logger.info(f"Booking {booking.id} status updated to CONFIRMED.")

            # Update or create associated Payment record for history/consistency
            payment, created = Payment.objects.get_or_create(
                booking=booking,
                defaults={
                    'amount': booking.total_price, # Ensure this is correct; PI amount might be better
                    'currency': payment_intent.currency.upper(),
                    'stripe_payment_intent_id': stripe_pi_id,
                    'status': 'succeeded',
                }
            )
            if not created and payment.status != 'succeeded':
                payment.status = 'succeeded'
                payment.stripe_payment_intent_id = stripe_pi_id # Ensure PI ID is set
                if payment.amount != (payment_intent.amount / 100): # Stripe amount is in cents
                    payment.amount = payment_intent.amount / 100
                payment.currency = payment_intent.currency.upper()
                payment.save()
                logger.info(f"Existing Payment record {payment.id} for Booking {booking.id} updated to succeeded.")
            elif created:
                logger.info(f"New Payment record {payment.id} created for Booking {booking.id} with status succeeded.")
            else:
                logger.info(f"Payment record {payment.id} for Booking {booking.id} already marked succeeded.")

            # Ensure booking has the payment_intent_id if it was somehow missed (belt and braces)
            if not booking.payment_intent_id:
                booking.payment_intent_id = stripe_pi_id
                booking.save(update_fields=['payment_intent_id'])

            logger.info(f"Payment for booking {booking.id} (Stripe PI: {stripe_pi_id}) successfully processed.")

            # Send confirmation email
            try:
                send_booking_related_email(
                    booking=booking,
                    subject_template_name='emails/booking_confirmation_subject.txt', # Corrected template name
                    body_html_template_name='emails/booking_confirmation_body.html', # Corrected template name
                    body_text_template_name='emails/booking_confirmation_body.txt',   # Corrected template name
                    payment=payment # Pass the updated/created payment object
                )
                logger.info(f"Payment confirmation email sent for booking {booking.id}.")
            except Exception as e:
                logger.error(f"Error sending payment confirmation email for booking {booking.id}: {e}")

        except Booking.DoesNotExist:
            logger.error(f"Booking not found for Stripe PaymentIntent ID {stripe_pi_id}. Cannot update status.")
            # Consider if a Payment record should be searched or created if booking is not found by PI.
            # For now, if Booking.payment_intent_id is the source of truth, this is the main failure point.
        except Exception as e:
            logger.error(f"Error in handle_payment_success for Stripe PI {stripe_pi_id}: {e}")


    def handle_payment_failure(self, payment_intent):
        stripe_pi_id = payment_intent.id
        logger.info(f"Processing payment_intent.payment_failed for Stripe PI ID: {stripe_pi_id}")

        try:
            booking = Booking.objects.select_related('user', 'event').get(payment_intent_id=stripe_pi_id)
            logger.info(f"Found booking {booking.id} via payment_intent_id {stripe_pi_id} for failure processing.")

            # Booking status typically remains PENDING_PAYMENT or similar; payment failure doesn't auto-cancel booking.
            # Business logic might dictate other status changes (e.g., to FAILED if too many retries).
            # For now, we primarily update the Payment model.

            # Update or create associated Payment record
            payment, created = Payment.objects.get_or_create(
                booking=booking,
                defaults={ # Defaults if creating new
                    'amount': payment_intent.amount / 100,
                    'currency': payment_intent.currency.upper(),
                    'stripe_payment_intent_id': stripe_pi_id,
                    'status': 'failed',
                }
            )
            if not created and payment.status != 'failed':
                payment.status = 'failed'
                payment.stripe_payment_intent_id = stripe_pi_id # Ensure PI ID is set
                if payment.amount != (payment_intent.amount / 100):
                    payment.amount = payment_intent.amount / 100
                payment.currency = payment_intent.currency.upper()
                # Store failure reason if your Payment model has such a field
                # payment.failure_reason = payment_intent.last_payment_error.message if payment_intent.last_payment_error else "Unknown"
                payment.save()
                logger.info(f"Existing Payment record {payment.id} for Booking {booking.id} updated to failed.")
            elif created:
                logger.info(f"New Payment record {payment.id} created for Booking {booking.id} with status failed.")
            else:
                 logger.info(f"Payment record {payment.id} for Booking {booking.id} already marked failed.")

            # Ensure booking has the payment_intent_id if it was somehow missed
            if not booking.payment_intent_id:
                booking.payment_intent_id = stripe_pi_id
                booking.save(update_fields=['payment_intent_id'])

            logger.info(f"Payment failure for booking {booking.id} (Stripe PI: {stripe_pi_id}) processed.")

            # Send payment failure email
            try:
                send_booking_related_email(
                    booking=booking,
                    subject_template_name='emails/payment_failed_subject.txt',
                    body_html_template_name='emails/payment_failed_body.html',
                    body_text_template_name='emails/payment_failed_body.txt',
                    payment=payment # Pass the updated/created payment object
                )
                logger.info(f"Payment failure email sent for booking {booking.id}.")
            except Exception as e:
                logger.error(f"Error sending payment failure email for booking {booking.id}: {e}")

        except Booking.DoesNotExist:
            logger.error(f"Booking not found for Stripe PaymentIntent ID {stripe_pi_id} on failure. Cannot update status.")
        except Exception as e:
            logger.error(f"Error in handle_payment_failure for Stripe PI {stripe_pi_id}: {e}")


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

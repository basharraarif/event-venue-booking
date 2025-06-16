import stripe
from django.conf import settings
from django.urls import reverse
from ..bookings.models import Booking # Assuming Booking model is in bookings.models

stripe.api_key = settings.STRIPE_SECRET_KEY

def create_payment_intent(booking_id, request):
    """
    Creates a Stripe PaymentIntent for a given booking.
    Returns the client_secret for the frontend and payment_intent_id for storage.
    """
    try:
        booking = Booking.objects.get(id=booking_id)
        if not booking:
            raise ValueError("Booking not found.")

        if booking.total_price <= 0:
            raise ValueError("Booking total price must be greater than zero to create a payment intent.")

        # Convert decimal to cents (Stripe expects amount in smallest currency unit)
        amount_in_cents = int(booking.total_price * 100)

        # Create PaymentIntent
        intent = stripe.PaymentIntent.create(
            amount=amount_in_cents,
            currency='usd',  # Or get from settings/booking
            metadata={
                'booking_id': booking.id,
                'user_id': booking.user.id,
                'event_id': booking.event.id
            },
            # automatic_payment_methods={"enabled": True}, # Enable this for dynamic payment methods
            # payment_method_types=['card'], # Or specify payment method types
        )

        # Update booking with payment_intent_id
        booking.payment_intent_id = intent.id
        booking.save()

        return {
            'client_secret': intent.client_secret,
            'payment_intent_id': intent.id
        }
    except Booking.DoesNotExist:
        # Handle case where booking is not found
        # Log error or raise custom exception
        return None # Or raise
    except stripe.error.StripeError as e:
        # Handle Stripe API errors
        # Log error (e.g., logger.error(f"Stripe error: {e.user_message}"))
        # You might want to raise a custom exception or return an error indicator
        raise e # Re-raise for now, or handle more gracefully
    except Exception as e:
        # Handle other unexpected errors
        # Log error
        raise e # Re-raise for now


def retrieve_payment_intent(payment_intent_id):
    """
    Retrieves a PaymentIntent from Stripe.
    """
    try:
        intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        return intent
    except stripe.error.StripeError as e:
        # Handle Stripe API errors
        raise e
    except Exception as e:
        # Handle other unexpected errors
        raise e

def handle_stripe_webhook(payload, sig_header):
    """
    Handles incoming Stripe webhook events.
    Verifies the signature and processes the event.
    """
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError as e:
        # Invalid payload
        # Log error: logger.error("Invalid webhook payload.")
        return {'status': 'invalid payload'}, 400
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        # Log error: logger.error("Invalid webhook signature.")
        return {'status': 'invalid signature'}, 400
    except Exception as e:
        # Log error: logger.error(f"Webhook construction error: {str(e)}")
        return {'status': f'error: {str(e)}'}, 500

    # Handle the event
    if event.type == 'payment_intent.succeeded':
        payment_intent = event.data.object  # contains a stripe.PaymentIntent
        # Logic to update booking status, send confirmation email, etc.
        booking_id = payment_intent.metadata.get('booking_id')
        if booking_id:
            try:
                booking = Booking.objects.get(id=booking_id, payment_intent_id=payment_intent.id)
                booking.status = Booking.BookingStatus.CONFIRMED # Or your equivalent status
                # Potentially update other fields like payment_time
                booking.save()
                # Trigger email notification (separate task)
                # logger.info(f"Payment succeeded for booking {booking_id}. Status updated to Confirmed.")
            except Booking.DoesNotExist:
                # logger.error(f"Booking not found for successful payment_intent {payment_intent.id}")
                pass # Or handle as an error
            except Exception as e:
                # logger.error(f"Error updating booking for successful payment_intent {payment_intent.id}: {str(e)}")
                pass # Or handle as an error
        else:
            # logger.warning(f"Booking ID not found in metadata for successful payment_intent {payment_intent.id}")
            pass

    elif event.type == 'payment_intent.payment_failed':
        payment_intent = event.data.object
        # Logic to update booking status, notify user, etc.
        booking_id = payment_intent.metadata.get('booking_id')
        if booking_id:
            try:
                booking = Booking.objects.get(id=booking_id, payment_intent_id=payment_intent.id)
                booking.status = Booking.BookingStatus.FAILED # Or your equivalent status
                booking.save()
                # Trigger email notification (separate task)
                # logger.info(f"Payment failed for booking {booking_id}. Status updated to Failed.")
            except Booking.DoesNotExist:
                # logger.error(f"Booking not found for failed payment_intent {payment_intent.id}")
                pass
            except Exception as e:
                # logger.error(f"Error updating booking for failed payment_intent {payment_intent.id}: {str(e)}")
                pass
        else:
            # logger.warning(f"Booking ID not found in metadata for failed payment_intent {payment_intent.id}")
            pass

    # ... handle other event types
    else:
        # logger.info(f'Unhandled event type {event.type}')
        pass

    return {'status': 'success'}, 200

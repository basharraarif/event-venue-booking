from django.core.mail import EmailMultiAlternatives, send_mail # Added EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags # To create plain text from HTML

# from ..bookings.models import Booking # Avoid top-level import if it causes issues with app loading order

def send_booking_confirmation_email(booking_instance):
    """
    Sends a booking confirmation email (HTML and plain text) to the user.

    Args:
        booking_instance: The Booking model instance.
    """
    if not hasattr(booking_instance, 'user') or not hasattr(booking_instance.user, 'email'):
        print(f"Cannot send confirmation for Booking ID {booking_instance.id}: User or user email missing.")
        return
    if not hasattr(booking_instance, 'event') or not hasattr(booking_instance.event, 'name'):
        print(f"Cannot send confirmation for Booking ID {booking_instance.id}: Event details missing.")
        return

    user_email = booking_instance.user.email
    event_name = booking_instance.event.name
    num_tickets = booking_instance.number_of_tickets
    total_price = booking_instance.total_price
    # Assuming currency_code exists on event model, otherwise default
    currency = booking_instance.event.currency_code if hasattr(booking_instance.event, 'currency_code') and booking_instance.event.currency_code else 'USD'
    # Assuming start_time exists for event_date
    event_date = booking_instance.event.start_time if hasattr(booking_instance.event, 'start_time') else None


    subject = f"Your Booking Confirmation for {event_name}"

    context = {
        'user': booking_instance.user,
        'booking_id': booking_instance.id,
        'event_name': event_name,
        'num_tickets': num_tickets,
        'total_price': total_price,
        'currency': currency,
        'event_date': event_date,
    }

    try:
        html_content = render_to_string('emails/booking_confirmation.html', context)
        text_content = strip_tags(html_content) # Basic plain text version from HTML

        # Fallback plain text message if stripping HTML is not good enough or for more control
        # text_content_manual = f"""
        # Dear {booking_instance.user.username or 'Customer'},
        # ... (construct your full plain text message here if needed)
        # """

        from_email = settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@example.com'

        msg = EmailMultiAlternatives(subject, text_content, from_email, [user_email])
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)

        print(f"Booking confirmation email sent successfully to {user_email} for Booking ID {booking_instance.id}")

    except Exception as e:
        print(f"Error sending booking confirmation email to {user_email} for Booking ID {booking_instance.id}: {e}")

# Placeholder for future use
def send_payment_receipt_email(payment_instance):
    pass

from django.core.mail import EmailMultiAlternatives, send_mail # Added EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

def send_booking_related_email(booking, subject_template_name, body_html_template_name, body_text_template_name):
    """
    Sends a booking-related email (HTML and plain text) to the user.

    Args:
        booking: The Booking model instance.
        subject_template_name: Path to the subject template file.
        body_html_template_name: Path to the HTML body template file.
        body_text_template_name: Path to the plain text body template file.
    """
    if not hasattr(booking, 'user') or not hasattr(booking.user, 'email'):
        print(f"Cannot send email for Booking ID {booking.id}: User or user email missing.")
        return
    if not hasattr(booking, 'event') or not hasattr(booking.event, 'name'):
        print(f"Cannot send email for Booking ID {booking.id}: Event details missing.")
        return

    user_email = booking.user.email
    event_name = booking.event.name
    num_tickets = booking.number_of_tickets
    total_price = booking.total_price
    currency = booking.event.currency_code if hasattr(booking.event, 'currency_code') and booking.event.currency_code else 'USD'
    event_date = booking.event.start_time if hasattr(booking.event, 'start_time') else None
    venue_name = booking.event.venue.name if hasattr(booking.event, 'venue') and hasattr(booking.event.venue, 'name') else 'N/A'
    transaction_id = getattr(getattr(booking, 'payment', None), 'transaction_id', None)


    context = {
        'user_name': booking.user.username, # Use username for personalization
        'booking_id': booking.id,
        'event_name': event_name,
        'num_tickets': num_tickets,
        'total_price': total_price,
        'currency': currency,
        'event_date': event_date,
        'venue_name': venue_name,
        'transaction_id': transaction_id,
        # Add any other context variables your templates might need
    }

    try:
        subject = render_to_string(subject_template_name, context).strip() # .strip() to remove newlines
        html_content = render_to_string(body_html_template_name, context)

        # Attempt to render a separate text template if provided and valid
        try:
            text_content = render_to_string(body_text_template_name, context)
        except Exception: # Catch if text template is missing or has errors
            text_content = strip_tags(html_content) # Fallback to stripping HTML

        from_email = settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@example.com'

        msg = EmailMultiAlternatives(subject, text_content, from_email, [user_email])
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)

        print(f"Booking-related email '{subject}' sent successfully to {user_email} for Booking ID {booking.id}")

    except Exception as e:
        print(f"Error sending booking-related email to {user_email} for Booking ID {booking.id}: {e}")


# This function is now replaced by the more generic send_booking_related_email
# It's kept here for reference or if other parts of the system still use it directly,
# but new integrations should use send_booking_related_email.
def send_booking_confirmation_email(booking_instance):
    """
    Sends a booking confirmation email. This is a specific use case of send_booking_related_email.
    """
    send_booking_related_email(
        booking=booking_instance,
        subject_template_name='emails/booking_confirmation_subject.txt',
        body_html_template_name='emails/booking_confirmation_body.html',
        body_text_template_name='emails/booking_confirmation_body.txt'
    )

# Placeholder for future use (if needed, or can be removed)
def send_payment_receipt_email(payment_instance):
    # This might need a different structure if it's purely about payment and not directly a booking lifecycle event.
    # For now, if it's tied to a booking's payment success, send_booking_confirmation_email (now send_booking_related_email) covers it.
    pass

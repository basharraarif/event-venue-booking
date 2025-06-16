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
    print(f"Attempting to send email for Booking ID {booking.id} - Step 1: Start of function")
    if not hasattr(booking, 'user') or not hasattr(booking.user, 'email') or not booking.user.email: # Added check for empty email
        print(f"Cannot send email for Booking ID {booking.id}: User or user email missing/empty.")
        return
    if not hasattr(booking, 'event') or not hasattr(booking.event, 'name'):
        print(f"Cannot send email for Booking ID {booking.id}: Event details missing.")
        return

    user_email = booking.user.email
    event_name = booking.event.name
    num_tickets = booking.number_of_tickets
    total_price = booking.total_price
    # Event model does not have currency_code. Payment model has currency.
    payment_currency = 'USD' # Default currency
    if hasattr(booking, 'payment') and booking.payment and hasattr(booking.payment, 'currency'):
        payment_currency = booking.payment.currency
    currency = payment_currency
    event_date = booking.event.start_time if hasattr(booking.event, 'start_time') else None
    venue_name = booking.event.venue.name if hasattr(booking.event, 'venue') and hasattr(booking.event.venue, 'name') else 'N/A'
    transaction_id = None
    if hasattr(booking, 'payment') and booking.payment:
        transaction_id = getattr(booking.payment, 'stripe_payment_intent_id', None)


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
        print(f"Attempting to send email for Booking ID {booking.id} - Step 2: Context created")
        subject = render_to_string(subject_template_name, context).strip() # .strip() to remove newlines
        html_content = render_to_string(body_html_template_name, context)

        # Attempt to render a separate text template if provided and valid
        try:
            text_content = render_to_string(body_text_template_name, context)
        except Exception: # Catch if text template is missing or has errors
            text_content = strip_tags(html_content) # Fallback to stripping HTML

        print(f"Attempting to send email for Booking ID {booking.id} - Step 3: Content rendered")
        from_email = settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@example.com'

        msg = EmailMultiAlternatives(subject, text_content, from_email, [user_email])
        msg.attach_alternative(html_content, "text/html")
        print(f"Attempting to send email for Booking ID {booking.id} - Step 4: About to call msg.send()")
        msg.send(fail_silently=False)

        print(f"Booking-related email '{subject}' sent successfully to {user_email} for Booking ID {booking.id}")
        print(f"Attempting to send email for Booking ID {booking.id} - Step 5: Email sent")

    except Exception as e:
        print(f"Error sending booking-related email to {user_email} for Booking ID {booking.id}: {e}")
        print(f"Attempting to send email for Booking ID {booking.id} - Step 6: Exception caught - {e}")


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


def send_booking_cancellation_email(booking_instance):
    """
    Sends a booking cancellation email.
    """
    send_booking_related_email(
        booking=booking_instance,
        subject_template_name='emails/booking_cancellation_subject.txt',
        body_html_template_name='emails/booking_cancellation_body.html',
        body_text_template_name='emails/booking_cancellation_body.txt'
    )

def send_payment_failure_email(booking_instance):
    """
    Sends a payment failure notification email for a booking.
    """
    # The generic send_booking_related_email context should be mostly sufficient.
    # We might want to add specific error messages if available on the booking/payment.
    # For now, using the standard context.
    send_booking_related_email(
        booking=booking_instance,
        subject_template_name='emails/payment_failed_subject.txt',
        body_html_template_name='emails/payment_failed_body.html',
        body_text_template_name='emails/payment_failed_body.txt'
    )

def send_new_user_registration_email(user_instance):
    """
    Sends a welcome email to a newly registered user.
    """
    if not user_instance or not user_instance.email:
        print(f"Cannot send registration email: User or user email missing/empty for User ID {user_instance.id if user_instance else 'N/A'}.")
        return

    context = {
        'user_name': user_instance.username,
        'user_email': user_instance.email,
        # Add any other context variables your templates might need, e.g., login_url
        # 'login_url': reverse('account_login') # Example if you have named URL routes
    }

    subject_template_name = 'emails/new_user_registration_subject.txt'
    body_html_template_name = 'emails/new_user_registration_body.html'
    body_text_template_name = 'emails/new_user_registration_body.txt'

    try:
        subject = render_to_string(subject_template_name, context).strip()
        html_content = render_to_string(body_html_template_name, context)
        try:
            text_content = render_to_string(body_text_template_name, context)
        except Exception:
            text_content = strip_tags(html_content)

        from_email = settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@example.com'

        msg = EmailMultiAlternatives(subject, text_content, from_email, [user_instance.email])
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)

        print(f"New user registration email sent successfully to {user_instance.email}")

    except Exception as e:
        print(f"Error sending new user registration email to {user_instance.email}: {e}")

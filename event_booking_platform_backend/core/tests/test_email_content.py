import pytest
from django.core import mail
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.conf import settings # Import Django settings
from mixer.backend.django import mixer
from decimal import Decimal
import datetime # Import datetime

from core.email_utils import (
    send_booking_related_email,
    send_new_user_registration_email,
    # Specific wrappers if we want to test them directly, though send_booking_related_email is the core
    send_booking_confirmation_email,
    send_booking_cancellation_email,
    send_payment_failure_email
)
from events.models import Event, Venue, Category
from bookings.models import Booking
from payments.models import Payment

User = get_user_model()

@pytest.fixture
def common_setup(db): # db fixture ensures database access for mixer
    # Using db fixture ensures database is properly set up and torn down for each test
    settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

    user = mixer.blend(User, username='testuser_content', email='customer_content@example.com', first_name='Test', last_name='UserContent')
    venue_owner = mixer.blend(User, username='venueowner_content')
    venue = mixer.blend(Venue, name='Content Test Venue', address='123 Content St', capacity=100, owner=venue_owner)
    category = mixer.blend(Category, name='Content Category')
    event = mixer.blend(
        Event,
        name='Content Test Event',
        venue=venue,
        organizer=user,
        ticket_price=Decimal('50.00'),
        currency='USD',
        start_time=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=15),
        end_time=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=15, hours=3),
        status=Event.EventStatus.UPCOMING
    )
    event.categories.add(category)

    booking = mixer.blend(
        Booking,
        event=event,
        user=user,
        number_of_tickets=2,
        price_per_ticket_at_booking=event.ticket_price,
    )
    # Manually trigger save to ensure total_price is calculated by model's save()
    booking.save()

    payment = mixer.blend(
        Payment,
        booking=booking,
        amount=booking.total_price,
        currency=event.currency, # Match event currency
        status=Payment.PaymentStatus.SUCCEEDED # Default for confirmation test
    )
    booking.payment_intent_id = payment.stripe_payment_intent_id # Simulate PI ID being set
    booking.save()

    # Refresh booking to ensure relations like 'payment' are updated if using OneToOne
    booking.refresh_from_db()

    return user, event, booking, payment


class TestEmailContents:

    @pytest.mark.django_db
    def test_new_user_registration_email_content(self, settings):
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
        user = mixer.blend(User, username='newbie_content', email='newbie_content@example.com', first_name='New', last_name='ContentUser')

        send_new_user_registration_email(user_instance=user)

        assert len(mail.outbox) == 1
        email = mail.outbox[0]

        assert email.to == [user.email]
        # Subject from template: Welcome to Our Platform, {{ user_name }}!
        assert f"Welcome to Our Platform, {user.username}!" in email.subject

        # Text body checks
        assert f"Hi {user.username}," in email.body
        assert "Thank you for registering on Our Platform!" in email.body # Adjusted to match template
        assert f"Your username is: {user.username}" in email.body
        assert f"Your registered email is: {user.email}" in email.body

        # HTML body checks
        html_body = email.alternatives[0][0]
        assert f"<h1>Welcome, {user.username}!</h1>" in html_body
        assert f"<p>Your username is: {user.username}</p>" in html_body # Check specific HTML structure
        assert f"<p>Your registered email is: {user.email}</p>" in html_body

    @pytest.mark.django_db
    def test_booking_confirmation_paid_email_content(self, common_setup):
        user, event, booking, payment = common_setup
        booking.status = Booking.BookingStatus.CONFIRMED # Ensure status is confirmed
        booking.save()
        payment.status = Payment.PaymentStatus.SUCCEEDED
        payment.stripe_payment_intent_id = "pi_test_confirm_content"
        payment.save()
        booking.refresh_from_db()


        send_booking_confirmation_email(booking) # Uses the specific wrapper

        assert len(mail.outbox) == 1
        email = mail.outbox[0]

        assert email.to == [user.email]
        # Subject from template: Booking Confirmed for {{ event_name }}!
        assert f"Booking Confirmed for {event.name}!" in email.subject

        # Text body checks
        assert f"Dear {user.username}," in email.body
        assert f"Your booking for the event \"{event.name}\" (Booking ID: {booking.id}) is confirmed." in email.body
        assert f"Transaction ID: {payment.stripe_payment_intent_id}" in email.body
        assert f"Event: {event.name}" in email.body
        assert f"Number of Tickets: {booking.number_of_tickets}" in email.body
        assert f"Total Price: {booking.total_price} {payment.currency}" in email.body
        assert f"Venue: {event.venue.name}" in email.body

        # HTML body checks
        html_body = email.alternatives[0][0]
        assert f"<p>Dear {user.username},</p>" in html_body
        assert f"<strong>{event.name}</strong>" in html_body
        assert f"Booking ID: {booking.id}" in html_body
        assert f"Transaction ID: {payment.stripe_payment_intent_id}" in html_body
        assert f"<li>Event: {event.name}</li>" in html_body
        assert f"<li>Number of Tickets: {booking.number_of_tickets}</li>" in html_body
        assert f"<li>Total Price: {booking.total_price} {payment.currency}</li>" in html_body
        assert f"<li>Venue: {event.venue.name}</li>" in html_body

    @pytest.mark.django_db
    def test_booking_pending_email_content(self, common_setup):
        user, event, booking, payment = common_setup
        booking.status = Booking.BookingStatus.PENDING_PAYMENT
        booking.save()
        payment.status = Payment.PaymentStatus.PENDING
        payment.save()
        booking.refresh_from_db()

        # Call the generic sender with specific pending templates
        send_booking_related_email(
            booking=booking,
            subject_template_name='emails/booking_pending_subject.txt',
            body_html_template_name='emails/booking_pending_body.html',
            body_text_template_name='emails/booking_pending_body.txt'
        )

        assert len(mail.outbox) == 1
        email = mail.outbox[0]
        assert email.to == [user.email]
        # Subject from template: Booking Pending for {{ event_name }}
        assert f"Booking Pending for {event.name}" in email.subject

        # Text body checks
        assert f"Dear {user.username}," in email.body
        assert f"Your booking for the event \"{event.name}\" (Booking ID: {booking.id}) is currently pending." in email.body
        assert "We are awaiting payment confirmation." in email.body
        assert f"Event: {event.name}" in email.body
        assert f"Number of Tickets: {booking.number_of_tickets}" in email.body
        assert f"Total Price: {booking.total_price} {payment.currency}" in email.body

        # HTML body checks
        html_body = email.alternatives[0][0]
        assert f"<p>Dear {user.username},</p>" in html_body
        assert f"<strong>{event.name}</strong>" in html_body
        assert f"Booking ID: {booking.id}" in html_body
        assert "awaiting payment confirmation" in html_body
        assert f"<li>Event: {event.name}</li>" in html_body
        assert f"<li>Total Price: {booking.total_price} {payment.currency}</li>" in html_body

    @pytest.mark.django_db
    def test_booking_cancelled_email_content(self, common_setup):
        user, event, booking, _ = common_setup # payment not strictly needed for cancellation content
        booking.status = Booking.BookingStatus.CANCELLED
        booking.save()

        send_booking_cancellation_email(booking)

        assert len(mail.outbox) == 1
        email = mail.outbox[0]
        assert email.to == [user.email]
        # Subject from template: Booking Cancelled for {{ event_name }}
        assert f"Booking Cancelled for {event.name}" in email.subject

        # Text body checks
        assert f"Dear {user.username}," in email.body
        assert f"Your booking for the event \"{event.name}\" (Booking ID: {booking.id}) has been cancelled." in email.body
        assert "If this was unintentional, please contact us or try booking again." in email.body
        assert f"Event: {event.name}" in email.body
        assert f"Number of Tickets: {booking.number_of_tickets}" in email.body

        # HTML body checks
        html_body = email.alternatives[0][0]
        assert f"<p>Dear {user.username},</p>" in html_body
        assert f"<strong>{event.name}</strong>" in html_body
        assert f"Booking ID: {booking.id}" in html_body
        assert "has been cancelled." in html_body
        assert f"<li>Event: {event.name}</li>" in html_body

    @pytest.mark.django_db
    def test_payment_failed_email_content(self, common_setup):
        user, event, booking, payment = common_setup
        booking.status = Booking.BookingStatus.PENDING_PAYMENT # Or FAILED, depending on desired flow post-failure
        booking.save()
        payment.status = Payment.PaymentStatus.FAILED
        payment.save()
        booking.refresh_from_db()

        send_payment_failure_email(booking)

        assert len(mail.outbox) == 1
        email = mail.outbox[0]
        assert email.to == [user.email]
        # Subject from template: Booking Failed for {{ event_name }}
        assert f"Booking Failed for {event.name}" in email.subject

        # Text body checks
        assert f"Dear {user.username}," in email.body
        assert f"your booking for the event \"{event.name}\" (Booking ID: {booking.id}) has failed." in email.body
        assert "This was due to an issue with processing your payment." in email.body
        assert f"Event: {event.name}" in email.body
        assert f"Number of Tickets: {booking.number_of_tickets}" in email.body
        assert f"Total Price: {booking.total_price} {payment.currency}" in email.body
        assert "Please try booking again or contact support if you continue to have issues." in email.body

        # HTML body checks
        html_body = email.alternatives[0][0]
        assert f"<p>Dear {user.username},</p>" in html_body
        assert f"<strong>{event.name}</strong>" in html_body
        assert f"Booking ID: {booking.id}" in html_body
        assert "issue with processing your payment" in html_body
        assert f"<li>Event: {event.name}</li>" in html_body
        assert f"<li>Total Price: {booking.total_price} {payment.currency}</li>" in html_body

    @pytest.mark.django_db
    def test_booking_confirmation_free_event_email_content(self, common_setup):
        user, event, booking, _ = common_setup

        # Modify event to be free
        event.ticket_price = Decimal('0.00')
        event.save()

        # Re-create booking for the free event
        free_booking = mixer.blend(
            Booking,
            event=event,
            user=user,
            number_of_tickets=1,
            price_per_ticket_at_booking=event.ticket_price, # Should be 0.00
            status=Booking.BookingStatus.CONFIRMED # Free bookings are auto-confirmed
        )
        free_booking.save() # Ensure total_price is calculated as 0.00

        # No payment object for free booking

        send_booking_confirmation_email(free_booking)

        assert len(mail.outbox) == 1
        email = mail.outbox[0]

        assert email.to == [user.email]
        assert f"Booking Confirmed for {event.name}!" in email.subject

        # Text body checks
        assert f"Dear {user.username}," in email.body
        assert f"Your booking for the event \"{event.name}\" (Booking ID: {free_booking.id}) is confirmed." in email.body
        # For free events, transaction ID might be absent or message different
        assert "Transaction ID" not in email.body # Assuming no transaction ID for free events
        assert f"Total Price: {free_booking.total_price} {event.currency}" in email.body # Should show 0.00 USD (or event currency)

        # HTML body checks
        html_body = email.alternatives[0][0]
        assert f"<strong>{event.name}</strong>" in html_body
        assert f"Booking ID: {free_booking.id}" in html_body
        assert "Transaction ID" not in html_body
        assert f"<li>Total Price: {free_booking.total_price} {event.currency}</li>" in html_body

```

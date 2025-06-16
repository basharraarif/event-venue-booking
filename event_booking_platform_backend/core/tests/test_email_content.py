import pytest
from django.core import mail
from django.contrib.auth import get_user_model
from django.urls import reverse # If needed for context
from django.test import override_settings

from mixer.backend.django import mixer # For creating model instances

from core.email_utils import send_booking_related_email, send_new_user_registration_email, send_payment_failure_email, send_booking_cancellation_email # Assuming this is where it is
# from core.signals import send_new_user_registration_email # Alternative if it's a signal handler
from events.models import Event, Venue, Category
from decimal import Decimal
from bookings.models import Booking
from payments.models import Payment # If needed for context in some emails
from core.models import Role # If user roles affect email content

User = get_user_model()

class TestEmailContents:

    @pytest.mark.django_db
    def test_new_user_registration_email_content(self, settings):
        # Override settings to use locmem email backend for testing
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

        user = mixer.blend(User, username='newbie', email='newbie@example.com', first_name='New', last_name='User')

        # Assuming send_new_user_registration_email is the function to call.
        # If it's a signal, this test would need to trigger user creation differently
        # or mock the signal handler call. For now, assume direct call.
        # This function might need to be imported from where it's defined (e.g., core.signals or core.views)
        # For this example, let's assume it's available as send_new_user_registration_email(user)

        # If the email is sent upon user creation via a signal (e.g., post_save on User):
        # No direct call needed here if user = mixer.blend(User, ...) triggers it.
        # For now, let's assume a direct call or that mixer.blend triggers it if it's a simple post_save signal.
        # If send_new_user_registration_email is a standalone utility:
        # The actual function in email_utils takes user_instance, not user_id
        send_new_user_registration_email(user_instance=user)

        assert len(mail.outbox) >= 1 # Use >=1 in case other signals also send mail
        email = mail.outbox[-1] # Get the last email sent

        assert email.to == [user.email]
        assert "Welcome to Event Booking Platform" in email.subject # Example subject
        assert user.username in email.body
        assert "thank you for registering" in email.body.lower()
        assert user.email in email.alternatives[0][0] # Check HTML part if it exists
        assert "welcome" in email.alternatives[0][0].lower()
        #pytest.skip("Email content test for new user registration not fully implemented.") # Remove skip

    @pytest.mark.django_db
    def test_booking_confirmation_paid_email_content(self, settings):
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

        user = mixer.blend(User, email='customer@example.com')
        venue_owner = mixer.blend(User, username='venueowner_email_content') # Unique username
        venue = mixer.blend(Venue, owner=venue_owner, capacity=100, name="Concert Hall X")
        event_organizer = mixer.blend(User, username='eventorg_email_content') # Unique username
        event = mixer.blend(Event, venue=venue, organizer=event_organizer, ticket_price=Decimal('25.00'), name="Awesome Concert", status=Event.EventStatus.UPCOMING)

        booking = mixer.blend(Booking, user=user, event=event, number_of_tickets=2, status=Booking.BookingStatus.CONFIRMED, price_per_ticket_at_booking=event.ticket_price)
        booking.total_price = booking.price_per_ticket_at_booking * booking.number_of_tickets # Manually set if not done by mixer/save
        booking.save()

        payment = mixer.blend(Payment, booking=booking, amount=booking.total_price, status=Payment.PaymentStatus.SUCCEEDED, currency="USD", stripe_payment_intent_id="pi_test_confirm_email")

        send_booking_related_email(
            booking=booking,
            # payment=payment, # Pass payment if the template uses it - check template context
            subject_template_name='emails/booking_confirmation_subject.txt',
            body_html_template_name='emails/booking_confirmation_body.html',
            body_text_template_name='emails/booking_confirmation_body.txt'
        )

        assert len(mail.outbox) == 1
        email = mail.outbox[0]

        assert email.to == [user.email]
        assert f"Booking Confirmed for {event.name}" in email.subject # Or match exact template output
        assert str(booking.id) in email.body
        assert event.name in email.body
        assert str(booking.number_of_tickets) in email.body
        assert str(booking.total_price) in email.body # Check for total price
        assert str(payment.currency) in email.body # Check for currency
        assert str(booking.event.venue.name) in email.body # Check for venue name
        if payment.stripe_payment_intent_id: # Check for transaction ID if payment exists
             assert str(payment.stripe_payment_intent_id) in email.body
        assert event.name in email.alternatives[0][0] # Check HTML part
        # pytest.skip("Email content test for paid booking confirmation not fully implemented.") # Remove skip

    @pytest.mark.django_db
    def test_booking_pending_email_content(self):
        # TODO: Setup user, event (paid), booking (pending_payment)
        # TODO: Call send_booking_related_email for booking pending
        # TODO: assert len(mail.outbox) == 1
        # TODO: email = mail.outbox[0]
        # TODO: assert "Booking Pending" in email.subject (or similar)
        # pytest.skip("Email content test for booking pending not fully implemented.") # Remove skip
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
        user = mixer.blend(User, email='customer_pending@example.com')
        event = mixer.blend(Event, name="Event Requiring Payment", ticket_price=Decimal('10.00'))
        booking = mixer.blend(Booking, user=user, event=event, status=Booking.BookingStatus.PENDING_PAYMENT, number_of_tickets=1, price_per_ticket_at_booking=event.ticket_price)
        booking.total_price = booking.price_per_ticket_at_booking * booking.number_of_tickets
        booking.save()
        # Payment object might be created by Booking model's save or view logic when status is PENDING_PAYMENT
        payment, _ = Payment.objects.get_or_create(booking=booking, defaults={'amount': booking.total_price, 'currency': 'USD', 'status': Payment.PaymentStatus.PENDING})

        send_booking_related_email(
            booking=booking,
            payment=payment,
            subject_template_name='emails/booking_pending_subject.txt',
            body_html_template_name='emails/booking_pending_body.html',
            body_text_template_name='emails/booking_pending_body.txt'
        )

        assert len(mail.outbox) == 1
        email = mail.outbox[0]
        assert email.to == [user.email]
        assert f"Your Booking for {event.name} is Pending Payment" in email.subject # Or similar
        assert str(booking.id) in email.body
        assert "requires payment" in email.body.lower()

    @pytest.mark.django_db
    def test_booking_cancelled_email_content(self, settings):
        # TODO: Setup user, event, booking (cancelled)
        # TODO: Call send_booking_related_email for booking cancelled
        # TODO: assert len(mail.outbox) == 1
        # TODO: email = mail.outbox[0]
        # TODO: assert "Booking Cancelled" in email.subject (or similar)
        # pytest.skip("Email content test for booking cancelled not fully implemented.") # Remove skip
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
        user = mixer.blend(User, email='customer_cancel@example.com')
        event = mixer.blend(Event, name="Cancelled Event Booking")
        booking = mixer.blend(Booking, user=user, event=event, status=Booking.BookingStatus.CANCELLED, number_of_tickets=2)

        send_booking_related_email( # Or use send_booking_cancellation_email(booking) if that's preferred and calls send_booking_related_email
            booking=booking,
            subject_template_name='emails/booking_cancelled_subject.txt',
            body_html_template_name='emails/booking_cancelled_body.html',
            body_text_template_name='emails/booking_cancelled_body.txt'
        )

        assert len(mail.outbox) == 1
        email = mail.outbox[0]
        assert email.to == [user.email]
        assert f"Your Booking for {event.name} has been Cancelled" in email.subject # Or similar
        assert str(booking.id) in email.body
        assert "has been cancelled" in email.body.lower()

    @pytest.mark.django_db
    def test_payment_failed_email_content(self, settings):
        # TODO: Setup user, event (paid), booking (pending_payment or failed), payment (failed)
        # TODO: Call send_booking_related_email for payment failed
        # TODO: assert len(mail.outbox) == 1
        # TODO: email = mail.outbox[0]
        # TODO: assert "Payment Failed" in email.subject (or similar)
        # pytest.skip("Email content test for payment failed not fully implemented.") # Remove skip
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
        user = mixer.blend(User, email='customer_payment_fail@example.com')
        event = mixer.blend(Event, name="Event with Failed Payment", ticket_price=Decimal('30.00'))
        booking = mixer.blend(Booking, user=user, event=event, status=Booking.BookingStatus.PENDING_PAYMENT, number_of_tickets=1, price_per_ticket_at_booking=event.ticket_price)
        booking.total_price = booking.price_per_ticket_at_booking * booking.number_of_tickets
        booking.save()
        payment = mixer.blend(Payment, booking=booking, amount=booking.total_price, status=Payment.PaymentStatus.FAILED, currency='USD')

        send_booking_related_email( # Or use send_payment_failure_email(booking)
            booking=booking,
            payment=payment,
            subject_template_name='emails/payment_failed_subject.txt',
            body_html_template_name='emails/payment_failed_body.html',
            body_text_template_name='emails/payment_failed_body.txt'
        )

        assert len(mail.outbox) == 1
        email = mail.outbox[0]
        assert email.to == [user.email]
        assert f"Payment Issue for Your Booking: {event.name}" in email.subject # Or similar
        assert str(booking.id) in email.body
        assert "payment for your booking failed" in email.body.lower()

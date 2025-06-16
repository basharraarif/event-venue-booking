import unittest
from unittest.mock import patch, MagicMock
from django.conf import settings
from django.test import TestCase, override_settings
from django.template.loader import render_to_string # Import for actual rendering

from core.email_utils import (
    send_booking_related_email,
    send_booking_cancellation_email,
    send_booking_confirmation_email,
    send_payment_failure_email,
    send_new_user_registration_email
)
from bookings.models import Booking
from events.models import Event, Venue, Category
from django.contrib.auth import get_user_model
from payments.models import Payment
from decimal import Decimal
import datetime

User = get_user_model()

# Helper function to create context, similar to what's in email_utils.py
def get_email_context(booking_instance):
    payment_currency = 'USD'
    transaction_id = None
    if hasattr(booking_instance, 'payment') and booking_instance.payment:
        payment_currency = booking_instance.payment.currency
        transaction_id = getattr(booking_instance.payment, 'stripe_payment_intent_id', None)

    return {
        'user_name': booking_instance.user.username,
        'booking_id': booking_instance.id,
        'event_name': booking_instance.event.name,
        'num_tickets': booking_instance.number_of_tickets,
        'total_price': booking_instance.total_price,
        'currency': payment_currency,
        'event_date': booking_instance.event.start_time,
        'venue_name': booking_instance.event.venue.name,
        'transaction_id': transaction_id,
    }

class EmailUtilsTests(TestCase):

    def setUp(self):
        # No need to configure settings here if project settings are loaded by test runner
        self.user = User.objects.create_user(username='testuser_email', email='test@example.com', password='password')
        self.venue_owner = User.objects.create_user(username='venueowner_email', email='vo@example.com', password='password')
        self.venue = Venue.objects.create(name='Email Test Venue', address='123 Email St', capacity=100, owner=self.venue_owner)
        self.event = Event.objects.create(
            name='Email Test Event',
            venue=self.venue,
            organizer=self.user, # Or venue_owner if that makes more sense for some tests
            ticket_price=Decimal('25.00'),
            currency='EUR', # Test with a different currency
            start_time=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=10),
            end_time=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=10, hours=2),
        )
        self.booking = Booking.objects.create(
            event=self.event,
            user=self.user,
            number_of_tickets=2
            # price_per_ticket_at_booking and total_price are set by model's save()
        )
        # Payment for booking related emails
        self.payment = Payment.objects.create(
            booking=self.booking,
            amount=self.booking.total_price,
            currency=self.event.currency, # Use event's currency
            status=Payment.PaymentStatus.SUCCEEDED, # Default for confirmation
            stripe_payment_intent_id='pi_email_test_123'
        )
        self.booking.refresh_from_db() # To link payment if OneToOneField is used

    @patch('core.email_utils.EmailMultiAlternatives')
    def test_send_booking_confirmation_email_content(self, mock_email_multi_alternatives_constructor):
        mock_msg_instance = MagicMock()
        mock_email_multi_alternatives_constructor.return_value = mock_msg_instance

        # Call the specific wrapper function
        send_booking_confirmation_email(self.booking)

        # Verify EmailMultiAlternatives was called (once by the wrapper)
        mock_email_multi_alternatives_constructor.assert_called_once()

        # Get the arguments passed to EmailMultiAlternatives constructor
        call_args = mock_email_multi_alternatives_constructor.call_args[0]
        subject = call_args[0]
        text_body = call_args[1]
        from_email_arg = call_args[2]
        to_email_list = call_args[3]

        # Get the HTML alternative (assuming it's the first one attached)
        html_body = ""
        if mock_msg_instance.attach_alternative.called:
            html_body = mock_msg_instance.attach_alternative.call_args[0][0]

        # Assertions for from and to emails
        self.assertEqual(from_email_arg, settings.DEFAULT_FROM_EMAIL)
        self.assertEqual(to_email_list, [self.user.email])

        # Expected context values
        self.assertIn(f"Booking Confirmation for {self.event.name}", subject) # Example subject check

        # Text body checks
        self.assertIn(f"Dear {self.user.username}", text_body)
        self.assertIn(f"Your booking for {self.event.name} is confirmed.", text_body)
        self.assertIn(f"Booking ID: {self.booking.id}", text_body)
        self.assertIn(f"Event: {self.event.name}", text_body)
        self.assertIn(f"Number of tickets: {self.booking.number_of_tickets}", text_body)
        self.assertIn(f"Total Price: {self.booking.total_price} {self.payment.currency}", text_body)
        self.assertIn(f"Venue: {self.venue.name}", text_body)
        if self.payment.stripe_payment_intent_id:
            self.assertIn(f"Transaction ID: {self.payment.stripe_payment_intent_id}", text_body)

        # HTML body checks (similar to text, but can also check for HTML tags if needed)
        self.assertIn(f"<h1>Booking Confirmed!</h1>", html_body) # Example HTML check
        self.assertIn(f"Hi {self.user.username}", html_body)
        self.assertIn(f"event_name\">{self.event.name}<", html_body) # Example of checking value within a span/td
        self.assertIn(f"{self.booking.id}", html_body)
        self.assertIn(f"{self.booking.number_of_tickets}", html_body)
        self.assertIn(f"{self.booking.total_price} {self.payment.currency}", html_body)

        mock_msg_instance.send.assert_called_once_with(fail_silently=False)

    @patch('core.email_utils.EmailMultiAlternatives')
    def test_send_booking_pending_email_content(self, mock_email_multi_alternatives_constructor):
        mock_msg_instance = MagicMock()
        mock_email_multi_alternatives_constructor.return_value = mock_msg_instance

        self.booking.status = Booking.BookingStatus.PENDING_PAYMENT
        self.booking.save()
        if hasattr(self.booking, 'payment'):
            self.payment.status = Payment.PaymentStatus.PENDING
            self.payment.save()
            self.booking.refresh_from_db()


        # Directly use send_booking_related_email as it's called by views for pending status
        send_booking_related_email(
            booking=self.booking,
            subject_template_name='emails/booking_pending_subject.txt',
            body_html_template_name='emails/booking_pending_body.html',
            body_text_template_name='emails/booking_pending_body.txt'
        )

        mock_email_multi_alternatives_constructor.assert_called_once()
        call_args = mock_email_multi_alternatives_constructor.call_args[0]
        subject, text_body, _, to_list = call_args[:4]
        html_body = mock_msg_instance.attach_alternative.call_args[0][0] if mock_msg_instance.attach_alternative.called else ""

        self.assertEqual(to_list, [self.user.email])
        self.assertIn("Your Booking is Pending Payment", subject)
        self.assertIn(f"Dear {self.user.username}", text_body)
        self.assertIn(f"Your booking for {self.event.name} is currently pending payment.", text_body)
        self.assertIn(f"Booking ID: {self.booking.id}", text_body)
        self.assertIn(f"Please complete your payment to confirm your spot.", text_body)
        self.assertIn(f"Total Amount Due: {self.booking.total_price} {self.payment.currency}", text_body)

        self.assertIn("Booking Pending Payment", html_body)
        self.assertIn(f"complete your payment for booking ID {self.booking.id}", html_body)
        mock_msg_instance.send.assert_called_once()


    @patch('core.email_utils.EmailMultiAlternatives')
    def test_send_payment_failure_email_content(self, mock_email_multi_alternatives_constructor):
        mock_msg_instance = MagicMock()
        mock_email_multi_alternatives_constructor.return_value = mock_msg_instance

        self.booking.status = Booking.BookingStatus.PENDING_PAYMENT # Or FAILED if that's the flow
        self.booking.save()
        if hasattr(self.booking, 'payment'):
            self.payment.status = Payment.PaymentStatus.FAILED
            self.payment.save()
            self.booking.refresh_from_db()

        send_payment_failure_email(self.booking)

        mock_email_multi_alternatives_constructor.assert_called_once()
        call_args = mock_email_multi_alternatives_constructor.call_args[0]
        subject, text_body, _, to_list = call_args[:4]
        html_body = mock_msg_instance.attach_alternative.call_args[0][0] if mock_msg_instance.attach_alternative.called else ""

        self.assertEqual(to_list, [self.user.email])
        self.assertIn("Payment Failed for Your Booking", subject)
        self.assertIn(f"Dear {self.user.username}", text_body)
        self.assertIn(f"We regret to inform you that the payment for your booking (ID: {self.booking.id}) for the event {self.event.name} has failed.", text_body)
        self.assertIn(f"Event: {self.event.name}", text_body)
        self.assertIn(f"Amount: {self.booking.total_price} {self.payment.currency}", text_body)
        self.assertIn("Please try updating your payment method or contact support.", text_body)

        self.assertIn("Payment Failed", html_body)
        self.assertIn(f"booking ID: {self.booking.id}", html_body)
        mock_msg_instance.send.assert_called_once()

    @patch('core.email_utils.EmailMultiAlternatives')
    def test_send_booking_cancellation_email_content(self, mock_email_multi_alternatives_constructor):
        mock_msg_instance = MagicMock()
        mock_email_multi_alternatives_constructor.return_value = mock_msg_instance

        self.booking.status = Booking.BookingStatus.CANCELLED
        self.booking.save()

        send_booking_cancellation_email(self.booking)

        mock_email_multi_alternatives_constructor.assert_called_once()
        call_args = mock_email_multi_alternatives_constructor.call_args[0]
        subject, text_body, _, to_list = call_args[:4]
        html_body = mock_msg_instance.attach_alternative.call_args[0][0] if mock_msg_instance.attach_alternative.called else ""

        self.assertEqual(to_list, [self.user.email])
        self.assertIn("Your Booking Has Been Cancelled", subject)
        self.assertIn(f"Dear {self.user.username}", text_body)
        self.assertIn(f"your booking (ID: {self.booking.id}) for the event {self.event.name} has been cancelled.", text_body)
        self.assertIn(f"Event: {self.event.name}", text_body)

        self.assertIn("Booking Cancelled", html_body)
        self.assertIn(f"ID: {self.booking.id}", html_body)
        mock_msg_instance.send.assert_called_once()

    @patch('core.email_utils.EmailMultiAlternatives')
    def test_send_new_user_registration_email_content(self, mock_email_multi_alternatives_constructor):
        mock_msg_instance = MagicMock()
        mock_email_multi_alternatives_constructor.return_value = mock_msg_instance

        new_user = User.objects.create_user(username='newlyreg', email='newlyreg@example.com', password='password')
        send_new_user_registration_email(new_user)

        mock_email_multi_alternatives_constructor.assert_called_once()
        call_args = mock_email_multi_alternatives_constructor.call_args[0]
        subject, text_body, from_email_arg, to_list = call_args[:4]
        html_body = mock_msg_instance.attach_alternative.call_args[0][0] if mock_msg_instance.attach_alternative.called else ""

        self.assertEqual(from_email_arg, settings.DEFAULT_FROM_EMAIL)
        self.assertEqual(to_list, [new_user.email])

        self.assertIn(f"Welcome to Our Platform, {new_user.username}!", subject)

        self.assertIn(f"Hi {new_user.username},", text_body)
        self.assertIn("Welcome to EventFlow!", text_body) # Assuming 'EventFlow' is the platform name from template
        self.assertIn("We're excited to have you.", text_body)
        self.assertIn(f"Your email: {new_user.email}", text_body)

        self.assertIn(f"<h1>Welcome, {new_user.username}!</h1>", html_body)
        self.assertIn("platform_name\">EventFlow<", html_body) # Example of checking value within a span/td
        self.assertIn(f"{new_user.email}", html_body)

        mock_msg_instance.send.assert_called_once_with(fail_silently=False)


    @patch('core.email_utils.EmailMultiAlternatives')
    def test_send_booking_related_email_no_user_email(self, mock_email_multi_alternatives):
        # Test that email is not sent if user has no email address
        original_email = self.user.email
        self.user.email = ''
        self.user.save()
        self.booking.refresh_from_db()

        send_booking_confirmation_email(self.booking) # Try sending any booking email
        mock_email_multi_alternatives.assert_not_called()

        self.user.email = original_email # Restore email
        self.user.save()

    @patch('core.email_utils.EmailMultiAlternatives')
    def test_send_new_user_registration_email_no_user_email(self, mock_email_multi_alternatives):
        # Test that email is not sent if user has no email address
        no_email_user = User.objects.create_user(username='no_email_user', email='', password='password')

        send_new_user_registration_email(no_email_user)
        mock_email_multi_alternatives.assert_not_called()


    @patch('core.email_utils.EmailMultiAlternatives')
    @patch('core.email_utils.render_to_string', side_effect=Exception("Template rendering failed globally"))
    def test_send_email_handles_global_render_exception(self, mock_render_to_string_global_fail, mock_email_multi_alternatives):
        # Test handling of generic render_to_string exception
        send_booking_confirmation_email(self.booking) # Any email type
        mock_email_multi_alternatives.assert_not_called() # Should not attempt to send if rendering fails


    @patch('core.email_utils.EmailMultiAlternatives')
    def test_text_body_fallback_if_text_template_fails_in_send_booking_related_email(self, mock_email_multi_alternatives_constructor):
        # This test focuses on the fallback logic within send_booking_related_email
        mock_msg_instance = MagicMock()
        mock_email_multi_alternatives_constructor.return_value = mock_msg_instance

        # Actual subject and HTML content will be rendered by templates.
        # We need to make the text template rendering fail.

        # Use a new booking or modify existing for this specific test to avoid side effects
        test_fallback_booking = Booking.objects.create(
            event=self.event, user=self.user, number_of_tickets=1
        )
        if not hasattr(test_fallback_booking, 'payment') or not test_fallback_booking.payment:
             Payment.objects.create(
                booking=test_fallback_booking, amount=test_fallback_booking.total_price,
                currency=test_fallback_booking.event.currency, status='succeeded'
            )
        test_fallback_booking.refresh_from_db()


        # We need to mock render_to_string carefully for this specific test
        original_render_to_string = render_to_string

        def selective_render_side_effect(template_name, context):
            if template_name == 'emails/problematic_text_template.txt': # This is the one we want to fail
                raise Exception("Simulated text template rendering error")
            # For other templates, use the actual render_to_string
            return original_render_to_string(template_name, context)

        with patch('core.email_utils.render_to_string', side_effect=selective_render_side_effect) as mock_render_selective:
            send_booking_related_email(
                booking=test_fallback_booking,
                subject_template_name='emails/booking_confirmation_subject.txt', # A real subject template
                body_html_template_name='emails/booking_confirmation_body.html',   # A real HTML template
                body_text_template_name='emails/problematic_text_template.txt' # The failing one
            )

            mock_email_multi_alternatives_constructor.assert_called_once()
            call_args = mock_email_multi_alternatives_constructor.call_args[0]
            text_body_used_for_email = call_args[1] # This is the text body that EmailMultiAlternatives received

            # Expected: text_body_used_for_email should be the strip_tags version of the HTML content
            # We need to render the HTML content separately to compare
            expected_html_content = original_render_to_string('emails/booking_confirmation_body.html', get_email_context(test_fallback_booking))
            from django.utils.html import strip_tags
            expected_stripped_text = strip_tags(expected_html_content)

            self.assertEqual(text_body_used_for_email, expected_stripped_text)
            mock_msg_instance.attach_alternative.assert_called_once_with(expected_html_content, "text/html")
            mock_msg_instance.send.assert_called_once()
```

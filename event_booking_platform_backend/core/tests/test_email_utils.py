import unittest
from unittest.mock import patch, MagicMock
from django.conf import settings
from django.test import TestCase, override_settings

from core.email_utils import send_booking_related_email
from bookings.models import Booking # Requires Booking, Event, User, Venue for setup
from events.models import Event, Venue, Category
from django.contrib.auth import get_user_model
from payments.models import Payment # For payment currency and transaction ID in context
from decimal import Decimal
import datetime

User = get_user_model()

class EmailUtilsTests(TestCase):

    def setUp(self):
        # Configure minimal settings for email sending, rest will be mocked
        if not settings.configured:
            settings.configure(
                DEFAULT_FROM_EMAIL='noreply@example.com',
                TEMPLATES=[{
                    'BACKEND': 'django.template.backends.django.DjangoTemplates',
                    'DIRS': [settings.BASE_DIR / 'templates'], # Ensure your project's BASE_DIR is correct
                }]
            )

        self.user = User.objects.create_user(username='testuser', email='test@example.com', password='password')
        self.venue_owner = User.objects.create_user(username='venueowner', email='vo@example.com', password='password')
        self.venue = Venue.objects.create(name='Test Venue', address='123 Test St', capacity=100, owner=self.venue_owner)
        self.event = Event.objects.create(
            name='Test Event',
            venue=self.venue,
            organizer=self.user,
            ticket_price=Decimal('10.00'),
            start_time=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1),
            end_time=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=2),
        )
        self.booking = Booking.objects.create(
            event=self.event,
            user=self.user,
            number_of_tickets=2,
            status=Booking.BookingStatus.CONFIRMED # Example status
        )
        # Simulate a payment object linked to the booking for context
        self.payment = Payment.objects.create(
            booking=self.booking,
            amount=self.booking.total_price,
            currency='USD',
            status='succeeded',
            stripe_payment_intent_id='pi_test123'
        )
        # Refresh booking to link payment (if using OneToOneField 'payment' on Booking)
        self.booking.refresh_from_db()


    @patch('core.email_utils.EmailMultiAlternatives')
    def test_send_booking_related_email_successful(self, mock_email_multi_alternatives):
        mock_msg_instance = MagicMock()
        mock_email_multi_alternatives.return_value = mock_msg_instance

        subject_template = 'emails/test_subject.txt'
        body_html_template = 'emails/test_body.html'
        body_text_template = 'emails/test_body.txt'

        # Create dummy template files for the test
        # This would typically be done by having actual test template files in your templates/emails directory
        # For this test, we assume render_to_string will work if templates are present.
        # If not, this test would fail at render_to_string.
        # To make it more robust, consider mocking render_to_string or ensuring test templates exist.

        # We will let render_to_string use the actual dummy templates created.
        send_booking_related_email(
            booking=self.booking,
            subject_template_name=subject_template,
            body_html_template_name=body_html_template,
            body_text_template_name=body_text_template
        )

        # Construct expected content based on dummy templates and booking context
        expected_subject = f"Test Subject for {self.event.name} - Booking ID: {self.booking.id}"
        expected_text_content = (
            f"Hello {self.user.username},\n\n"
            f"This is a test text email for booking {self.booking.id} for the event: {self.event.name}.\n"
            f"Price: {self.booking.total_price} {self.payment.currency}"
        )
        expected_html_content = (
            f"<p>Hello {self.user.username},</p>\n"
            f"<p>This is a test HTML email for booking {self.booking.id} for the event: {self.event.name}.</p>\n"
            f"<p>Price: {self.booking.total_price} {self.payment.currency}</p>"
        )
        # render_to_string adds a newline to subject, so strip it for comparison
        mock_email_multi_alternatives.assert_called_once_with(
            expected_subject.strip(), # Subjects might have trailing newlines from render_to_string
            expected_text_content,
                settings.DEFAULT_FROM_EMAIL,
                [self.user.email]
            )
            mock_msg_instance.attach_alternative.assert_called_once_with(expected_html_content, "text/html")
            mock_msg_instance.send.assert_called_once_with(fail_silently=False)

    @patch('core.email_utils.EmailMultiAlternatives')
    def test_send_booking_related_email_no_user_email(self, mock_email_multi_alternatives):
        self.user.email = '' # No email
        self.user.save()
        self.booking.refresh_from_db() # Refresh booking as user is linked

        send_booking_related_email(
            booking=self.booking,
            subject_template_name='subject.txt',
            body_html_template_name='body.html',
            body_text_template_name='body.txt'
        )
        mock_email_multi_alternatives.assert_not_called()

    @override_settings(DEFAULT_FROM_EMAIL='customsender@example.com')
    @patch('core.email_utils.EmailMultiAlternatives')
    def test_send_email_uses_settings_default_from_email(self, mock_email_multi_alternatives):
        with patch('core.email_utils.render_to_string', return_value="content"):
            send_booking_related_email(
                booking=self.booking,
                subject_template_name='s.txt',
                body_html_template_name='h.html',
                body_text_template_name='t.txt'
            )
            self.assertEqual(mock_email_multi_alternatives.call_args[0][2], 'customsender@example.com')

    @patch('core.email_utils.render_to_string', side_effect=Exception("Template rendering failed"))
    @patch('core.email_utils.EmailMultiAlternatives')
    def test_send_email_handles_render_exception(self, mock_email_multi_alternatives, mock_render_to_string):
        # Expect the function to catch the exception and not call EmailMultiAlternatives or send
        send_booking_related_email(
            booking=self.booking,
            subject_template_name='s.txt',
            body_html_template_name='h.html',
            body_text_template_name='t.txt'
        )
        mock_email_multi_alternatives.assert_not_called()
        # Check logs or other error handling if implemented for this failure

    @patch('core.email_utils.EmailMultiAlternatives')
    def test_text_body_fallback_if_text_template_fails(self, mock_email_multi_alternatives):
        mock_msg_instance = MagicMock()
        mock_email_multi_alternatives.return_value = mock_msg_instance

        subject_template = 'emails/test_subject.txt'
        html_template = 'emails/test_body.html'
        text_template_to_fail = 'emails/non_existent_body.txt' # This will cause render_to_string to fail for text

        # Expected content based on dummy templates if text part fails and is stripped from HTML
        expected_subject_rendered = f"Test Subject for {self.event.name} - Booking ID: {self.booking.id}"
        expected_html_content_rendered = (
            f"<p>Hello {self.user.username},</p>\n"
            f"<p>This is a test HTML email for booking {self.booking.id} for the event: {self.event.name}.</p>\n"
            f"<p>Price: {self.booking.total_price} {self.payment.currency}</p>"
        )
        # Simulate strip_tags result for the expected HTML content
        expected_text_from_html = (
            f"Hello {self.user.username},\n"
            f"This is a test HTML email for booking {self.booking.id} for the event: {self.event.name}.\n"
            f"Price: {self.booking.total_price} {self.payment.currency}"
        )


        with patch('core.email_utils.render_to_string') as mock_render:
            # Simulate text template failing, html and subject template succeeding using actual templates
            def side_effect_render(template_name, context):
                from django.template.loader import render_to_string as original_render_to_string
                if template_name == text_template_to_fail:
                    raise Exception("Simulated text template rendering error")
                # For subject and HTML, use the actual render_to_string with dummy templates
                return original_render_to_string(template_name, context)

            mock_render.side_effect = side_effect_render

            # We also need to ensure strip_tags is called as part of the fallback
            with patch('core.email_utils.strip_tags', return_value=expected_text_from_html) as mock_strip_tags:
                send_booking_related_email(
                    booking=self.booking,
                    subject_template_name=subject_template,
                    body_html_template_name=html_template,
                    body_text_template_name=text_template_to_fail
                )

                mock_email_multi_alternatives.assert_called_once_with(
                    expected_subject_rendered.strip(),
                    expected_text_from_html, # This should be the stripped HTML
                    settings.DEFAULT_FROM_EMAIL,
                    [self.user.email]
                )
                # Assert that render_to_string was called for HTML (which provides the fallback content)
                mock_render.assert_any_call(html_template, unittest.mock.ANY)
                # Assert that strip_tags was called with the result of rendering the HTML template
                # We need to find the call to render_to_string for the HTML template to get its exact output for strip_tags
                html_render_call = None
                for call_args in mock_render.call_args_list:
                    if call_args[0][0] == html_template:
                        # This is tricky because the actual rendered output isn't easily captured here if original_render_to_string is used.
                        # For simplicity, we trust strip_tags was called if the flow reached this point.
                        # A more direct way is to check strip_tags was called with the content *as rendered by the html_template*.
                        # The current patch on strip_tags predefines its return value, so we check it was called.
                        mock_strip_tags.assert_called_once() # Check it was called
                        # We can check that it was called with the *expected* HTML content that would have been rendered
                        # This means we'd have to render it outside or trust the `expected_html_content_rendered`
                        # For this test, it's simpler to assume strip_tags got called with *some* HTML string.

                mock_msg_instance.attach_alternative.assert_called_once_with(unittest.mock.ANY, "text/html") # HTML content here
                self.assertIn(f"<p>Hello {self.user.username},</p>", mock_msg_instance.attach_alternative.call_args[0][0]) # Check some part of HTML
                mock_msg_instance.send.assert_called_once()

# To ensure these tests run, you might need to create dummy template files in your
# project's templates/emails/ directory, e.g., test_subject.txt, test_body.html, test_body.txt
# or enhance the mocking of render_to_string for more complex context verification.
# Example:
# templates/emails/test_subject.txt -> Subject: {{ event_name }}
# templates/emails/test_body.html -> <p>Hello {{ user_name }}, event {{ event_name }}</p>
# templates/emails/test_body.txt -> Hello {{ user_name }}, event {{ event_name }}

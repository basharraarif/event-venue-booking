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

        # For simplicity, let's assume render_to_string works or mock it if it causes issues in test env
        with patch('core.email_utils.render_to_string') as mock_render_to_string:
            mock_render_to_string.side_effect = lambda template_name, context: f"Rendered {template_name} with {context.get('event_name', '')}"

            send_booking_related_email(
                booking=self.booking,
                subject_template_name=subject_template,
                body_html_template_name=body_html_template,
                body_text_template_name=body_text_template
            )

            mock_render_to_string.assert_any_call(subject_template, unittest.mock.ANY)
            mock_render_to_string.assert_any_call(body_html_template, unittest.mock.ANY)
            mock_render_to_string.assert_any_call(body_text_template, unittest.mock.ANY)

            expected_subject = f"Rendered {subject_template} with {self.event.name}"
            expected_text_content = f"Rendered {body_text_template} with {self.event.name}"
            expected_html_content = f"Rendered {body_html_template} with {self.event.name}"

            mock_email_multi_alternatives.assert_called_once_with(
                expected_subject,
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

        with patch('core.email_utils.render_to_string') as mock_render:
            # Simulate text template failing, html template succeeding
            def side_effect_render(template_name, context):
                if template_name == 'emails/test_body.txt':
                    raise Exception("Text template error")
                elif template_name == 'emails/test_body.html':
                    return "<p>HTML Content for Event Test Event</p>" # Include event name for context check
                elif template_name == 'emails/test_subject.txt':
                    return "Subject for Event Test Event"
                return "default content"

            mock_render.side_effect = side_effect_render

            with patch('core.email_utils.strip_tags') as mock_strip_tags:
                mock_strip_tags.return_value = "HTML Content for Event Test Event" # Expected text after stripping

                send_booking_related_email(
                    booking=self.booking,
                    subject_template_name='emails/test_subject.txt',
                    body_html_template_name='emails/test_body.html',
                    body_text_template_name='emails/test_body.txt'
                )

                expected_subject = "Subject for Event Test Event"
                # Text content should be the stripped HTML
                expected_text_content = "HTML Content for Event Test Event"
                expected_html_content = "<p>HTML Content for Event Test Event</p>"

                mock_email_multi_alternatives.assert_called_once_with(
                    expected_subject,
                    expected_text_content, # This should be the stripped HTML
                    settings.DEFAULT_FROM_EMAIL,
                    [self.user.email]
                )
                mock_strip_tags.assert_called_once_with(expected_html_content)
                mock_msg_instance.attach_alternative.assert_called_once_with(expected_html_content, "text/html")
                mock_msg_instance.send.assert_called_once()

# To ensure these tests run, you might need to create dummy template files in your
# project's templates/emails/ directory, e.g., test_subject.txt, test_body.html, test_body.txt
# or enhance the mocking of render_to_string for more complex context verification.
# Example:
# templates/emails/test_subject.txt -> Subject: {{ event_name }}
# templates/emails/test_body.html -> <p>Hello {{ user_name }}, event {{ event_name }}</p>
# templates/emails/test_body.txt -> Hello {{ user_name }}, event {{ event_name }}

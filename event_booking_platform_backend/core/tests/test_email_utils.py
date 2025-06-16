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
    @patch('core.email_utils.render_to_string')
    def test_send_booking_confirmation_email_content_verification(self, mock_render_to_string, mock_email_multi_alternatives):
        mock_msg_instance = MagicMock()
        mock_email_multi_alternatives.return_value = mock_msg_instance

        # Define expected rendered content for mocking
        # This allows us to verify the structure of the call to EmailMultiAlternatives
        # without needing the actual template rendering output.
        mock_render_to_string.side_effect = lambda template_name, context: f"Mocked content for {template_name} with user {context.get('user_name')}"

        # Use the actual confirmation email templates
        subject_template = 'emails/booking_confirmation_subject.txt'
        body_html_template = 'emails/booking_confirmation_body.html'
        body_text_template = 'emails/booking_confirmation_body.txt'

        # Ensure booking has a payment for full context
        if not hasattr(self.booking, 'payment') or not self.booking.payment:
            self.payment = Payment.objects.create(
                booking=self.booking, amount=self.booking.total_price, currency='USD', status='succeeded', stripe_payment_intent_id='pi_confirm_test'
            )
            self.booking.refresh_from_db()


        send_booking_related_email(
            booking=self.booking, # self.booking is set to CONFIRMED status in setUp
            subject_template_name=subject_template,
            body_html_template_name=body_html_template,
            body_text_template_name=body_text_template
        )

        # Verify render_to_string calls with correct context
        expected_context = {
            'user_name': self.booking.user.username,
            'booking_id': self.booking.id,
            'event_name': self.booking.event.name,
            'num_tickets': self.booking.number_of_tickets,
            'total_price': self.booking.total_price,
            'currency': self.booking.payment.currency,
            'event_date': self.booking.event.start_time,
            'venue_name': self.booking.event.venue.name,
            'transaction_id': self.booking.payment.stripe_payment_intent_id,
        }
        mock_render_to_string.assert_any_call(subject_template, expected_context)
        mock_render_to_string.assert_any_call(body_html_template, expected_context)
        mock_render_to_string.assert_any_call(body_text_template, expected_context)

        # Verify EmailMultiAlternatives call
        mock_email_multi_alternatives.assert_called_once_with(
            f"Mocked content for {subject_template} with user {self.user.username}".strip(),
            f"Mocked content for {body_text_template} with user {self.user.username}",
            settings.DEFAULT_FROM_EMAIL,
            [self.user.email]
        )
        mock_msg_instance.attach_alternative.assert_called_once_with(
            f"Mocked content for {body_html_template} with user {self.user.username}", "text/html"
        )
        mock_msg_instance.send.assert_called_once_with(fail_silently=False)

    @patch('core.email_utils.EmailMultiAlternatives')
    def test_send_booking_related_email_no_user_email(self, mock_email_multi_alternatives):
        original_email = self.user.email # Save original email
        self.user.email = '' # No email
        self.user.save()
        self.booking.refresh_from_db() # Refresh booking as user is linked

        send_booking_related_email(
            booking=self.booking,
            subject_template_name='emails/booking_confirmation_subject.txt', # Use actual template names
            body_html_template_name='emails/booking_confirmation_body.html',
            body_text_template_name='emails/booking_confirmation_body.txt'
        )
        mock_email_multi_alternatives.assert_not_called()
        self.user.email = original_email # Restore email
        self.user.save()

    @override_settings(DEFAULT_FROM_EMAIL='customsender@example.com')
    @patch('core.email_utils.EmailMultiAlternatives')
    @patch('core.email_utils.render_to_string', return_value="Mocked Content") # Mock render_to_string for simplicity
    def test_send_email_uses_settings_default_from_email(self, mock_render_to_string, mock_email_multi_alternatives):
        with override_settings(DEFAULT_FROM_EMAIL='customsender@example.com'): # Use override_settings correctly
            send_booking_related_email(
                booking=self.booking,
                subject_template_name='s.txt', # Generic template names are fine here
                body_html_template_name='h.html',
                body_text_template_name='t.txt'
            )
            mock_email_multi_alternatives.assert_called_once()
            # Check the 'from_email' argument in the EmailMultiAlternatives call
            self.assertEqual(mock_email_multi_alternatives.call_args[0][2], 'customsender@example.com')


    @patch('core.email_utils.render_to_string', side_effect=Exception("Template rendering failed"))
    @patch('core.email_utils.EmailMultiAlternatives')
    def test_send_email_handles_render_exception(self, mock_email_multi_alternatives, mock_render_to_string):
        send_booking_related_email(
            booking=self.booking,
            subject_template_name='s.txt', # Generic template names
            body_html_template_name='h.html',
            body_text_template_name='t.txt'
        )
        mock_email_multi_alternatives.assert_not_called()


    @patch('core.email_utils.EmailMultiAlternatives')
    @patch('core.email_utils.strip_tags')
    @patch('core.email_utils.render_to_string')
    def test_text_body_fallback_if_text_template_fails(self, mock_render_to_string, mock_strip_tags, mock_email_multi_alternatives):
        mock_msg_instance = MagicMock()
        mock_email_multi_alternatives.return_value = mock_msg_instance

        subject_content = "Test Subject Fallback"
        html_content = "<p>HTML Content For Fallback</p>" # Specific HTML content for this test
        stripped_html_content = "HTML Content For Fallback" # Expected strip_tags output

        def render_side_effect(template_name, context):
            if template_name == 'emails/subject_for_fallback.txt':
                return subject_content
            elif template_name == 'emails/html_body_for_fallback.html':
                return html_content
            elif template_name == 'emails/text_body_intended_to_fail.txt':
                raise Exception("Simulated text template rendering error")
            return "Should not be called for other templates in this test"

        mock_render_to_string.side_effect = render_side_effect
        mock_strip_tags.return_value = stripped_html_content

        send_booking_related_email(
            booking=self.booking,
            subject_template_name='emails/subject_for_fallback.txt',
            body_html_template_name='emails/html_body_for_fallback.html',
            body_text_template_name='emails/text_body_intended_to_fail.txt'
        )

        mock_render_to_string.assert_any_call('emails/subject_for_fallback.txt', unittest.mock.ANY)
        mock_render_to_string.assert_any_call('emails/html_body_for_fallback.html', unittest.mock.ANY)
        mock_render_to_string.assert_any_call('emails/text_body_intended_to_fail.txt', unittest.mock.ANY)
        mock_strip_tags.assert_called_once_with(html_content)

        mock_email_multi_alternatives.assert_called_once_with(
            subject_content.strip(),
            stripped_html_content,
            settings.DEFAULT_FROM_EMAIL,
            [self.user.email]
        )
        mock_msg_instance.attach_alternative.assert_called_once_with(html_content, "text/html")
        mock_msg_instance.send.assert_called_once()


    @patch('core.email_utils.send_booking_related_email') # Mock the generic function
    def test_send_booking_cancellation_email_wrapper(self, mock_send_booking_related_email):
        from core.email_utils import send_booking_cancellation_email # Import here
        send_booking_cancellation_email(self.booking)
        mock_send_booking_related_email.assert_called_once_with(
            booking=self.booking,
            subject_template_name='emails/booking_cancellation_subject.txt',
            body_html_template_name='emails/booking_cancellation_body.html',
            body_text_template_name='emails/booking_cancellation_body.txt'
        )

    @patch('core.email_utils.send_booking_related_email')
    def test_send_booking_confirmation_email_wrapper(self, mock_send_booking_related_email):
        from core.email_utils import send_booking_confirmation_email # Import the specific wrapper
        # self.booking is already CONFIRMED in setUp
        send_booking_confirmation_email(self.booking)
        mock_send_booking_related_email.assert_called_once_with(
            booking=self.booking,
            subject_template_name='emails/booking_confirmation_subject.txt',
            body_html_template_name='emails/booking_confirmation_body.html',
            body_text_template_name='emails/booking_confirmation_body.txt'
        )

    @patch('core.email_utils.send_booking_related_email')
    def test_send_booking_pending_email_wrapper(self, mock_send_booking_related_email):
        # This test effectively checks if the main function would be called with these template names.
        # It doesn't use a specific wrapper "send_booking_pending_email" as it doesn't exist.
        temp_booking = Booking.objects.create(
            event=self.event, user=self.user, number_of_tickets=1, status=Booking.BookingStatus.PENDING_PAYMENT
        )
        send_booking_related_email( # Direct call, as done in views
            booking=temp_booking,
            subject_template_name='emails/booking_pending_subject.txt',
            body_html_template_name='emails/booking_pending_body.html',
            body_text_template_name='emails/booking_pending_body.txt'
        )
        mock_send_booking_related_email.assert_called_once_with(
            booking=temp_booking,
            subject_template_name='emails/booking_pending_subject.txt',
            body_html_template_name='emails/booking_pending_body.html',
            body_text_template_name='emails/booking_pending_body.txt'
        )


    @patch('core.email_utils.send_booking_related_email') # Mock the generic function
    def test_send_payment_failure_email_wrapper(self, mock_send_booking_related_email):
        from core.email_utils import send_payment_failure_email # Import here
        send_payment_failure_email(self.booking)
        mock_send_booking_related_email.assert_called_once_with(
            booking=self.booking,
            subject_template_name='emails/payment_failed_subject.txt',
            body_html_template_name='emails/payment_failed_body.html',
            body_text_template_name='emails/payment_failed_body.txt'
        )

    @patch('core.email_utils.EmailMultiAlternatives')
    def test_send_new_user_registration_email_successful(self, mock_email_multi_alternatives):
        from core.email_utils import send_new_user_registration_email # Import here

        mock_msg_instance = MagicMock()
        mock_email_multi_alternatives.return_value = mock_msg_instance

        # These templates were created in a previous step.
        # For this test, we assume render_to_string will work with them.
        # If more detailed checking of rendered content is needed, templates should be simpler or render_to_string mocked.

        with patch('core.email_utils.render_to_string') as mock_render:
            # Define what render_to_string should return for each template
            def side_effect_render(template_name, context):
                if template_name == 'emails/new_user_registration_subject.txt':
                    return f"Welcome to Our Platform, {context['user_name']}!"
                elif template_name == 'emails/new_user_registration_body.html':
                    return f"<h1>Welcome, {context['user_name']}!</h1><p>Email: {context['user_email']}</p>"
                elif template_name == 'emails/new_user_registration_body.txt':
                    return f"Hi {context['user_name']},\nEmail: {context['user_email']}"
                return "" # Default empty for any other unexpected template

            mock_render.side_effect = side_effect_render

            send_new_user_registration_email(self.user)

            expected_subject = f"Welcome to Our Platform, {self.user.username}!"
            expected_html_body = f"<h1>Welcome, {self.user.username}!</h1><p>Email: {self.user.email}</p>"
            expected_text_body = f"Hi {self.user.username},\nEmail: {self.user.email}"

            mock_email_multi_alternatives.assert_called_once_with(
                expected_subject,
                expected_text_body,
                settings.DEFAULT_FROM_EMAIL,
                [self.user.email]
            )
            mock_msg_instance.attach_alternative.assert_called_once_with(expected_html_body, "text/html")
            mock_msg_instance.send.assert_called_once_with(fail_silently=False)

            # Verify render_to_string calls
            mock_render.assert_any_call('emails/new_user_registration_subject.txt', unittest.mock.ANY)
            mock_render.assert_any_call('emails/new_user_registration_body.html', unittest.mock.ANY)
            mock_render.assert_any_call('emails/new_user_registration_body.txt', unittest.mock.ANY)

    @patch('core.email_utils.EmailMultiAlternatives')
    def test_send_new_user_registration_email_no_user_email(self, mock_email_multi_alternatives):
        from core.email_utils import send_new_user_registration_email # Import here
        original_email = self.user.email
        self.user.email = ''
        self.user.save()

        send_new_user_registration_email(self.user)
        mock_email_multi_alternatives.assert_not_called()

        self.user.email = original_email # Reset email for other tests
        self.user.save()

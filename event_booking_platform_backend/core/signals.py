from django.dispatch import receiver
from allauth.account.signals import user_signed_up
from .email_utils import send_new_user_registration_email
import logging

logger = logging.getLogger(__name__)

@receiver(user_signed_up)
def handle_new_user_signup(sender, request, user, **kwargs):
    """
    Handles actions to be performed when a new user signs up.
    Specifically, sends a welcome/registration email.
    """
    try:
        logger.info(f"New user signed up: {user.username} ({user.email}). Sending registration email.")
        send_new_user_registration_email(user)
    except Exception as e:
        # Log any errors during email sending but don't break the registration flow
        logger.error(f"Error sending registration email to {user.email}: {e}")

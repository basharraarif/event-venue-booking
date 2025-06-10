from django.apps import AppConfig # Ensure AppConfig is imported

class PaymentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'payments' # App name as registered in INSTALLED_APPS
    verbose_name = 'Payments'

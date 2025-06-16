from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BookingViewSet
from payments.views import StripeWebhookView # Corrected import

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r'bookings', BookingViewSet, basename='booking')

# The API URLs are now determined automatically by the router.
urlpatterns = [
    path('', include(router.urls)),
    path('webhooks/stripe/', StripeWebhookView.as_view(), name='stripe-webhook'),
]

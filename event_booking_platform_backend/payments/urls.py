from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('create-payment-intent/', views.CreatePaymentIntentView.as_view(), name='create_payment_intent'),
    path('stripe-webhook/', views.StripeWebhookView.as_view(), name='stripe_webhook'),
    path('<uuid:id>/', views.PaymentDetailView.as_view(), name='payment_detail'),
]

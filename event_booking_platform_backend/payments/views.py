import uuid
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from bookings.models import Booking
from .models import Payment
from .serializers import PaymentSerializer
from core.email_utils import send_booking_related_email # Changed import

class PaymentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Payments.
    """
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated: # Should be handled by IsAuthenticated permission, but good practice
            return Payment.objects.none()

        # Base queryset for the user
        queryset = Payment.objects.filter(booking__user=user)

        # Optimize by selecting related objects that are frequently accessed
        # booking__event__venue might be too much for a simple payment list/detail,
        # but booking, booking__user, and booking__event are very common.
        queryset = queryset.select_related(
            'booking',
            'booking__user',
            'booking__event',
            # 'booking__event__venue' # Uncomment if venue details are often shown with payments
        ).order_by('-created_at') # Added ordering

        return queryset

    def perform_create(self, serializer):
        # This method is typically called by DRF after serializer validation
        # The booking_id should be passed in the request data and validated by the serializer
        # Or, if payments are always created alongside bookings, this might not be directly exposed
        # For now, assuming 'booking' (booking_id) is part of validated_data
        # and status is defaulted in the model or here
        booking_id = serializer.validated_data.get('booking_id') # Assuming booking_id is passed
        if not booking_id:
             # This check might be better placed in serializer's validate method
            raise serializers.ValidationError({"booking_id": "This field is required."})

        try:
            booking = Booking.objects.get(id=booking_id, user=self.request.user)
        except Booking.DoesNotExist:
            raise serializers.ValidationError({"booking_id": "Booking not found or permission denied."})

        # Ensure a payment doesn't already exist for this booking, or handle appropriately
        if Payment.objects.filter(booking=booking).exists():
            raise serializers.ValidationError({"booking_id": "A payment for this booking already exists."})

        serializer.save(booking=booking, status='pending')


    @action(detail=True, methods=['post'])
    def succeed_payment(self, request, pk=None):
        payment = self.get_object()
        if payment.status != 'pending':
            return Response({'error': 'Only pending payments can be marked as successful.'}, status=status.HTTP_400_BAD_REQUEST)

        payment.status = 'successful'
        payment.transaction_id = uuid.uuid4().hex # Generate a mock transaction ID
        payment.save()

        # Update booking status to 'confirmed'
        booking = payment.booking
        booking.status = 'confirmed'
        booking.save()

        # Send booking confirmation email
        try:
            send_booking_related_email(
                booking=booking,
                subject_template_name='emails/booking_confirmation_subject.txt',
                body_html_template_name='emails/booking_confirmation_body.html',
                body_text_template_name='emails/booking_confirmation_body.txt'
            )
        except Exception as email_exc:
            print(f"Error sending confirmation email for booking {booking.id}: {email_exc}")
            # Log this error, but don't let it fail the payment success response

        return Response(PaymentSerializer(payment).data)

    @action(detail=True, methods=['post'])
    def fail_payment(self, request, pk=None):
        payment = self.get_object()
        if payment.status != 'pending':
            return Response({'error': 'Only pending payments can be failed.'}, status=status.HTTP_400_BAD_REQUEST)

        payment.status = 'failed'
        payment.save()

        booking = payment.booking
        # Optionally, handle booking status update if a payment fails (e.g., back to 'pending' or 'payment_failed')
        # booking.status = 'payment_failed' # Example, if you have such a status
        # booking.save()

        # Send booking failed email
        try:
            send_booking_related_email(
                booking=booking,
                subject_template_name='emails/booking_failed_subject.txt',
                body_html_template_name='emails/booking_failed_body.html',
                body_text_template_name='emails/booking_failed_body.txt'
            )
        except Exception as email_exc:
            print(f"Error sending booking failed email for booking {booking.id}: {email_exc}")

        return Response(PaymentSerializer(payment).data)

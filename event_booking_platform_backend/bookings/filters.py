import django_filters
from .models import Booking

class BookingFilterSet(django_filters.FilterSet):
    class Meta:
        model = Booking
        fields = {
            'event': ['exact'],       # Filter by event ID: /api/bookings/?event=1
            'user': ['exact'],        # Filter by user ID: /api/bookings/?user=1 (mainly for admins)
            'status': ['exact'],      # Filter by status: /api/bookings/?status=confirmed
        }

# Optional: Add date range filters for booking_time if needed in the future
# booking_time_after = django_filters.DateTimeFilter(field_name='booking_time', lookup_expr='gte')
# booking_time_before = django_filters.DateTimeFilter(field_name='booking_time', lookup_expr='lte')

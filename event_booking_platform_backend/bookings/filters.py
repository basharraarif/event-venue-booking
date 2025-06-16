import django_filters
from .models import Booking

class BookingFilterSet(django_filters.FilterSet):
    class Meta:
        model = Booking
        fields = {
            'event': ['exact'],       # Filter by event ID: /api/bookings/?event=1
            'user': ['exact'],        # Filter by user ID: /api/bookings/?user=1 (mainly for admins)
            'status': ['exact'],      # Filter by status: /api/bookings/?status=confirmed
            # Add booking_time to the fields dictionary to enable them if defined below
            'booking_time': ['gte', 'lte'],
        }

    # Optional: Add date range filters for booking_time if needed in the future
    booking_time_after = django_filters.DateTimeFilter(field_name='booking_time', lookup_expr='gte')
    booking_time_before = django_filters.DateTimeFilter(field_name='booking_time', lookup_expr='lte')

    # To make them usable, they also need to be in Meta.fields or handled if defined outside Meta
    # The above 'booking_time': ['gte', 'lte'] in Meta.fields assumes that DjangoFilter will automatically
    # create filters named 'booking_time__gte' and 'booking_time__lte'.
    # If we define them explicitly as booking_time_after and booking_time_before,
    # they should be listed in Meta.fields by these names if not automatically picked up.
    # For clarity, let's remove 'booking_time': ['gte', 'lte'] from Meta.fields if we define them explicitly.

    class Meta:
        model = Booking
        fields = {
            'event': ['exact'],
            'user': ['exact'],
            'status': ['exact'],
        }
        # Add explicitly defined filters to this list if they are not automatically added by name.
        # However, django-filter usually picks them up if they are attributes of the FilterSet class.
        # For safety, one might list them:
        # fields = ['event', 'user', 'status', 'booking_time_after', 'booking_time_before']
        # Let's rely on auto-pickup for now. If tests fail, will add them explicitly to Meta.fields list.

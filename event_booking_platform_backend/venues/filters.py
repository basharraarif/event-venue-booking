import django_filters
from .models import Venue

class VenueFilter(django_filters.FilterSet):
    capacity = django_filters.NumberFilter(field_name='capacity', lookup_expr='gte')
    is_available = django_filters.BooleanFilter(field_name='is_available')
    min_price_per_hour = django_filters.NumberFilter(field_name='pricing_per_hour', lookup_expr='gte')
    max_price_per_hour = django_filters.NumberFilter(field_name='pricing_per_hour', lookup_expr='lte')
    min_price_per_day = django_filters.NumberFilter(field_name='pricing_per_day', lookup_expr='gte')
    max_price_per_day = django_filters.NumberFilter(field_name='pricing_per_day', lookup_expr='lte')
    address_contains = django_filters.CharFilter(field_name='address', lookup_expr='icontains')
    # You can also add filtering for amenities if it's a JSONField with specific keys
    # For example, if amenities is like {"wifi": true, "parking": false}:
    # amenities_wifi = django_filters.BooleanFilter(field_name='amenities__wifi')

    class Meta:
        model = Venue
        fields = [
            'capacity',
            'is_available',
            'min_price_per_hour',
            'max_price_per_hour',
            'min_price_per_day',
            'max_price_per_day',
            'address_contains',
            # 'amenities_wifi', # if you add specific amenity filters
        ]

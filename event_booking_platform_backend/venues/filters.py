import django_filters
from .models import Venue

class VenueFilter(django_filters.FilterSet):
    capacity = django_filters.NumberFilter(field_name='capacity', lookup_expr='gte')
    is_available = django_filters.BooleanFilter(field_name='is_available')
    min_price_per_hour = django_filters.NumberFilter(field_name='pricing_per_hour', lookup_expr='gte')
    max_price_per_hour = django_filters.NumberFilter(field_name='pricing_per_hour', lookup_expr='lte')
    min_price_per_day = django_filters.NumberFilter(field_name='pricing_per_day', lookup_expr='gte')
    max_price_per_day = django_filters.NumberFilter(field_name='pricing_per_day', lookup_expr='lte')
    name = django_filters.CharFilter(field_name='name', lookup_expr='icontains') # Added for partial name search
    address_contains = django_filters.CharFilter(field_name='address', lookup_expr='icontains')
    # You can also add filtering for amenities if it's a JSONField with specific keys
    # For example, if amenities is like {"wifi": true, "parking": false}:
    # amenities_wifi = django_filters.BooleanFilter(field_name='amenities__wifi')
    amenities_name_in = django_filters.CharFilter(method='filter_amenities_name_in', label="Amenities (any of, comma-separated)")

    def filter_amenities_name_in(self, queryset, name, value):
        # Assumes 'value' is a comma-separated string of amenity names
        # And Venue.amenities is a JSONField storing a list of strings
        if not value:
            return queryset

        amenity_names = [item.strip() for item in value.split(',') if item.strip()]
        if not amenity_names:
            return queryset

        # Manual filtering for SQLite compatibility with JSONField contains
        venue_ids = []
        for venue in queryset:
            if isinstance(venue.amenities, list):
                if any(amenity in venue.amenities for amenity in amenity_names):
                    venue_ids.append(venue.id)

        return queryset.filter(id__in=venue_ids)

    class Meta:
        model = Venue
        fields = [
            'name', # Added name filter
            'capacity',
            'is_available',
            'min_price_per_hour',
            'max_price_per_hour',
            'min_price_per_day',
            'max_price_per_day',
            'address_contains',
            'amenities_name_in', # Added to fields
            'owner', # Added owner filter
            # 'amenities_wifi', # if you add specific amenity filters
        ]

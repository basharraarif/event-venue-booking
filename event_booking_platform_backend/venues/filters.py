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
    amenities_name_in = django_filters.CharFilter(method='filter_amenities_name_in', label="Amenities (any of, comma-separated)")

    def filter_amenities_name_in(self, queryset, name, value):
        # Assumes 'value' is a comma-separated string of amenity names
        # And Venue.amenities is a JSONField storing a list of strings
        if not value:
            return queryset

        amenity_names = [item.strip() for item in value.split(',') if item.strip()]
        if not amenity_names:
            return queryset

        # Create a Q object for each amenity name to check if it's contained in the JSON list
        # This effectively creates an OR condition for each amenity name.
        # For a venue to match, its 'amenities' list must contain AT LEAST ONE of the provided names.
        # Note: This uses 'amenities__contains' which expects a single item or a sublist.
        # If 'amenities' stores ["wifi", "projector"], then amenities__contains='wifi' works.
        # If we want to check if *any* of ["wifi", "screen"] are present, we need OR logic.
        from django.db.models import Q
        query = Q()
        for amenity_name in amenity_names:
            query |= Q(amenities__contains=amenity_name) # Check if the amenity is in the list

        return queryset.filter(query).distinct() # .distinct() if multiple OR conditions could match the same venue

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
            'amenities_name_in', # Added to fields
            'owner', # Added owner filter
            # 'amenities_wifi', # if you add specific amenity filters
        ]

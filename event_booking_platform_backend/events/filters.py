import django_filters
from .models import Event, Category

class EventFilterSet(django_filters.FilterSet):
    # Filter by event name (case-insensitive partial match)
    name = django_filters.CharFilter(field_name='name', lookup_expr='icontains')

    # Filter by category name
    category_name = django_filters.CharFilter(field_name='categories__name', lookup_expr='iexact')

    # Filter by date range for start_time
    start_time_after = django_filters.DateTimeFilter(field_name='start_time', lookup_expr='gte')
    start_time_before = django_filters.DateTimeFilter(field_name='start_time', lookup_expr='lte')

    # Filter by venue ID (exact match)
    # venue_id = django_filters.NumberFilter(field_name='venue__id') # Alternative if 'venue' field is not directly filterable by ID

    class Meta:
        model = Event
        fields = {
            'venue': ['exact'], # Allows filtering by venue ID: /api/events/?venue=1
            'organizer': ['exact'], # Allows filtering by organizer ID: /api/events/?organizer=1
            'status': ['exact'], # Allows filtering by status: /api/events/?status=upcoming
            # 'categories': ['exact'], # Allows filtering by category ID directly if needed
        }

# Note: For ManyToManyField 'categories', filtering by 'categories__id' or 'categories__name'
# is often more useful. 'categories__name' is added above.
# If you want to filter by multiple category IDs (e.g., events that are in category 1 AND category 2,
# or category 1 OR category 2), more complex filter setup or custom methods might be needed.
# The `category_name` filter above allows filtering for one category by its exact name.
# To filter by multiple categories (e.g., categories=1,2 or categories__name=Music,Sports),
# you might need a ModelMultipleChoiceFilter or a custom method.
# For simplicity, starting with single category name filter.

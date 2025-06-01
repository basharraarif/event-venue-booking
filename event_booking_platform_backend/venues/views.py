from rest_framework import viewsets, filters # Import filters
from .models import Venue
from .serializers import VenueSerializer
from .filters import VenueFilter # Import VenueFilter

class VenueViewSet(viewsets.ModelViewSet):
    queryset = Venue.objects.all()
    serializer_class = VenueSerializer
    filterset_class = VenueFilter # Set the filterset class

    # Since SearchFilter is in DEFAULT_FILTER_BACKENDS,
    # we just need to specify which fields it should search on.
    search_fields = ['name', 'address', 'amenities'] # amenities can be searched if it's JSON and your DB supports it well, or if it's TextField

    # Basic permissioning can be added later if needed, e.g.:
    # from rest_framework import permissions
    # permission_classes = [permissions.IsAuthenticatedOrReadOnly]

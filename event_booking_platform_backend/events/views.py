from rest_framework import viewsets, permissions
from django_filters.rest_framework import DjangoFilterBackend
from .models import Event, Category
from .serializers import EventSerializer, CategorySerializer
from .filters import EventFilterSet

class CategoryViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows categories to be viewed or edited.
    """
    queryset = Category.objects.all().order_by('name')
    serializer_class = CategorySerializer
    permission_classes = [permissions.DjangoModelPermissionsOrAnonReadOnly]

class EventViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows events to be viewed or edited.
    Supports filtering by:
    - name (icontains)
    - venue (ID)
    - organizer (ID)
    - status (exact: upcoming, ongoing, past, cancelled)
    - category_name (exact name of one category)
    - start_time_after (YYYY-MM-DD[THH:MM[:SS[.ffffff]][Z|+HHMM]] format)
    - start_time_before (YYYY-MM-DD[THH:MM[:SS[.ffffff]][Z|+HHMM]] format)
    """
    queryset = Event.objects.all().order_by('-start_time')
    serializer_class = EventSerializer
    permission_classes = [permissions.DjangoModelPermissionsOrAnonReadOnly] # DjangoObjectPermissions can be added here if object-level perms are specifically needed beyond model perms.
    filter_backends = [DjangoFilterBackend] # Removed permissions.DjangoObjectPermissions from here
    filterset_class = EventFilterSet
    # For more complex searches, you can add:
    # search_fields = ['name', 'description', 'venue__name', 'categories__name']
    # ordering_fields = ['start_time', 'name', 'status', 'venue__name']

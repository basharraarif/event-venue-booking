from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import VenueViewSet

router = DefaultRouter()
router.register(r'', VenueViewSet, basename='venue') # Registering at the root of this app's URLs

urlpatterns = [
    path('', include(router.urls)),
]

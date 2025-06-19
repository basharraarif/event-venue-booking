"""
URL configuration for event_booking_platform_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from core import views as core_views

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r"users", core_views.UserViewSet)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),  # Include the router URLs
    # path('api/auth/', include('rest_framework.urls', namespace='rest_framework')), # Old DRF auth
    path("api/auth/", include("dj_rest_auth.urls")),  # dj-rest-auth main URLs
    path("api/auth/registration/", include("dj_rest_auth.registration.urls")),  # dj-rest-auth registration
    path("api/venues/", include("venues.urls")),  # Venue URLs
    path("api/events-management/", include("events.urls")),  # Event and Category URLs
    path("api/bookings/", include("bookings.urls")),  # Booking URLs
    path("api/payments/", include("payments.urls")),  # Payment URLs
    # API Schema & Docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]

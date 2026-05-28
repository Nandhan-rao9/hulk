"""
URL configuration for hulk project.
"""

from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.activities.views import ActivityViewSet
from apps.ingestion.views import SourceFileViewSet
from apps.core.views import (
    CSRFTokenView, LoginView, LogoutView, CurrentUserView,
    PlantLookupUploadView, MaterialMappingUploadView
)

# DRF router for API endpoints
router = DefaultRouter()
router.register(r'activities', ActivityViewSet, basename='activity')
router.register(r'source-files', SourceFileViewSet, basename='sourcefile')

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
    path('api-auth/', include('rest_framework.urls')),  # DRF browsable API login

    # Auth endpoints
    path('api/auth/csrf/', CSRFTokenView.as_view(), name='auth-csrf'),
    path('api/auth/login/', LoginView.as_view(), name='auth-login'),
    path('api/auth/logout/', LogoutView.as_view(), name='auth-logout'),
    path('api/auth/me/', CurrentUserView.as_view(), name='auth-me'),

    # Lookup upload endpoints (admin only)
    path('api/lookups/plant/upload/', PlantLookupUploadView.as_view(), name='plant-lookup-upload'),
    path('api/lookups/material-mapping/upload/', MaterialMappingUploadView.as_view(), name='material-mapping-upload'),
]

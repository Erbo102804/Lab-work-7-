"""URL configuration for config project."""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/doc/', include('django.contrib.admindocs.urls')),  # django docs
    path('admin/', admin.site.urls),
    path('', include('tours.urls')),
]

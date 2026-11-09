from django.urls import path

from . import views

app_name = 'tours'

urlpatterns = [
    path('', views.TourListView.as_view(), name='list'),
    path('create/', views.TourCreateView.as_view(), name='create'),
    path('<int:pk>/', views.TourDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.TourUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.TourDeleteView.as_view(), name='delete'),
    path('<int:pk>/comment/', views.CommentCreateView.as_view(), name='comment'),
    path('session/<int:pk>/book/', views.BookingCreateView.as_view(), name='book'),
]

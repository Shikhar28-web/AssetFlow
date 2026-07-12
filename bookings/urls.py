from django.urls import path
from . import views

urlpatterns = [
    path('', views.booking_list, name='booking_list'),
    path('book/', views.book_resource, name='book_resource'),
    path('book/<int:asset_pk>/', views.book_resource, name='book_resource_specific'),
    path('cancel/<int:pk>/', views.cancel_booking, name='cancel_booking'),
    path('api/events/<int:asset_pk>/', views.booking_calendar_api, name='booking_calendar_api'),
    path('<int:pk>/ics/', views.download_booking_ics, name='download_booking_ics'),
    path('api/sync-mock/<int:pk>/', views.booking_sync_mock_api, name='booking_sync_mock_api'),
]

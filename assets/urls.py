from django.urls import path
from . import views

urlpatterns = [
    path('', views.asset_list, name='asset_list'),
    path('register/', views.asset_register, name='asset_register'),
    path('edit/<int:pk>/', views.asset_edit, name='asset_edit'),
    path('<int:pk>/', views.asset_detail, name='asset_detail'),
    path('reports/', views.reports_view, name='reports_view'),
    path('qr-lookup/', views.qr_lookup, name='qr_lookup'),
]

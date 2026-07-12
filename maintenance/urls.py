from django.urls import path
from . import views

urlpatterns = [
    path('', views.maintenance_list, name='maintenance_list'),
    path('raise/', views.raise_maintenance, name='raise_maintenance'),
    path('raise/<int:asset_pk>/', views.raise_maintenance, name='raise_maintenance_specific'),
    path('<int:pk>/', views.maintenance_detail, name='maintenance_detail'),
]

from django.urls import path
from . import views

urlpatterns = [
    path('', views.audit_list, name='audit_list'),
    path('create/', views.audit_create, name='audit_create'),
    path('<int:pk>/', views.audit_detail, name='audit_detail'),
    path('<int:cycle_pk>/verify/<int:item_pk>/', views.audit_item_verify, name='audit_item_verify'),
    path('<int:pk>/close/', views.audit_close, name='audit_close'),
]

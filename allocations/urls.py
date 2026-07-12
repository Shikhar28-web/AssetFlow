from django.urls import path
from . import views

urlpatterns = [
    path('allocate/', views.allocate_asset, name='allocate_asset'),
    path('allocate/<int:asset_pk>/', views.allocate_asset, name='allocate_asset_specific'),
    path('return/<int:allocation_pk>/', views.return_asset, name='return_asset'),
    path('transfer/request/<int:asset_pk>/', views.raise_transfer_request, name='raise_transfer_request'),
    path('transfers/', views.transfer_list, name='transfer_list'),
    path('transfer/approve/<int:transfer_pk>/', views.approve_transfer, name='approve_transfer'),
    path('transfer/reject/<int:transfer_pk>/', views.reject_transfer, name='reject_transfer'),
    path('device-requests/new/', views.device_request_create, name='device_request_create'),
    path('device-requests/', views.device_request_list, name='device_request_list'),
    path('device-requests/manage/', views.device_request_manage, name='device_request_manage'),
    path('device-requests/approve/<int:pk>/', views.device_request_approve, name='device_request_approve'),
    path('device-requests/reject/<int:pk>/', views.device_request_reject, name='device_request_reject'),
]

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
]

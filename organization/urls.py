from django.urls import path
from . import views

urlpatterns = [
    path('setup/', views.organization_setup, name='organization_setup'),
    path('department/create/', views.department_create, name='department_create'),
    path('department/edit/<int:pk>/', views.department_edit, name='department_edit'),
    path('category/create/', views.category_create, name='category_create'),
    path('category/edit/<int:pk>/', views.category_edit, name='category_edit'),
    path('employee/promote/<int:pk>/', views.employee_promote, name='employee_promote'),
]

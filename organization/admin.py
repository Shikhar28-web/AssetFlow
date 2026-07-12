from django.contrib import admin
from .models import Department, AssetCategory

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'head', 'parent_department', 'status')
    list_filter = ('status', 'parent_department')
    search_fields = ('name', 'code')

@admin.register(AssetCategory)
class AssetCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

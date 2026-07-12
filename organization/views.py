from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from .models import Department, AssetCategory
from accounts.models import User
from .forms import DepartmentForm, AssetCategoryForm, RolePromotionForm
from notifications.models import ActionLog

def is_admin(user):
    return user.is_authenticated and (user.role == 'admin' or user.is_staff)

@user_passes_test(is_admin)
def organization_setup(request):
    departments = Department.objects.all().order_by('name')
    categories = AssetCategory.objects.all().order_by('name')
    
    # Filter employee directory
    search_query = request.GET.get('search', '')
    employees = User.objects.all().order_by('email')
    if search_query:
        employees = employees.filter(
            email__icontains=search_query
        ) | employees.filter(
            first_name__icontains=search_query
        ) | employees.filter(
            last_name__icontains=search_query
        )
    
    active_tab = request.GET.get('tab', 'departments')
    
    context = {
        'departments': departments,
        'categories': categories,
        'employees': employees,
        'search_query': search_query,
        'active_tab': active_tab,
    }
    return render(request, 'organization/setup.html', context)

@user_passes_test(is_admin)
def department_create(request):
    if request.method == 'POST':
        form = DepartmentForm(request.POST)
        if form.is_valid():
            dept = form.save()
            ActionLog.objects.create(
                user=request.user,
                action="Department Created",
                details=f"Created department {dept.name} ({dept.code})"
            )
            messages.success(request, f"Department '{dept.name}' created successfully.")
            return redirect('/organization/setup/?tab=departments')
    else:
        form = DepartmentForm()
    return render(request, 'organization/department_form.html', {'form': form, 'title': 'Create Department'})

@user_passes_test(is_admin)
def department_edit(request, pk):
    dept = get_object_or_404(Department, pk=pk)
    if request.method == 'POST':
        form = DepartmentForm(request.POST, instance=dept)
        if form.is_valid():
            form.save()
            ActionLog.objects.create(
                user=request.user,
                action="Department Updated",
                details=f"Updated department {dept.name} ({dept.code})"
            )
            messages.success(request, f"Department '{dept.name}' updated successfully.")
            return redirect('/organization/setup/?tab=departments')
    else:
        form = DepartmentForm(instance=dept)
    return render(request, 'organization/department_form.html', {'form': form, 'title': f'Edit Department: {dept.name}'})

@user_passes_test(is_admin)
def category_create(request):
    if request.method == 'POST':
        form = AssetCategoryForm(request.POST)
        if form.is_valid():
            cat = form.save()
            ActionLog.objects.create(
                user=request.user,
                action="Asset Category Created",
                details=f"Created asset category {cat.name}"
            )
            messages.success(request, f"Asset Category '{cat.name}' created successfully.")
            return redirect('/organization/setup/?tab=categories')
    else:
        form = AssetCategoryForm()
    return render(request, 'organization/category_form.html', {'form': form, 'title': 'Create Asset Category'})

@user_passes_test(is_admin)
def category_edit(request, pk):
    cat = get_object_or_404(AssetCategory, pk=pk)
    if request.method == 'POST':
        form = AssetCategoryForm(request.POST, instance=cat)
        if form.is_valid():
            form.save()
            ActionLog.objects.create(
                user=request.user,
                action="Asset Category Updated",
                details=f"Updated asset category {cat.name}"
            )
            messages.success(request, f"Asset Category '{cat.name}' updated successfully.")
            return redirect('/organization/setup/?tab=categories')
    else:
        form = AssetCategoryForm(instance=cat)
    return render(request, 'organization/category_form.html', {'form': form, 'title': f'Edit Asset Category: {cat.name}'})

@user_passes_test(is_admin)
def employee_promote(request, pk):
    employee = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = RolePromotionForm(request.POST, instance=employee)
        if form.is_valid():
            form.save()
            ActionLog.objects.create(
                user=request.user,
                action="Employee Promoted/Modified",
                details=f"Modified employee {employee.email}: Role={employee.role}, Dept={employee.department}, Status={employee.status}"
            )
            messages.success(request, f"Employee '{employee.email}' updated successfully.")
            return redirect('/organization/setup/?tab=employees')
    else:
        form = RolePromotionForm(instance=employee)
    return render(request, 'organization/employee_promote.html', {'form': form, 'employee': employee})

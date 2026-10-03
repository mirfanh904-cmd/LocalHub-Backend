from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db.models import Sum, Q, Count
from django.utils import timezone
from django.http import Http404

from accounts.models import User, ProfessionalProfile, UserProfile, Address, FavouriteService, FavouriteProfessional
from services.models import Category, Service, ServicePackage, ServiceFAQ, ServiceRequirement, ServiceGroup
from bookings.models import Booking, BookingStatus, BookingStatusHistory
from bookings.services import BookingService
from bookings.selectors import BookingSelector
from services.services.services import CategoryService, ServiceService, PackageService, ServiceRequirementService, ServiceGroupService

from .forms import CategoryForm, ServiceForm, ServicePackageForm, ServiceFAQForm, ServiceRequirementForm, ServiceGroupForm
from verification.models import VerificationStatus
# Check if superuser or admin role
def is_admin(user):
    return user.is_authenticated and (user.is_superuser or user.role == "ADMIN")


@login_required
@user_passes_test(is_admin)
def dashboard(request):
    today = timezone.localdate()
    
    total_users = User.objects.count()
    total_professionals = ProfessionalProfile.objects.count()
    pending_approvals = ProfessionalProfile.objects.filter(
        verification__status=VerificationStatus.PENDING
    ).count()
    total_categories = Category.objects.count()
    total_services = Service.objects.count()
    
    pending_bookings = Booking.objects.filter(status=BookingStatus.PENDING).count()
    today_bookings = Booking.objects.filter(booking_date=today).count()
    
    revenue_res = Booking.objects.filter(status=BookingStatus.COMPLETED).aggregate(Sum("total_amount"))
    total_revenue = revenue_res.get("total_amount__sum") or 0.00
    
    # Recent logs
    latest_bookings = Booking.objects.select_related("customer", "service", "worker").order_by("-created_at")[:5]
    latest_professionals = ProfessionalProfile.objects.select_related("user").order_by("-created_at")[:5]
    latest_customers = User.objects.filter(role="CUSTOMER").order_by("-created_at")[:5]
    
    context = {
        "total_users": total_users,
        "total_professionals": total_professionals,
        "pending_approvals": pending_approvals,
        "total_categories": total_categories,
        "total_services": total_services,
        "pending_bookings": pending_bookings,
        "today_bookings": today_bookings,
        "total_revenue": total_revenue,
        "latest_bookings": latest_bookings,
        "latest_professionals": latest_professionals,
        "latest_customers": latest_customers,
    }
    return render(request, "dashboard/admin/dashboard.html", context)


# =========================================================================
# SERVICE GROUP MANAGEMENT
# =========================================================================

@login_required
@user_passes_test(is_admin)
def service_group_list(request):
    query = request.GET.get("search", "")
    groups = ServiceGroup.objects.annotate(
        categories_count=Count("categories", distinct=True),
        services_count=Count("categories__services", distinct=True)
    ).order_by("-created_at")
    
    if query:
        groups = groups.filter(Q(name__icontains=query) | Q(short_description__icontains=query))
        
    paginator = Paginator(groups, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    
    return render(request, "dashboard/admin/service_groups/list.html", {
        "page_obj": page_obj,
        "search": query,
    })


@login_required
@user_passes_test(is_admin)
def service_group_create(request):
    if request.method == "POST":
        form = ServiceGroupForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                ServiceGroupService.create(**form.cleaned_data)
                messages.success(request, "Service Group created successfully.")
                return redirect("admin_service_group_list")
            except Exception as e:
                messages.error(request, f"Error creating service group: {e}")
    else:
        form = ServiceGroupForm()
    return render(request, "dashboard/admin/service_groups/form.html", {"form": form, "title": "Create Service Group"})


@login_required
@user_passes_test(is_admin)
def service_group_edit(request, pk):
    group = get_object_or_404(ServiceGroup, pk=pk)
    if request.method == "POST":
        form = ServiceGroupForm(request.POST, request.FILES, instance=group)
        if form.is_valid():
            try:
                ServiceGroupService.update(group, **form.cleaned_data)
                messages.success(request, "Service Group updated successfully.")
                return redirect("admin_service_group_list")
            except Exception as e:
                messages.error(request, f"Error updating service group: {e}")
    else:
        form = ServiceGroupForm(instance=group)
    return render(request, "dashboard/admin/service_groups/form.html", {"form": form, "title": "Edit Service Group", "group": group})


@login_required
@user_passes_test(is_admin)
def service_group_delete(request, pk):
    group = get_object_or_404(ServiceGroup, pk=pk)
    if group.categories.exists():
        messages.error(request, f"Cannot delete Service Group '{group.name}' as it contains categories.")
    else:
        ServiceGroupService.delete(group)
        messages.success(request, f"Service Group '{group.name}' deleted successfully.")
    return redirect("admin_service_group_list")


@login_required
@user_passes_test(is_admin)
def service_group_toggle_active(request, pk):
    group = get_object_or_404(ServiceGroup, pk=pk)
    group.is_active = not group.is_active
    group.save(update_fields=["is_active"])
    messages.success(request, f"Service Group '{group.name}' status updated.")
    return redirect("admin_service_group_list")


# =========================================================================
# CATEGORY MANAGEMENT
# =========================================================================

@login_required
@user_passes_test(is_admin)
def category_list(request):
    query = request.GET.get("search", "")
    group_id = request.GET.get("group", "")
    
    categories = Category.objects.annotate(
        services_count=Count("services", distinct=True)
    ).select_related("service_group").order_by("-created_at")
    
    if query:
        categories = categories.filter(Q(name__icontains=query) | Q(short_description__icontains=query))
    if group_id:
        categories = categories.filter(service_group_id=group_id)
        
    paginator = Paginator(categories, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    
    groups = ServiceGroup.objects.all()
    
    return render(request, "dashboard/admin/categories/list.html", {
        "page_obj": page_obj,
        "search": query,
        "groups": groups,
        "selected_group": group_id,
    })


@login_required
@user_passes_test(is_admin)
def category_create(request):
    if request.method == "POST":
        form = CategoryForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                CategoryService.create(form.cleaned_data)
                messages.success(request, "Category created successfully.")
                return redirect("admin_category_list")
            except Exception as e:
                messages.error(request, f"Error creating category: {e}")
    else:
        form = CategoryForm()
    return render(request, "dashboard/admin/categories/form.html", {"form": form, "title": "Create Category"})


@login_required
@user_passes_test(is_admin)
def category_edit(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == "POST":
        form = CategoryForm(request.POST, request.FILES, instance=category)
        if form.is_valid():
            try:
                CategoryService.update(category, form.cleaned_data)
                messages.success(request, "Category updated successfully.")
                return redirect("admin_category_list")
            except Exception as e:
                messages.error(request, f"Error updating category: {e}")
    else:
        form = CategoryForm(instance=category)
    return render(request, "dashboard/admin/categories/form.html", {"form": form, "title": "Edit Category", "category": category})


@login_required
@user_passes_test(is_admin)
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if category.services.exists():
        messages.error(request, f"Cannot delete category '{category.name}' as it contains services.")
    else:
        CategoryService.delete(category)
        messages.success(request, f"Category '{category.name}' deleted successfully.")
    return redirect("admin_category_list")


@login_required
@user_passes_test(is_admin)
def category_toggle_active(request, pk):
    category = get_object_or_404(Category, pk=pk)
    category.is_active = not category.is_active
    category.save(update_fields=["is_active"])
    messages.success(request, f"Category '{category.name}' status updated.")
    return redirect("admin_category_list")


@login_required
@user_passes_test(is_admin)
def category_toggle_featured(request, pk):
    category = get_object_or_404(Category, pk=pk)
    category.is_featured = not category.is_featured
    category.save(update_fields=["is_featured"])
    messages.success(request, f"Category '{category.name}' featured status updated.")
    return redirect("admin_category_list")


@login_required
@user_passes_test(is_admin)
def category_bulk_action(request):
    if request.method == "POST":
        action = request.POST.get("action")
        selected_ids = request.POST.getlist("selected_categories")
        
        if not selected_ids:
            messages.warning(request, "No categories selected.")
            return redirect("admin_category_list")
            
        queryset = Category.objects.filter(id__in=selected_ids)
        
        if action == "activate":
            queryset.update(is_active=True)
            messages.success(request, f"Activated {queryset.count()} categories.")
        elif action == "deactivate":
            queryset.update(is_active=False)
            messages.success(request, f"Deactivated {queryset.count()} categories.")
        elif action == "feature":
            queryset.update(is_featured=True)
            messages.success(request, f"Featured {queryset.count()} categories.")
        elif action == "unfeature":
            queryset.update(is_featured=False)
            messages.success(request, f"Unfeatured {queryset.count()} categories.")
        elif action == "delete":
            deleted_count = 0
            for category in queryset:
                if category.services.exists():
                    messages.error(request, f"Cannot delete '{category.name}' as it contains services.")
                else:
                    CategoryService.delete(category)
                    deleted_count += 1
            if deleted_count > 0:
                messages.success(request, f"Successfully deleted {deleted_count} categories.")
                
    return redirect("admin_category_list")


# =========================================================================
# SERVICE MANAGEMENT
# =========================================================================

@login_required
@user_passes_test(is_admin)
def service_list(request):
    query = request.GET.get("search", "")
    category_id = request.GET.get("category", "")
    
    services = Service.objects.select_related("category").all()
    
    if query:
        services = services.filter(Q(name__icontains=query) | Q(short_description__icontains=query))
    if category_id:
        services = services.filter(category_id=category_id)
        
    paginator = Paginator(services, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    
    categories = Category.objects.all()
    
    return render(request, "dashboard/admin/services/list.html", {
        "page_obj": page_obj,
        "search": query,
        "categories": categories,
        "selected_category": category_id,
    })


@login_required
@user_passes_test(is_admin)
def service_create(request):
    if request.method == "POST":
        form = ServiceForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                ServiceService.create(form.cleaned_data)
                messages.success(request, "Service created successfully.")
                return redirect("admin_service_list")
            except Exception as e:
                messages.error(request, f"Error creating service: {e}")
    else:
        form = ServiceForm()
    return render(request, "dashboard/admin/services/form.html", {"form": form, "title": "Create Service"})


@login_required
@user_passes_test(is_admin)
def service_edit(request, pk):
    service = get_object_or_404(Service, pk=pk)
    if request.method == "POST":
        form = ServiceForm(request.POST, request.FILES, instance=service)
        if form.is_valid():
            try:
                ServiceService.update(service, form.cleaned_data)
                messages.success(request, "Service updated successfully.")
                return redirect("admin_service_list")
            except Exception as e:
                messages.error(request, f"Error updating service: {e}")
    else:
        form = ServiceForm(instance=service)
        
    # Nested resources for managing Packages, FAQs, and Requirements
    packages = service.packages.all()
    faqs = service.faqs.all()
    requirements = service.requirements.all()
    
    # Related Professionals Providing this service
    professionals = ProfessionalProfile.objects.filter(services__service=service).select_related("user")
    
    return render(request, "dashboard/admin/services/form.html", {
        "form": form,
        "title": "Edit Service",
        "service": service,
        "packages": packages,
        "faqs": faqs,
        "requirements": requirements,
        "professionals": professionals,
    })


@login_required
@user_passes_test(is_admin)
def service_delete(request, pk):
    service = get_object_or_404(Service, pk=pk)
    if service.bookings.exists():
        messages.error(request, f"Cannot delete service '{service.name}' as it has existing bookings. Recommend marking it inactive instead.")
    elif service.packages.exists() or service.faqs.exists() or service.requirements.exists():
        messages.error(request, f"Cannot delete service '{service.name}' as it contains packages, FAQs, or requirements. Please delete those first.")
    else:
        ServiceService.delete(service)
        messages.success(request, f"Service '{service.name}' deleted successfully.")
    return redirect("admin_service_list")


@login_required
@user_passes_test(is_admin)
def service_toggle_active(request, pk):
    service = get_object_or_404(Service, pk=pk)
    service.is_active = not service.is_active
    service.save(update_fields=["is_active"])
    messages.success(request, f"Service '{service.name}' status updated.")
    return redirect("admin_service_list")


@login_required
@user_passes_test(is_admin)
def service_toggle_featured(request, pk):
    service = get_object_or_404(Service, pk=pk)
    service.is_featured = not service.is_featured
    service.save(update_fields=["is_featured"])
    messages.success(request, f"Service '{service.name}' featured status updated.")
    return redirect("admin_service_list")


# =========================================================================
# NESTED SERVICE SUB-RESOURCES (Packages, FAQs, Requirements)
# =========================================================================

# Service Packages CRUD
@login_required
@user_passes_test(is_admin)
def package_create(request, service_pk):
    service = get_object_or_404(Service, pk=service_pk)
    if request.method == "POST":
        form = ServicePackageForm(request.POST)
        if form.is_valid():
            try:
                PackageService.create(service=service, **form.cleaned_data)
                messages.success(request, "Service Package added successfully.")
                return redirect("admin_service_edit", pk=service_pk)
            except Exception as e:
                messages.error(request, f"Error saving package: {e}")
    else:
        form = ServicePackageForm()
    return render(request, "dashboard/admin/services/packages/form.html", {"form": form, "service": service, "title": "Add Package"})


@login_required
@user_passes_test(is_admin)
def package_edit(request, service_pk, pk):
    service = get_object_or_404(Service, pk=service_pk)
    package = get_object_or_404(ServicePackage, pk=pk, service=service)
    if request.method == "POST":
        form = ServicePackageForm(request.POST, instance=package)
        if form.is_valid():
            try:
                PackageService.update(package, **form.cleaned_data)
                messages.success(request, "Service Package updated successfully.")
                return redirect("admin_service_edit", pk=service_pk)
            except Exception as e:
                messages.error(request, f"Error updating package: {e}")
    else:
        form = ServicePackageForm(instance=package)
    return render(request, "dashboard/admin/services/packages/form.html", {"form": form, "service": service, "package": package, "title": "Edit Package"})


@login_required
@user_passes_test(is_admin)
def package_delete(request, service_pk, pk):
    package = get_object_or_404(ServicePackage, pk=pk, service_id=service_pk)
    package.delete()
    messages.success(request, "Service Package deleted successfully.")
    return redirect("admin_service_edit", pk=service_pk)


# Service FAQs CRUD
@login_required
@user_passes_test(is_admin)
def faq_create(request, service_pk):
    service = get_object_or_404(Service, pk=service_pk)
    if request.method == "POST":
        form = ServiceFAQForm(request.POST)
        if form.is_valid():
            faq = form.save(commit=False)
            faq.service = service
            faq.save()
            messages.success(request, "FAQ added successfully.")
            return redirect("admin_service_edit", pk=service_pk)
    else:
        form = ServiceFAQForm()
    return render(request, "dashboard/admin/services/faqs/form.html", {"form": form, "service": service, "title": "Add FAQ"})


@login_required
@user_passes_test(is_admin)
def faq_edit(request, service_pk, pk):
    service = get_object_or_404(Service, pk=service_pk)
    faq = get_object_or_404(ServiceFAQ, pk=pk, service=service)
    if request.method == "POST":
        form = ServiceFAQForm(request.POST, instance=faq)
        if form.is_valid():
            form.save()
            messages.success(request, "FAQ updated successfully.")
            return redirect("admin_service_edit", pk=service_pk)
    else:
        form = ServiceFAQForm(instance=faq)
    return render(request, "dashboard/admin/services/faqs/form.html", {"form": form, "service": service, "faq": faq, "title": "Edit FAQ"})


@login_required
@user_passes_test(is_admin)
def faq_delete(request, service_pk, pk):
    faq = get_object_or_404(ServiceFAQ, pk=pk, service_id=service_pk)
    faq.delete()
    messages.success(request, "FAQ deleted successfully.")
    return redirect("admin_service_edit", pk=service_pk)


# Service Requirements CRUD
@login_required
@user_passes_test(is_admin)
def requirement_create(request, service_pk):
    service = get_object_or_404(Service, pk=service_pk)
    if request.method == "POST":
        form = ServiceRequirementForm(request.POST)
        if form.is_valid():
            req = form.save(commit=False)
            req.service = service
            req.save()
            messages.success(request, "Requirement added successfully.")
            return redirect("admin_service_edit", pk=service_pk)
    else:
        form = ServiceRequirementForm()
    return render(request, "dashboard/admin/services/requirements/form.html", {"form": form, "service": service, "title": "Add Requirement"})


@login_required
@user_passes_test(is_admin)
def requirement_edit(request, service_pk, pk):
    service = get_object_or_404(Service, pk=service_pk)
    requirement = get_object_or_404(ServiceRequirement, pk=pk, service=service)
    if request.method == "POST":
        form = ServiceRequirementForm(request.POST, instance=requirement)
        if form.is_valid():
            form.save()
            messages.success(request, "Requirement updated successfully.")
            return redirect("admin_service_edit", pk=service_pk)
    else:
        form = ServiceRequirementForm(instance=requirement)
    return render(request, "dashboard/admin/services/requirements/form.html", {"form": form, "service": service, "requirement": requirement, "title": "Edit Requirement"})


@login_required
@user_passes_test(is_admin)
def requirement_delete(request, service_pk, pk):
    requirement = get_object_or_404(ServiceRequirement, pk=pk, service_id=service_pk)
    requirement.delete()
    messages.success(request, "Requirement deleted successfully.")
    return redirect("admin_service_edit", pk=service_pk)


# =========================================================================
# PROFESSIONAL MANAGEMENT
# =========================================================================

@login_required
@user_passes_test(is_admin)
def professional_list(request):
    query = request.GET.get("search", "")
    status_filter = request.GET.get("status", "")
    
    professionals = ProfessionalProfile.objects.select_related("user", "verification").order_by("-created_at")
    
    if query:
        professionals = professionals.filter(Q(user__first_name__icontains=query) | Q(user__last_name__icontains=query) | Q(professional_title__icontains=query))
    if status_filter:
        professionals = professionals.filter(verification__status=status_filter.lower())
        
    paginator = Paginator(professionals, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    
    return render(request, "dashboard/admin/professionals/list.html", {
        "page_obj": page_obj,
        "search": query,
        "selected_status": status_filter,
    })


@login_required
@user_passes_test(is_admin)
def professional_detail(request, pk):
    professional = get_object_or_404(ProfessionalProfile.objects.select_related("user", "verification"), pk=pk)
    assigned_services = professional.services.select_related("service")
    return render(request, "dashboard/admin/professionals/detail.html", {
        "professional": professional,
        "assigned_services": assigned_services,
    })


@login_required
@user_passes_test(is_admin)
def approve_professional(request, pk):
    professional = get_object_or_404(ProfessionalProfile, pk=pk)
    from verification.services import VerificationService
    from verification.models import VerificationStatus
    verification = VerificationService.get_verification(professional)
    if verification.status == VerificationStatus.DRAFT:
        verification.status = VerificationStatus.PENDING
        verification.save(update_fields=["status"])
    try:
        VerificationService.approve_verification(verification, request.user)
        messages.success(request, f"Professional profile for '{professional.user.full_name}' is approved.")
    except Exception as e:
        messages.error(request, str(e))
    return redirect("admin_professional_detail", pk=pk)


@login_required
@user_passes_test(is_admin)
def reject_professional(request, pk):
    professional = get_object_or_404(ProfessionalProfile, pk=pk)
    from verification.services import VerificationService
    from verification.models import VerificationStatus
    verification = VerificationService.get_verification(professional)
    if verification.status == VerificationStatus.DRAFT:
        verification.status = VerificationStatus.PENDING
        verification.save(update_fields=["status"])
    reason = request.POST.get("reason", "Rejected by administrator.")
    try:
        VerificationService.reject_verification(verification, request.user, reason=reason)
        messages.success(request, f"Professional profile for '{professional.user.full_name}' is rejected.")
    except Exception as e:
        messages.error(request, str(e))
    return redirect("admin_professional_detail", pk=pk)


# =========================================================================
# CUSTOMER MANAGEMENT
# =========================================================================

@login_required
@user_passes_test(is_admin)
def customer_list(request):
    query = request.GET.get("search", "")
    customers = User.objects.filter(role="CUSTOMER").order_by("-created_at")
    
    if query:
        customers = customers.filter(Q(first_name__icontains=query) | Q(last_name__icontains=query) | Q(email__icontains=query))
        
    paginator = Paginator(customers, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    
    return render(request, "dashboard/admin/customers/list.html", {
        "page_obj": page_obj,
        "search": query,
    })


@login_required
@user_passes_test(is_admin)
def customer_detail(request, pk):
    customer = get_object_or_404(User, pk=pk, role="CUSTOMER")
    addresses = customer.addresses.all()
    bookings = Booking.objects.filter(customer=customer).select_related("service", "worker").order_by("-created_at")
    
    # Favorites
    fav_services = FavouriteService.objects.filter(user=customer).select_related("service")
    fav_professionals = FavouriteProfessional.objects.filter(user=customer).select_related("professional", "professional__user")
    
    return render(request, "dashboard/admin/customers/detail.html", {
        "customer": customer,
        "addresses": addresses,
        "bookings": bookings,
        "fav_services": fav_services,
        "fav_professionals": fav_professionals,
    })


# =========================================================================
# BOOKING MANAGEMENT
# =========================================================================

@login_required
@user_passes_test(is_admin)
def booking_list(request):
    query = request.GET.get("search", "")
    status_filter = request.GET.get("status", "")
    date_filter = request.GET.get("date", "")
    
    bookings = Booking.objects.select_related("customer", "service", "worker").order_by("-created_at")
    
    if query:
        bookings = bookings.filter(booking_number__icontains=query)
    if status_filter:
        bookings = bookings.filter(status=status_filter)
    if date_filter:
        bookings = bookings.filter(booking_date=date_filter)
        
    paginator = Paginator(bookings, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    
    status_choices = BookingStatus.choices
    
    return render(request, "dashboard/admin/bookings/list.html", {
        "page_obj": page_obj,
        "search": query,
        "selected_status": status_filter,
        "selected_date": date_filter,
        "status_choices": status_choices,
    })


@login_required
@user_passes_test(is_admin)
def booking_detail(request, booking_number):
    booking = BookingSelector.get(booking_number)
    if not booking:
        raise Http404
        
    history = BookingSelector.history(booking)
    
    # Resolve requirements labels dynamically from database
    req_details = []
    requirements_dict = booking.requirements or {}
    for req in booking.service.requirements.filter(is_active=True):
        val = requirements_dict.get(req.field_name)
        if val is not None:
            req_details.append({
                "label": req.label,
                "value": val,
                "is_list": isinstance(val, list),
            })
            
    # Professionals available to be assigned to this service
    available_professionals = ProfessionalProfile.objects.filter(
        services__service=booking.service,
        verification__status="approved"
    ).select_related("user")
    
    status_choices = BookingStatus.choices
    
    return render(request, "dashboard/admin/bookings/detail.html", {
        "booking": booking,
        "history": history,
        "requirements": req_details,
        "available_professionals": available_professionals,
        "status_choices": status_choices,
    })


@login_required
@user_passes_test(is_admin)
def booking_assign_worker(request, booking_number):
    if request.method == "POST":
        worker_id = request.POST.get("worker_id")
        booking = BookingSelector.get(booking_number)
        if not booking:
            raise Http404
            
        if not worker_id:
            messages.error(request, "Please select a professional.")
            return redirect("admin_booking_detail", booking_number=booking_number)
            
        worker = get_object_or_404(User, pk=worker_id, role="professional")
        
        try:
            if booking.status == BookingStatus.WORKER_ASSIGNED:
                # If worker is already assigned, directly override the worker FK to avoid transition state check fail
                booking.worker = worker
                booking.save(update_fields=["worker"])
                BookingStatusHistory.objects.create(
                    booking=booking,
                    status=booking.status,
                    changed_by=request.user,
                    source="admin",
                    note=f"Worker reassigned to {worker.full_name} by administrator."
                )
                messages.success(request, f"Worker successfully reassigned to {worker.full_name}.")
            else:
                BookingService.assign_worker(booking=booking, worker=worker, changed_by=request.user)
                messages.success(request, f"Worker {worker.full_name} successfully assigned to booking.")
        except Exception as e:
            messages.error(request, f"Error assigning worker: {e}")
            
    return redirect("admin_booking_detail", booking_number=booking_number)


@login_required
@user_passes_test(is_admin)
def booking_override_status(request, booking_number):
    if request.method == "POST":
        new_status = request.POST.get("new_status")
        booking = BookingSelector.get(booking_number)
        if not booking:
            raise Http404
            
        try:
            BookingService.change_status(
                booking=booking,
                status=new_status,
                changed_by=request.user,
                source="admin",
                note="Booking status updated by administrator."
            )
            messages.success(request, f"Booking status successfully changed to '{new_status}'.")
        except Exception as e:
            messages.error(request, f"Error overriding status: {e}")
            
    return redirect("admin_booking_detail", booking_number=booking_number)


@login_required
@user_passes_test(is_admin)
def booking_cancel(request, booking_number):
    if request.method == "POST":
        reason = request.POST.get("reason", "Cancelled by administrator.")
        booking = BookingSelector.get(booking_number)
        if not booking:
            raise Http404
            
        try:
            BookingService.cancel(booking=booking, changed_by=request.user, cancelled_reason=reason)
            messages.success(request, "Booking successfully cancelled.")
        except Exception as e:
            messages.error(request, f"Error cancelling booking: {e}")
            
    return redirect("admin_booking_detail", booking_number=booking_number)

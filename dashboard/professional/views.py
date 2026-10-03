from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.core.exceptions import PermissionDenied
from django.http import Http404
from accounts.services.professional_service import ProfessionalService
from verification.services import VerificationService

def _check_professional(user):
    if not hasattr(user, "professional_profile"):
        raise PermissionDenied


@login_required
def professional_dashboard(request):
    verification = None

    if hasattr(request.user, "professional_profile"):
        verification = VerificationService.get_verification(
            request.user.professional_profile
        )
    _check_professional(request.user)
    context = ProfessionalService.get_dashboard_context(
        request.user,

    )
    context["verification"] = verification
    context["tab"] = request.GET.get("tab", "dashboard")
    return render(
        request,
        "dashboard/professional/professional_dashboard.html",
        context,
    )


@login_required
def edit_professional_profile(request):
    _check_professional(request.user)
    profile = ProfessionalService.get_profile(
        request.user,
    )

    if request.method == "POST":
        success, form = ProfessionalService.save_profile(
            request.user,
            request.POST,
        )
        if success:
            messages.success(
                request,
                "Professional profile saved successfully.",
            )
            return redirect(
                "professional_dashboard",
            )
        print(form.errors)  # <-- temporary add
    else:
        form = ProfessionalService.get_form(
            profile,
        )

    return render(
        request,
        "dashboard/professional/edit_profile.html",
        {
            "form": form,
            "profile": profile,
        },
    )


@login_required
def professional_profile(request):
    _check_professional(request.user)
    context = ProfessionalService.get_dashboard_context(
        request.user,
    )
    return render(
        request,
        "dashboard/professional/profile.html",
        context,
    )


@login_required
def professional_booking_detail(request, booking_number):
    _check_professional(request.user)
    from bookings.selectors import BookingSelector
    
    booking = BookingSelector.worker_detail(booking_number, request.user)
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
            
    return render(
        request,
        "dashboard/professional/booking_detail.html",
        {
            "booking": booking,
            "history": history,
            "requirements": req_details,
        }
    )


@login_required
def accept_booking(request, booking_number):
    _check_professional(request.user)
    from bookings.selectors import BookingSelector
    from bookings.models import BookingStatus
    from bookings.services import BookingService
    
    booking = BookingSelector.worker_detail(booking_number, request.user)
    if not booking:
        raise Http404
        
    if booking.status != BookingStatus.PENDING:
        messages.error(request, "This booking cannot be accepted in its current state.")
        return redirect("professional_booking_detail", booking_number=booking_number)
        
    try:
        BookingService.change_status(
            booking=booking,
            status=BookingStatus.WORKER_ASSIGNED,
            changed_by=request.user,
            source="worker",
            note="Worker accepted the booking."
        )
        from notifications.services import NotificationService
        NotificationService.trigger_worker_accepted(booking)
        messages.success(request, "Booking accepted successfully.")
    except Exception as e:
        messages.error(request, str(e))
        
    return redirect("professional_booking_detail", booking_number=booking_number)


@login_required
def reject_booking(request, booking_number):
    _check_professional(request.user)
    from bookings.selectors import BookingSelector
    from bookings.models import BookingStatus, BookingStatusHistory
    
    booking = BookingSelector.worker_detail(booking_number, request.user)
    if not booking:
        raise Http404
        
    if booking.status != BookingStatus.PENDING:
        messages.error(request, "This booking cannot be rejected in its current state.")
        return redirect("professional_booking_detail", booking_number=booking_number)
        
    try:
        BookingStatusHistory.objects.create(
            booking=booking,
            status=booking.status,
            changed_by=request.user,
            source="worker",
            note="Worker rejected the booking."
        )
        booking.worker = None
        booking.save()
        from notifications.services import NotificationService
        NotificationService.trigger_worker_rejected(booking, request.user)
        messages.success(request, "Booking rejected successfully.")
    except Exception as e:
        messages.error(request, str(e))
        
    return redirect("professional_dashboard")


@login_required
def update_booking_status(request, booking_number):
    _check_professional(request.user)
    if request.method != "POST":
        return redirect("professional_booking_detail", booking_number=booking_number)
        
    from bookings.selectors import BookingSelector
    from bookings.models import BookingStatus
    from bookings.services import BookingService
    
    booking = BookingSelector.worker_detail(booking_number, request.user)
    if not booking:
        raise Http404
        
    current_status = booking.status
    
    try:
        if current_status == BookingStatus.WORKER_ASSIGNED:
            BookingService.on_the_way(booking, request.user)
            messages.success(request, "Status updated: On The Way.")
        elif current_status == BookingStatus.ON_THE_WAY:
            BookingService.arrived(booking, request.user)
            messages.success(request, "Status updated: Arrived.")
        elif current_status == BookingStatus.ARRIVED:
            BookingService.started(booking, request.user)
            messages.success(request, "Status updated: Started.")
        elif current_status == BookingStatus.STARTED:
            BookingService.in_progress(booking, request.user)
            messages.success(request, "Status updated: In Progress.")
        elif current_status == BookingStatus.IN_PROGRESS:
            BookingService.complete(booking, request.user)
            messages.success(request, "Status updated: Completed.")
        else:
            messages.error(request, "Cannot update status from current state.")
    except Exception as e:
        messages.error(request, str(e))
        
    return redirect("professional_booking_detail", booking_number=booking_number)
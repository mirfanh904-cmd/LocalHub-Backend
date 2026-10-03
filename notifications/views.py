from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.contrib import messages
from .selectors import NotificationSelector
from .services import NotificationService


@login_required
def notification_list(request):
    notifications_qs = NotificationSelector.user_notifications(request.user)
    paginator = Paginator(notifications_qs, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    
    return render(request, "dashboard/customer/notifications.html", {
        "page_obj": page_obj,
    })


@login_required
def mark_read(request, pk):
    success = NotificationService.mark_as_read(pk, request.user)
    if success:
        messages.success(request, "Notification marked as read.")
    else:
        messages.error(request, "Notification not found.")
    return redirect("notifications:list")


@login_required
def mark_all_read(request):
    NotificationService.mark_all_as_read(request.user)
    messages.success(request, "All notifications marked as read.")
    return redirect("notifications:list")

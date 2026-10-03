from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from services.services import ServiceSelector

from django.contrib import messages
from accounts.services import AddressService
from django.http import Http404
# from accounts.
from .selectors import BookingSelector
from accounts.selectors import AddressSelector
from professionals.selectors import ProfessionalSelector
from .services import BookingService
from .models import BookingStatus
from django.core.paginator import Paginator
from services.services.selectors import PackageSelector,ServiceRequirementSelector
import uuid

@login_required
def checkout(request, slug):
    service = ServiceSelector.get_by_slug(slug)
    rebook = request.session.get("rebook")
    package_slug = request.GET.get("package")
    package = None

    if package_slug:
        package = PackageSelector.detail(package_slug)
    professional_id = request.GET.get("professional")
    professional = None

    if professional_id:
        professional = ProfessionalSelector.detail(professional_id)

    elif rebook and rebook.get("professional_id"):
        professional = ProfessionalSelector.detail(
            rebook["professional_id"]
    )
    context = {
        "service": service,
        "rebook": rebook,
        "package": package,
        "professional": professional,
        "addresses": AddressSelector.user_addresses(
            request.user,),
        "requirements": ServiceRequirementSelector.service(service),
    }
    return render(request, "bookings/checkout.html", context, )




@login_required
def my_bookings(request):

    search = request.GET.get("search")
    status = request.GET.get("status")
    sort = request.GET.get("sort", "newest")
    queryset = BookingSelector.my_bookings(
        customer=request.user,
        search=search,
        status=status,
        sort=sort
    )

    paginator = Paginator(queryset, 10)

    page = request.GET.get("page")

    bookings = paginator.get_page(page)

    return render(request, "bookings/my_bookings.html", {
        "bookings": bookings,
        "search": search,
        "status": status,
        "sort":sort,
    })



@login_required
def cancel_booking(
    request,
    booking_number,
):

    if request.method != "POST":

        raise Http404

    booking = BookingSelector.customer_detail(
        booking_number=booking_number,
        customer=request.user,
    )

    if not booking:

        raise Http404

    if booking.status not in [
        BookingStatus.PENDING,
        BookingStatus.CONFIRMED,
    ]:

        messages.error(
            request,
            "This booking cannot be cancelled.",
        )

        return redirect(
            "bookings:booking_detail",
            booking.booking_number,
        )

    BookingService.cancel(
        booking=booking,
        changed_by=request.user,
        cancelled_reason=request.POST.get(
            "reason",
            "",
        ),
    )

    messages.success(
        request,
        "Booking cancelled successfully.",
    )

    return redirect(
        "bookings:booking_detail",
        booking.booking_number,
    )

@login_required
def booking_detail(request, booking_number):
    booking = BookingSelector.customer_detail(booking_number, request.user)
    history = BookingSelector.history(booking)
    return render(request, "bookings/booking_detail.html", {
        "booking": booking,
        "history": history,
    })

@login_required
def booking_method(request, slug):
    service = ServiceSelector.get_by_slug(slug)
    package_slug = request.GET.get("package")
    package = PackageSelector.detail(package_slug) if package_slug else None
    return render(request, "bookings/booking_method.html", {
        "service": service,
        "package":package,

    })


@login_required
def booking_add_address(request):
    next_url = request.GET.get("next")

    if request.method == "POST":

        success, form = AddressService.create(
            request.user,
            request.POST,
        )

        if success:

            messages.success(
                request,
                "Address added successfully.",
            )

            next_url = request.POST.get("next")

            if next_url:
                return redirect(next_url)

            return redirect(
                "bookings:checkout",
            )

    else:

        form = AddressService.get_form()

    return render(
        request,
        "bookings/add_address.html",
        {
            "form": form,
            "next": next_url,
        },
    )


@login_required
def create_booking(request, slug):
    if request.method != "POST":
        request.session.pop("rebook", None)
        return redirect(
            "bookings:checkout",
            slug=slug,
        )

    booking = BookingService.create_booking(
        request=request,
        slug=slug,
    )

    messages.success(
        request,
        "Booking created successfully.",
    )

    return redirect(
        "bookings:booking_success",
        booking_number=booking.booking_number,

    )


@login_required
def booking_success(
        request,
        booking_number,
):
    booking = BookingSelector.customer_detail(
        booking_number=booking_number,
        customer=request.user,
    )

    if not booking:
        raise Http404

    return render(
        request,
        "bookings/booking_success.html",
        {
            "booking": booking,
        },
    )

@login_required
def rebook(request, booking_number):

    booking = BookingSelector.customer_detail(
        booking_number,
        request.user,
    )

    if not booking:
        messages.error(request, "Booking not found.")
        return redirect("bookings:my_bookings")

    request.session["rebook"] = {
        "professional_id": str(booking.worker_id) if booking.worker_id else None,
        "address_id": booking.address_id,
        "customer_note": booking.customer_note or "",
    }

    return redirect(
        "bookings:booking_method",
        slug=booking.service.slug,
    )


from django.views.decorators.http import require_POST

@login_required
@require_POST
def submit_review(request, booking_number):
    from .services import ReviewService
    from .selectors import BookingSelector
    
    booking = BookingSelector.customer_detail(booking_number, request.user)
    if not booking:
        raise Http404
        
    rating = request.POST.get("rating")
    comment = request.POST.get("comment", "")
    
    try:
        ReviewService.create_review(
            booking=booking,
            customer=request.user,
            rating=rating,
            comment=comment
        )
        messages.success(request, "Thank you! Your review has been submitted.")
    except Exception as e:
        messages.error(request, str(e))
        
    return redirect("bookings:booking_detail", booking_number=booking_number)

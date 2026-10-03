from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import Http404
from services.services import ServiceSelector
from professionals.selectors import ProfessionalSelector
from django.core.paginator import Paginator
from services.services.selectors import PackageSelector
from accounts.selectors import FavouriteSelector


@login_required
def professional_list(request, service_slug):
    package_slug = request.GET.get("package")
    package = PackageSelector.detail(package_slug) if package_slug else None
    service = ServiceSelector.get_by_slug(service_slug)
    if not service:
        raise Http404
    return render(
        request,
        "professionals/professional_list/professional_list.html",
        {
            "package":package,
            "service": service,
            "professionals": ProfessionalSelector.by_service(service),
        },
    )

@login_required
def professional_detail(request, service_slug, professional_id):
    package_slug = request.GET.get("package")
    package = PackageSelector.detail(package_slug) if package_slug else None
    service = ServiceSelector.get_by_slug(
        service_slug,
    )

    professional = ProfessionalSelector.detail(
        professional_id,
    )

    if not service or not professional:
        raise Http404

    is_favourited = False
    if request.user.is_authenticated:
        is_favourited = FavouriteSelector.is_professional_favourited(request.user, professional)

    context = {
        "service": service,
        "package": package,
        "professional": professional,
        "is_favourited": is_favourited,
    }

    return render(
        request,
        "professionals/professional_detail.html",
        context,
    )
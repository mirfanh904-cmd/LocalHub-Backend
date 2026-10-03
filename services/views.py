from django.shortcuts import render
from django.http import Http404
from .services import ServiceGroupSelector, CategorySelector, ServiceSelector
from services.services.selectors import PackageSelector, ServiceFAQSelector
from accounts.selectors import FavouriteSelector


def service_group_list(request):
    context = {
        "service_groups": ServiceGroupSelector.all()
    }
    return render(
        request,
        "services/service_group_list.html",
        context,
    )


def service_group_detail(request, slug):
    service_group = ServiceGroupSelector.by_slug(slug)
    context = {
        "service_group": service_group
    }
    return render(
        request,
        "services/service_group_detail.html",
        context, )


def explore_services(request):
    group = request.GET.get("group")
    category = request.GET.get("category")
    if group:
        categories = CategorySelector.by_service_group(group)
    else:
        categories = CategorySelector.all()
    context = {

        "service_groups": ServiceGroupSelector.all(),
        "categories": categories,

        "selected_group": group,

        "selected_category": category,

        "services": ServiceSelector.filter(
            group=group,
            category=category,
        ),
        # Later
        # "categories": ...
        # "services": ...
        # "trending_searches": ...
    }

    return render(
        request,
        "services/explore_services.html",
        context,
    )


def service_group_detail(request, slug):
    service_group = ServiceGroupSelector.by_slug(slug)
    context = {
        "service_group": service_group
    }
    return render(
        request,
        "services/service_group_detail.html",
        context,
    )


def category_list(request):
    categories = CategorySelector.all()

    return render(
        request,
        "services/category_list.html",
        {
            "categories": categories,
        },
    )


def category_detail(request, slug):
    category = CategorySelector.by_slug(slug)

    return render(
        request,
        "services/category_detail.html",
        {
            "category": category,
        },
    )


def service_detail(request, slug):
    service = ServiceSelector.get_by_slug(slug)
    if not service:
        raise Http404
    packages = PackageSelector.service(service)
    faqs = ServiceFAQSelector.service(service)

    is_favourited = False
    if request.user.is_authenticated:
        is_favourited = FavouriteSelector.is_service_favourited(request.user, service)

    context = {
        "service": service,
        "related_services": ServiceSelector.related(service),
        "packages": packages,
        "faqs": faqs,
        "is_favourited": is_favourited,
    }

    return render(
        request,
        "services/service_details/service_detail.html",
        context,
    )

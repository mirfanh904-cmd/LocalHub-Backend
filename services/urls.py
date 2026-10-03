from django.urls import path
from .views import (service_group_detail, service_group_list, explore_services,
                    category_list, category_detail,service_detail)

app_name = "services"

urlpatterns = [
    path("service_list/", service_group_list, name="service_group_list",),
    path("", explore_services,name="explore_services",),
path(
    "categories/",
    category_list,
    name="category_list",
),

path(
    "categories/<slug:slug>/",
    category_detail,
    name="category_detail",
),
path(
    "<slug:slug>/",
    service_detail,
    name="service_detail",
),
]
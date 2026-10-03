from django.urls import path
from .views import (CategoryListAPIView,CategoryDetailAPIView,)
urlpatterns = [
    path(
        "categories/",
        CategoryListAPIView.as_view(),
        name="api_categories",
    ),

    path(
        "categories/<slug:slug>/",
        CategoryDetailAPIView.as_view(),
        name="api_category_detail",
    ),
    ]
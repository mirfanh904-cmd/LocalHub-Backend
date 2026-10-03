from django.urls import path
from . import views

app_name = "api_v1_notifications"

urlpatterns = [
    path("", views.NotificationListAPIView.as_view(), name="list"),
    path("unread-count/", views.UnreadNotificationCountAPIView.as_view(), name="unread_count"),
    path("<int:pk>/read/", views.MarkNotificationReadAPIView.as_view(), name="mark_read"),
    path("read-all/", views.MarkAllNotificationsReadAPIView.as_view(), name="mark_all_read"),
]

def unread_notifications_count(request):
    if request.user.is_authenticated:
        from notifications.selectors import NotificationSelector
        return {
            "unread_notifications_count": NotificationSelector.unread_count(request.user)
        }
    return {
        "unread_notifications_count": 0
    }

from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsTaskCustomerOrReadOnly(BasePermission):
    """
    Allows read permissions to authenticated users, but write/selection/cancellation
    actions only to the customer who created the task (or admin).
    """

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj.customer == request.user or request.user.is_staff or getattr(request.user, "role", None) == "ADMIN"


class IsProfessionalUser(BasePermission):
    """
    Allows access only to authenticated users with role='PROFESSIONAL'.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return getattr(request.user, "role", None) == "PROFESSIONAL" or request.user.is_staff or getattr(request.user, "role", None) == "ADMIN"


class IsAssignedProfessional(BasePermission):
    """
    Allows state change actions (start/complete) only to the assigned professional of the task.
    """

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff or getattr(request.user, "role", None) == "ADMIN":
            return True
        return obj.assigned_professional == request.user


class IsApplicationOwnerOrCustomer(BasePermission):
    """
    Application detail can be seen by the applicant or the task customer.
    Withdraw action only allowed to the applicant.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return obj.professional == request.user or obj.task.customer == request.user or request.user.is_staff
        return obj.professional == request.user or request.user.is_staff

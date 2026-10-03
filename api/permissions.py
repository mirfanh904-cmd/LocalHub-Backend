from rest_framework import permissions


class IsCustomer(permissions.BasePermission):
    """
    Allows access to all authenticated users for customer operations (browsing, booking, addresses, etc.).
    Every user starts as a customer and retains customer capabilities even after becoming a professional.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            getattr(request.user, "role", None) in ("CUSTOMER", "PROFESSIONAL", "ADMIN")
        )


class IsProfessional(permissions.BasePermission):
    """
    Allows access to any authenticated user applying for or holding a professional profile.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated
        )


class IsVerifiedWorker(permissions.BasePermission):
    """
    Allows access only to authenticated professionals with an approved KYC verification.
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        profile = getattr(request.user, "professional_profile", None)
        if not profile:
            return False
        from verification.models import ProfessionalVerification, VerificationStatus
        return ProfessionalVerification.objects.filter(
            professional=profile,
            status=VerificationStatus.APPROVED
        ).exists()


class IsAdmin(permissions.BasePermission):
    """
    Allows access only to admin or superuser accounts.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            (
                getattr(request.user, "role", None) == "ADMIN" or
                request.user.is_superuser or
                request.user.is_staff
            )
        )


class IsBookingOwner(permissions.BasePermission):
    """
    Object-level permission to only allow customer or assigned worker of a booking to access it.
    """
    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated):
            return False
        if getattr(request.user, "role", None) == "ADMIN" or request.user.is_superuser:
            return True
        customer_user = getattr(obj, "customer", None)
        worker_user = getattr(obj, "worker", None)
        return request.user in (customer_user, worker_user)


class IsVerificationOwnerOrAdmin(permissions.BasePermission):
    """
    Object-level permission for Verification & Verification Documents.
    Allows access only to the professional who owns the verification or an admin.
    """
    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated):
            return False
        if getattr(request.user, "role", None) == "ADMIN" or request.user.is_superuser or request.user.is_staff:
            return True
        # obj might be ProfessionalVerification or ProfessionalVerificationDocument
        if hasattr(obj, "professional"):
            return obj.professional.user_id == request.user.id
        if hasattr(obj, "verification"):
            return obj.verification.professional.user_id == request.user.id
        return False


class IsComplaintOwnerOrAdmin(permissions.BasePermission):
    """
    Object-level permission for Complaints.
    Allows customer who filed it or admin to access.
    """
    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated):
            return False
        if getattr(request.user, "role", None) == "ADMIN" or request.user.is_superuser or request.user.is_staff:
            return True
        return obj.customer_id == request.user.id

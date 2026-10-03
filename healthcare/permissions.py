from rest_framework import permissions


class IsPatientOrAssignedHealthcareProvider(permissions.BasePermission):
    """
    Object-level permission allowing:
    - Customer / Patient: Access to their own medical profile, emergency contacts, and appointments.
    - Assigned Healthcare Worker: Access to appointment details and patient notes for their assigned jobs.
    - Platform Admin: Full management access for safety and compliance.
    - Others: Denied (403 Forbidden).
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if getattr(user, "is_staff", False) or getattr(user, "role", "") == "ADMIN":
            return True

        # HealthcareAppointment
        if hasattr(obj, "booking"):
            booking = obj.booking
            return booking.customer == user or booking.worker == user

        # PatientMedicalProfile
        if hasattr(obj, "user"):
            return obj.user == user

        # EmergencyContact
        if hasattr(obj, "patient"):
            return obj.patient == user

        # MedicalVisitNote
        if hasattr(obj, "appointment"):
            booking = obj.appointment.booking
            if request.method in permissions.SAFE_METHODS:
                return booking.customer == user or booking.worker == user
            return booking.worker == user

        # PatientInstruction
        if hasattr(obj, "appointment"):
            booking = obj.appointment.booking
            return booking.customer == user or booking.worker == user

        return False


class IsAssignedHealthcareWorker(permissions.BasePermission):
    """
    Permission requiring that the user is the assigned professional on the booking.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if getattr(user, "is_staff", False) or getattr(user, "role", "") == "ADMIN":
            return True

        if hasattr(obj, "booking"):
            return obj.booking.worker == user
        if hasattr(obj, "appointment"):
            return obj.appointment.booking.worker == user
        return False

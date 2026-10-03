from accounts.forms import ProfessionalProfileForm
from accounts.models import ProfessionalProfile


class ProfessionalService:

    @staticmethod
    def has_profile(user):
        return ProfessionalProfile.objects.filter(
            user=user,
        ).exists()

    @staticmethod
    def get_profile(user):
        return ProfessionalProfile.objects.filter(
            user=user,
        ).first()

    @staticmethod
    def get_form(profile=None):
        return ProfessionalProfileForm(
            instance=profile,
        )

    @staticmethod
    def save_profile(user, data):

        profile = ProfessionalService.get_profile(user)

        form = ProfessionalProfileForm(
            data,
            instance=profile,
        )

        if form.is_valid():

            professional = form.save(
                commit=False,
            )

            professional.user = user
            professional.is_profile_completed = True

            professional.save()
            form.save_m2m()

            return True, form

        return False, form

    @staticmethod
    def get_dashboard_context(user):
        from bookings.selectors import BookingSelector
        profile = ProfessionalService.get_profile(user)

        return {
            "profile": profile,
            "skills": profile.skills.all() if profile else [],
            "languages": profile.languages.all() if profile else [],
            "today_jobs_count": BookingSelector.worker_today_jobs(user).count(),
            "upcoming_jobs_count": BookingSelector.worker_upcoming_jobs(user).count(),
            "completed_jobs_count": BookingSelector.worker_completed_jobs(user).count(),
            "total_earnings": BookingSelector.worker_earnings(user),
            "monthly_earnings": BookingSelector.worker_monthly_earnings(user),
            "new_requests": BookingSelector.worker_new_requests(user),
            "bookings": BookingSelector.worker_bookings(user),
            "today_jobs": BookingSelector.worker_today_jobs(user),
            "upcoming_jobs": BookingSelector.worker_upcoming_jobs(user),
            "completed_jobs": BookingSelector.worker_completed_jobs(user),
            "cancelled_jobs": BookingSelector.worker_cancelled_jobs(user),
        }
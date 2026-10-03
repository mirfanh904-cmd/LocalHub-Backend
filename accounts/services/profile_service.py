from accounts.models import User
from django.contrib.auth import authenticate, login, logout
from accounts.models import UserProfile
from accounts.forms import ProfileForm
from django.contrib.auth import update_session_auth_hash


class ProfileService:
    @staticmethod
    def get_profile_context(user):
        profile, created = UserProfile.objects.get_or_create(
            user=user
        )

        completion = ProfileService.calculate_profile_completion(
            profile,
            user, )
        return {
            "user": user,
            "profile": user.profile,
            "profile_completion": completion,

        }

    @staticmethod
    def get_profile_form(user):
        profile, created = UserProfile.objects.get_or_create(
            user=user
        )

        return ProfileForm(
            instance=profile,
            user=user,

        )

    @staticmethod
    def update_profile(user, request):
        profile, created = UserProfile.objects.get_or_create(
            user=user
        )
        form = ProfileForm(
            request.POST,
            request.FILES,
            instance=profile,
            user=user,
        )
        if form.is_valid():
            user.first_name = form.cleaned_data["first_name"]
            user.last_name = form.cleaned_data["last_name"]
            user.save()
            form.save()
            return True, form
        return False, form

    @staticmethod
    def calculate_profile_completion(profile, user):
        fields = [
            user.first_name,
            user.last_name,

            profile.profile_picture,
            profile.display_name,
            profile.date_of_birth,
            profile.gender,
            profile.occupation,
            profile.bio,
            profile.city,
            profile.preferred_language, ]
        completed = sum(1 for field in fields if field)
        return int((completed / len(fields)) * 100)

    # password change
    @staticmethod
    def change_password(request, form):
        form.save()

        update_session_auth_hash(
            request,
            form.user,
        )

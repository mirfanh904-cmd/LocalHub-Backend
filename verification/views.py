from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect, get_object_or_404
from verification.services import VerificationService, ProfessionalVerificationDocument, ProfessionalVerification
from .forms import VerificationDocumentForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from .models import ProfessionalVerification

@login_required
def verification_detail(request):
    professional = getattr(request.user, "professional_profile", None)
    if not professional:
        return redirect("home")

    verification = VerificationService.get_verification(professional)
    return render(request, "verification/detail.html", {"verification": verification})



@login_required
def upload_document(request):
    professional = getattr(request.user, "professional_profile", None)
    if not professional:
        return redirect("home")

    verification = VerificationService.get_verification(professional)

    if request.method == "POST":
        form = VerificationDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            VerificationService.upload_document(verification, **form.cleaned_data)
            return redirect("verification:detail")
    else:
        form = VerificationDocumentForm()

    return render(request, "verification/upload_document.html", {"form": form})


@login_required
def delete_document(request, pk):
    document = get_object_or_404(ProfessionalVerificationDocument, pk=pk)
    VerificationService.delete_document(document)
    return redirect("verification:detail")

# ------------------------ admin side ---------------------

@staff_member_required
def verification_list(request):
    verifications = ProfessionalVerification.objects.all().select_related("professional__user")
    return render(request, "verification/list.html", {"verifications": verifications})

@staff_member_required
def verification_admin_detail(request, pk):
    verification = get_object_or_404(ProfessionalVerification.objects.select_related("professional__user"), pk=pk)
    documents = VerificationService.get_documents(verification)
    return render(request, "verification/admin_detail.html", {"verification": verification, "documents": documents})

@staff_member_required
def approve_verification(request, pk):

    verification = get_object_or_404(
        ProfessionalVerification,
        pk=pk,
    )

    try:

        VerificationService.approve_verification(
            verification,
            request.user,
        )

        messages.success(
            request,
            "Verification approved successfully.",
        )

    except ValidationError as e:

        messages.error(
            request,
            e.message,
        )

    return redirect(
        "verification:admin_detail",
        pk=pk,
    )
@staff_member_required
def reject_verification(request, pk):
    verification = get_object_or_404(ProfessionalVerification, pk=pk)

    if request.method == "POST":
        reason = request.POST.get("reason")
        try:

            VerificationService.reject_verification(
                verification,
                request.user,
                reason,
            )

            messages.success(
                request,
                "Verification rejected successfully.",
            )

        except ValidationError as e:

            messages.error(
                request,
                e.message,
            )

        return redirect(
            "verification:admin_detail",
            pk=pk,
        )

    return render(request, "verification/reject.html", {"verification": verification})

@staff_member_required
def mark_under_review(request, pk):

    verification = get_object_or_404(
        ProfessionalVerification,
        pk=pk,
    )

    try:

        VerificationService.mark_under_review(
            verification,
            request.user,
        )

        messages.success(
            request,
            "Verification moved to under review.",
        )

    except ValidationError as e:

        messages.error(
            request,
            e.message,
        )

    return redirect(
        "verification:admin_detail",
        pk=pk,
    )
@staff_member_required
def suspend_verification(request, pk):
    verification = get_object_or_404(ProfessionalVerification, pk=pk)

    if request.method == "POST":
        reason = request.POST.get("reason")
        try:

            VerificationService.suspend_verification(
                verification,
                request.user,
                reason,
            )

            messages.success(
                request,
                "Verification suspended.",
            )

        except ValidationError as e:

            messages.error(
                request,
                e.message,
            )

        return redirect(
            "verification:admin_detail",
            pk=pk,
        )
    return render(request, "verification/suspend.html", {"verification": verification})

@login_required
@require_POST
def submit_verification(request, pk):

    verification = get_object_or_404(
        ProfessionalVerification,
        pk=pk,
        professional=request.user.professional_profile,
    )

    try:
        VerificationService.submit_for_review(verification)

        messages.success(
            request,
            "Your verification request has been submitted successfully."
        )

    except ValidationError as e:

        messages.error(
            request,
            e.message
        )

    return redirect(
        "verification:detail",

    )
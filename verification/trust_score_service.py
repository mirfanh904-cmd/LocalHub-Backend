from decimal import Decimal
from django.db.models import Avg, Count
from verification.models import ProfessionalVerification, VerificationStatus
from bookings.models import Booking, BookingStatus, Review


class TrustScoreService:
    """
    Deterministic Trust Score calculation service for professionals.
    Combines:
    - Identity & Document Verification (+25 points)
    - Rating & Review Signal (up to +15 points, or -10 points if low)
    - Experience / Completed Bookings (+10 to +15 points)
    - Complaint & Disciplinary Deductions (-15 points per upheld/active complaint)
    Clamped strictly between 0 and 100.
    """

    BASE_SCORE = 50

    @classmethod
    def calculate_score_for_profile(cls, profile):
        """
        Calculates the trust score and returns a comprehensive breakdown dictionary.
        """
        breakdown = {
            "base_score": cls.BASE_SCORE,
            "verification_points": 0,
            "ratings_points": 0,
            "bookings_points": 0,
            "complaint_deductions": 0,
            "total_score": cls.BASE_SCORE,
            "tier": "Good",
            "signals": [],
        }

        # 1. Verification Signal (+25 points)
        verification = getattr(profile, "verification", None)
        is_verified = bool(verification and verification.status == VerificationStatus.APPROVED)
        if is_verified:
            breakdown["verification_points"] = 25
            breakdown["signals"].append({
                "name": "Identity & Background Verification",
                "status": "passed",
                "points": 25,
                "description": "Government-issued KYC documents approved and verified by admin."
            })
        else:
            breakdown["signals"].append({
                "name": "Identity & Background Verification",
                "status": "pending" if verification and verification.status in [VerificationStatus.PENDING, VerificationStatus.UNDER_REVIEW] else "unverified",
                "points": 0,
                "description": "KYC verification not completed or not approved."
            })

        # 2. Rating & Review Signal
        avg_rating = float(profile.average_rating or 0.0)
        reviews_count = int(profile.reviews_count or 0)

        if reviews_count >= 5 and avg_rating >= 4.5:
            breakdown["ratings_points"] = 15
            breakdown["signals"].append({
                "name": "High Customer Satisfaction",
                "status": "excellent",
                "points": 15,
                "description": f"Outstanding rating of {avg_rating:.2f} stars across {reviews_count} verified customer reviews."
            })
        elif reviews_count >= 3 and avg_rating >= 4.0:
            breakdown["ratings_points"] = 10
            breakdown["signals"].append({
                "name": "Consistent Quality",
                "status": "good",
                "points": 10,
                "description": f"Solid rating of {avg_rating:.2f} stars across {reviews_count} reviews."
            })
        elif reviews_count >= 3 and avg_rating < 3.5:
            breakdown["ratings_points"] = -10
            breakdown["signals"].append({
                "name": "Low Rating Penalty",
                "status": "warning",
                "points": -10,
                "description": f"Rating is currently below standard ({avg_rating:.2f} stars)."
            })
        else:
            breakdown["ratings_points"] = 0
            breakdown["signals"].append({
                "name": "Customer Feedback Volume",
                "status": "building",
                "points": 0,
                "description": f"{reviews_count} customer reviews logged so far."
            })

        # 3. Completed Bookings Volume
        completed_bookings_count = Booking.objects.filter(
            worker=profile.user,
            status=BookingStatus.COMPLETED
        ).count()

        if completed_bookings_count >= 25:
            breakdown["bookings_points"] = 15
            breakdown["signals"].append({
                "name": "High Marketplace Experience",
                "status": "veteran",
                "points": 15,
                "description": f"Completed {completed_bookings_count} bookings with high reliability."
            })
        elif completed_bookings_count >= 10:
            breakdown["bookings_points"] = 10
            breakdown["signals"].append({
                "name": "Established Track Record",
                "status": "active",
                "points": 10,
                "description": f"Completed {completed_bookings_count} successful jobs."
            })
        elif completed_bookings_count >= 1:
            breakdown["bookings_points"] = 5
            breakdown["signals"].append({
                "name": "Started Fulfilling Bookings",
                "status": "emerging",
                "points": 5,
                "description": f"Successfully completed {completed_bookings_count} jobs on LocalHub."
            })
        else:
            breakdown["bookings_points"] = 0
            breakdown["signals"].append({
                "name": "New Professional",
                "status": "new",
                "points": 0,
                "description": "No completed bookings yet."
            })

        # 4. Complaints & Disciplinary Deductions
        from bookings.models import Complaint, ComplaintStatus
        active_complaints_count = Complaint.objects.filter(
            professional=profile.user,
            status__in=[ComplaintStatus.PENDING, ComplaintStatus.UNDER_INVESTIGATION, ComplaintStatus.RESOLVED]
        ).exclude(status=ComplaintStatus.REJECTED).count()

        if active_complaints_count > 0:
            deduction = -15 * active_complaints_count
            breakdown["complaint_deductions"] = deduction
            breakdown["signals"].append({
                "name": "Complaints & Disciplinary Record",
                "status": "alert",
                "points": deduction,
                "description": f"{active_complaints_count} complaint(s) logged against professional."
            })

        # Final total calculation and clamping
        raw_total = (
            cls.BASE_SCORE +
            breakdown["verification_points"] +
            breakdown["ratings_points"] +
            breakdown["bookings_points"] +
            breakdown["complaint_deductions"]
        )
        total_score = max(0, min(100, raw_total))
        breakdown["total_score"] = total_score

        # Determine Tier
        if total_score >= 85:
            breakdown["tier"] = "Elite"
        elif total_score >= 70:
            breakdown["tier"] = "Trusted"
        elif total_score >= 50:
            breakdown["tier"] = "Good"
        else:
            breakdown["tier"] = "Needs Improvement"

        return breakdown

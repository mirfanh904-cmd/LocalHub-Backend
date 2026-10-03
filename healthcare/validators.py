from datetime import date
from django.core.exceptions import ValidationError


class HealthcareValidator:

    @staticmethod
    def validate_date_of_birth(dob):
        if dob and dob > date.today():
            raise ValidationError("Date of birth cannot be in the future.")

    @staticmethod
    def validate_vitals(systolic_bp=None, diastolic_bp=None, heart_rate_bpm=None, temperature_f=None, oxygen_saturation=None):
        if systolic_bp is not None and not (50 <= systolic_bp <= 300):
            raise ValidationError("Systolic blood pressure must be between 50 and 300 mmHg.")
        
        if diastolic_bp is not None and not (30 <= diastolic_bp <= 200):
            raise ValidationError("Diastolic blood pressure must be between 30 and 200 mmHg.")

        if systolic_bp is not None and diastolic_bp is not None and diastolic_bp >= systolic_bp:
            raise ValidationError("Diastolic blood pressure must be less than systolic blood pressure.")

        if heart_rate_bpm is not None and not (30 <= heart_rate_bpm <= 250):
            raise ValidationError("Heart rate must be between 30 and 250 BPM.")

        if temperature_f is not None and not (85.0 <= float(temperature_f) <= 115.0):
            raise ValidationError("Temperature must be between 85.0°F and 115.0°F.")

        if oxygen_saturation is not None and not (50 <= oxygen_saturation <= 100):
            raise ValidationError("Oxygen saturation (SpO2) must be between 50% and 100%.")

    @staticmethod
    def validate_registration_number(reg_num):
        if not reg_num or len(str(reg_num).strip()) < 3:
            raise ValidationError("Medical / Nursing Council registration number is required (min 3 characters).")

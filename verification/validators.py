import os
from django.core.exceptions import ValidationError

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}

def validate_verification_document(file_obj):
    """
    Validates verification document size, extension, and binary header magic bytes.
    Allowed formats: PDF, JPEG, PNG. Maximum size: 5MB.
    """
    if not file_obj:
        raise ValidationError("No file provided.")

    # 1. File size check
    if file_obj.size > MAX_FILE_SIZE:
        raise ValidationError(f"File size exceeds maximum allowed limit of 5MB. Got {file_obj.size / (1024 * 1024):.2f}MB.")

    # 2. Extension check
    ext = os.path.splitext(file_obj.name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(f"Unsupported file extension '{ext}'. Allowed extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}.")

    # 3. Magic bytes / header check
    try:
        # Read first 16 bytes for magic signature
        initial_pos = file_obj.tell() if hasattr(file_obj, 'tell') else 0
        header = file_obj.read(16)
        if hasattr(file_obj, 'seek'):
            file_obj.seek(initial_pos)

        if ext == ".pdf":
            if not header.startswith(b"%PDF"):
                raise ValidationError("Invalid PDF file: corrupted or invalid header.")
        elif ext in [".jpg", ".jpeg"]:
            if not header.startswith(b"\xff\xd8\xff"):
                raise ValidationError("Invalid JPEG image file: invalid magic header.")
        elif ext == ".png":
            if not header.startswith(b"\x89PNG\r\n\x1a\n"):
                raise ValidationError("Invalid PNG image file: invalid magic header.")
    except Exception as e:
        if isinstance(e, ValidationError):
            raise
        raise ValidationError(f"Failed to validate file contents: {str(e)}")

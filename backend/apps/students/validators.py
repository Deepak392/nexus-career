from pathlib import Path

from rest_framework import serializers

MAX_RESUME_SIZE = 5 * 1024 * 1024


def validate_pdf_resume(upload):
    """Validate a resume by extension, declared MIME type, size and PDF signature."""
    if upload.size > MAX_RESUME_SIZE:
        raise serializers.ValidationError("Resume must be 5 MB or smaller.")

    if Path(upload.name).suffix.lower() != ".pdf":
        raise serializers.ValidationError("Only PDF resumes are accepted.")

    if upload.content_type != "application/pdf":
        raise serializers.ValidationError("Resume must have application/pdf content type.")

    current_position = upload.tell()
    signature = upload.read(5)
    upload.seek(current_position)

    if signature != b"%PDF-":
        raise serializers.ValidationError("The uploaded file does not contain a valid PDF signature.")

    return upload

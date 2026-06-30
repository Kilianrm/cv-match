from dataclasses import dataclass


ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt"}
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    reason: str = ""


def validate_cv_file(filename: str | None, content_type: str | None, content: bytes) -> ValidationResult:
    if not filename:
        return ValidationResult(False, "Filename is required")

    normalized = filename.lower().strip()
    ext = "." + normalized.rsplit(".", 1)[-1] if "." in normalized else ""

    if ext not in ALLOWED_EXTENSIONS:
        return ValidationResult(False, "Unsupported file extension")

    if content_type and content_type not in ALLOWED_CONTENT_TYPES:
        return ValidationResult(False, "Unsupported content type")

    if len(content) == 0:
        return ValidationResult(False, "File is empty")

    if len(content) > MAX_FILE_SIZE_BYTES:
        return ValidationResult(False, "File exceeds maximum allowed size")

    if ext == ".pdf" and not content.startswith(b"%PDF"):
        return ValidationResult(False, "Invalid PDF signature")

    if ext == ".docx" and not content.startswith(b"PK"):
        return ValidationResult(False, "Invalid DOCX signature")

    if ext == ".doc" and content.startswith(b"PK"):
        return ValidationResult(False, "DOC extension does not match DOC binary format")

    # Lightweight CV heuristic on plain text to avoid rejecting binary formats.
    if ext == ".txt":
        text_sample = content[:8192].decode("utf-8", errors="ignore").lower()
        keyword_hits = sum(
            1
            for keyword in ("curriculum", "resume", "experience", "education", "skills")
            if keyword in text_sample
        )
        if keyword_hits < 1:
            return ValidationResult(False, "Text file content does not look like a CV")

    return ValidationResult(True)

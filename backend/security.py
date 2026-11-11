import base64
import hashlib
import os

from cryptography.fernet import Fernet


_DEVELOPMENT_KEY = base64.urlsafe_b64encode(
    hashlib.sha256(
        b"ReportForge development-only key; configure REPORTFORGE_SECRET_KEY in production"
    ).digest()
).decode()


def load_fernet() -> Fernet:
    key = os.getenv("REPORTFORGE_SECRET_KEY")
    if not key:
        environment = os.getenv("REPORTFORGE_ENV", "production").strip().lower()
        if environment != "development":
            raise RuntimeError(
                "REPORTFORGE_SECRET_KEY is required unless REPORTFORGE_ENV=development"
            )
        key = _DEVELOPMENT_KEY

    try:
        return Fernet(key.encode("ascii"))
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise RuntimeError(
            "REPORTFORGE_SECRET_KEY must be a valid URL-safe base64 Fernet key"
        ) from exc

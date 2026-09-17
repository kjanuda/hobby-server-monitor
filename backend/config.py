import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(ENV_FILE)


BOOTSTRAP_ADMIN_EMAIL = os.getenv(
    "BOOTSTRAP_ADMIN_EMAIL",
    "",
).strip().lower()


GOOGLE_CLIENT_ID = os.getenv(
    "GOOGLE_CLIENT_ID",
    "",
).strip()

GOOGLE_CLIENT_SECRET = os.getenv(
    "GOOGLE_CLIENT_SECRET",
    "",
).strip()

GOOGLE_REDIRECT_URI = os.getenv(
    "GOOGLE_REDIRECT_URI",
    "http://localhost:8000/api/auth/google/callback",
).strip()


# OAuth endpoints

GOOGLE_AUTHORIZATION_ENDPOINT = (
    "https://accounts.google.com/o/oauth2/v2/auth"
)

GOOGLE_TOKEN_ENDPOINT = (
    "https://oauth2.googleapis.com/token"
)

GOOGLE_USERINFO_ENDPOINT = (
    "https://openidconnect.googleapis.com/v1/userinfo"
)


# Session configuration

SESSION_COOKIE_NAME = os.getenv(
    "SESSION_COOKIE_NAME",
    "hsm_session",
).strip()

SESSION_TTL_SECONDS = int(
    os.getenv(
        "SESSION_TTL_SECONDS",
        "28800",
    )
)

SESSION_COOKIE_SECURE = (
    os.getenv(
        "SESSION_COOKIE_SECURE",
        "false",
    )
    .strip()
    .lower()
    == "true"
)

CSRF_COOKIE_NAME = os.getenv(
    "CSRF_COOKIE_NAME",
    "hsm_csrf",
).strip()


# Metrics configuration

METRICS_INTERVAL_SECONDS = int(
    os.getenv(
        "METRICS_INTERVAL_SECONDS",
        "10",
    )
)

METRICS_RETENTION_HOURS = int(
    os.getenv(
        "METRICS_RETENTION_HOURS",
        "48",
    )
)

METRICS_DB_PATH = os.getenv(
    "METRICS_DB_PATH",
    "backend/data/metrics.csv",
).strip()

DISK_METRICS_INTERVAL_SECONDS = int(
    os.getenv(
        "DISK_METRICS_INTERVAL_SECONDS",
        "60",
    )
)
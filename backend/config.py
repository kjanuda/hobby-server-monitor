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
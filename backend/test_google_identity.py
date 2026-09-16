from services.user_service import (
    GoogleIdentityError,
    UserService,
)

service = UserService()

profile = {
    "sub": "fake-google-sub-for-test",
    "email": "not-invited@example.com",
    "email_verified": True,
    "name": "Not Invited User",
}

try:
    service.authenticate_google_identity(profile)

except GoogleIdentityError as exc:
    print(f"PASS: {exc}")

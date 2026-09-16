from services.user_service import (
    GoogleIdentityError,
    UserService,
)


class FakeRepository:
    def get_user_by_email(self, email):
        return {
            "id": 99,
            "email": email,
            "name": "Revoked User",
            "google_sub": None,
            "role": "container_user",
            "invited": 1,
            "active": 0,
        }

    def get_user_by_google_sub(self, google_sub):
        return None


service = UserService()
service.repository = FakeRepository()

profile = {
    "sub": "fake-revoked-google-sub",
    "email": "revoked@example.com",
    "email_verified": True,
    "name": "Revoked User",
}

try:
    service.authenticate_google_identity(profile)

except GoogleIdentityError as exc:
    print(f"PASS: {exc}")

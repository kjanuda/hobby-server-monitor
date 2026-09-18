from services.session_service import SessionService
from test_support import get_active_user


service = SessionService()

admin = get_active_user("admin")

assert admin is not None

token = None


try:
    print("1. Create admin session")

    token = service.create_session(
        admin["id"]
    )

    user = service.get_user_from_token(
        token
    )

    assert user is not None
    assert user["id"] == admin["id"]
    assert user["role"] == "admin"

    print(
        "PASS: session created and "
        "resolved correctly"
    )


finally:
    if token is not None:
        service.delete_session(token)


print("\n2. Verify logout")

user_after_logout = (
    service.get_user_from_token(token)
)

assert user_after_logout is None

print(
    "PASS: deleted session "
    "is no longer valid"
)

print(
    "\nPASS: session create, "
    "lookup and delete"
)

from services.session_service import SessionService


service = SessionService()

print("Creating session for admin user 2...")

token = service.create_session(user_id=2)

user = service.get_user_from_token(token)

print("Session lookup:")
print(user)

assert user is not None
assert user["id"] == 2
assert user["role"] == "admin"

service.delete_session(token)

user_after_logout = service.get_user_from_token(token)

assert user_after_logout is None

print("PASS: session create, lookup and delete")
from services.oauth_state_service import OAuthStateService


service = OAuthStateService()

state, _ = service.create_state()

first = service.consume_state(state)

assert first is not None

second = service.consume_state(state)

assert second is None

print("PASS: OAuth state is valid once only")
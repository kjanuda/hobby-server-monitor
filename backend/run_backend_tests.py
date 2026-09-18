import subprocess
import sys
import time
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


TESTS = [
    # Core / infrastructure
    "test_lxd.py",
    "test_sessions.py",
    "test_oauth_state.py",

    # Identity / users
    "test_google_identity.py",
    "test_revoked_google_identity.py",
    "test_users.py",
    "test_user_management.py",
    "test_audit.py",

    # Authentication / authorization
    "test_authorization.py",
    "test_auth_hardening.py",

    # User APIs
    "test_users_api.py",
    "test_user_update_api.py",

    # Container registry / access
    "test_container_registry.py",
    "test_container_access.py",
    "test_container_assignment_list.py",
    "test_container_direct_access.py",

    # Quotas
    "test_quota_validation.py",
    "test_host_capacity.py",
    "test_quota_api.py",

    # Metrics / terminal
    "test_metrics_api.py",
    "test_terminal_api.py",

    # Keep this sequence together.
    # Later tests depend on the temporary container
    # created by test_container_create.py.
    "test_container_create.py",
    "test_container_update.py",
    "test_container_live_update.py",
    "test_container_actions.py",
    "test_container_delete.py",
]


def run_test(filename):
    path = BASE_DIR / filename

    if not path.exists():
        print(
            f"\nERROR: Missing test file: {filename}"
        )
        return False, 0

    print()
    print("=" * 72)
    print(f"RUNNING: {filename}")
    print("=" * 72)

    started = time.monotonic()

    result = subprocess.run(
        [
            sys.executable,
            str(path),
        ],
        cwd=BASE_DIR,
    )

    elapsed = time.monotonic() - started

    if result.returncode != 0:
        print()
        print(
            f"FAILED: {filename} "
            f"({elapsed:.2f}s)"
        )
        return False, elapsed

    print()
    print(
        f"PASSED: {filename} "
        f"({elapsed:.2f}s)"
    )

    return True, elapsed


def main():
    print("=" * 72)
    print("HOBBY SERVER MONITOR - BACKEND REGRESSION SUITE")
    print("=" * 72)

    print(
        f"Python: {sys.executable}"
    )

    print(
        f"Tests: {len(TESTS)}"
    )

    suite_started = time.monotonic()

    passed = 0

    for filename in TESTS:
        success, _ = run_test(
            filename
        )

        if not success:
            total = (
                time.monotonic()
                - suite_started
            )

            print()
            print("=" * 72)
            print("BACKEND REGRESSION SUITE FAILED")
            print("=" * 72)

            print(
                f"Passed: {passed}/{len(TESTS)}"
            )

            print(
                f"Failed: {filename}"
            )

            print(
                f"Duration: {total:.2f}s"
            )

            sys.exit(1)

        passed += 1

    total = (
        time.monotonic()
        - suite_started
    )

    print()
    print("=" * 72)
    print("BACKEND REGRESSION SUITE PASSED")
    print("=" * 72)

    print(
        f"Passed: {passed}/{len(TESTS)}"
    )

    print(
        f"Duration: {total:.2f}s"
    )

    print(
        "Result: BACKEND REGRESSION PASS"
    )


if __name__ == "__main__":
    main()

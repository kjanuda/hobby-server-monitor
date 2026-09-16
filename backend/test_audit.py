from services.audit_service import AuditService
from services.user_service import UserService


users = UserService()
audit = AuditService()


print("Updating user 1...")

users.update_user(
    user_id=1,
    name="Updated Test User",
    role="container_user",
    ram_quota_bytes=3 * 1024 * 1024 * 1024,
    cpu_quota=2,
    disk_quota_bytes=25 * 1024 * 1024 * 1024,
)


print("\nRecent audit logs:")

for log in audit.list_logs(limit=10):
    print(log)
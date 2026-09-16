PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);

INSERT INTO schema_version (version)
SELECT 1
WHERE NOT EXISTS (
    SELECT 1 FROM schema_version
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    email TEXT NOT NULL UNIQUE,
    name TEXT,

    google_sub TEXT UNIQUE,

    role TEXT NOT NULL DEFAULT 'container_user'
        CHECK (role IN ('admin', 'container_user')),

    invited INTEGER NOT NULL DEFAULT 1
        CHECK (invited IN (0, 1)),

    active INTEGER NOT NULL DEFAULT 1
        CHECK (active IN (0, 1)),

    ram_quota_bytes INTEGER NOT NULL DEFAULT 0
        CHECK (ram_quota_bytes >= 0),

    cpu_quota INTEGER NOT NULL DEFAULT 0
        CHECK (cpu_quota >= 0),

    disk_quota_bytes INTEGER NOT NULL DEFAULT 0
        CHECK (disk_quota_bytes >= 0),

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS containers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    lxd_uuid TEXT NOT NULL UNIQUE,
    lxd_name TEXT NOT NULL UNIQUE,

    description TEXT,

    owner_user_id INTEGER,

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (owner_user_id)
        REFERENCES users(id)
        ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS container_access (
    user_id INTEGER NOT NULL,
    container_id INTEGER NOT NULL,

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (user_id, container_id),

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    FOREIGN KEY (container_id)
        REFERENCES containers(id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    user_id INTEGER,
    container_id INTEGER,

    actor_email TEXT,
    action TEXT NOT NULL,
    details TEXT,

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE SET NULL,

    FOREIGN KEY (container_id)
        REFERENCES containers(id)
        ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_users_email
ON users(email);

CREATE INDEX IF NOT EXISTS idx_containers_uuid
ON containers(lxd_uuid);

CREATE INDEX IF NOT EXISTS idx_containers_owner
ON containers(owner_user_id);

CREATE INDEX IF NOT EXISTS idx_access_user
ON container_access(user_id);

CREATE INDEX IF NOT EXISTS idx_access_container
ON container_access(container_id);

CREATE INDEX IF NOT EXISTS idx_audit_created_at
ON audit_logs(created_at);

CREATE INDEX IF NOT EXISTS idx_audit_user
ON audit_logs(user_id);

CREATE INDEX IF NOT EXISTS idx_audit_container
ON audit_logs(container_id);
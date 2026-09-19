# Final Report — Hobby Server Monitor

## Project Summary

Hobby Server Monitor is an on-premises LXD container management and monitoring system built with Falcon, Astro, pylxd, SQLite, TinyFlux and systemd.

The implementation focuses on two priorities from the assessment: security and resource efficiency. Administrators can create and manage containers, manage users and quotas, assign container access, view historical metrics and use a container terminal. Container users can see only their assigned containers, their own quota information, historical metrics and terminal access for containers they are authorized to use.

The metrics collector runs as an independent background service and continues operating without the browser or API. It also survives temporary LXD outages and resumes automatically when LXD returns.

---

## Time Spent

The following values are retrospective estimates; I did not track time with a timer.

| Area | Approximate Time |
| --- | ---: |
| Backend API, authentication and authorization | 7 hours |
| Astro dashboard and UI integration | 6 hours |
| LXD integration and container lifecycle | 4 hours |
| Background collector and metrics | 4 hours |
| Testing and debugging | 6 hours |
| Documentation and final report | 3 hours |
| **Total** | **30 hours** |

The largest amount of time went into backend correctness, authorization, testing and integration because those areas have the highest security impact.

---

## Key Decisions

### 1. Explicit bootstrap administrator instead of “first login wins”

I chose to configure the initial administrator using `BOOTSTRAP_ADMIN_EMAIL`.

During database initialization, that email is inserted as an invited administrator. If the same email already belongs to a non-admin user, initialization refuses to silently promote the account.

I rejected a “first Google account to sign in becomes admin” design because it creates an unnecessary race and makes accidental or unauthorized administrative access possible during first deployment.

---

### 2. Opaque server-side sessions

The application creates a random session token after successful Google authentication. Only a hash of the token is persisted in SQLite, while the browser receives the raw token in an `HttpOnly` cookie.

Sessions have an expiry time and logout invalidates the stored session.

I chose this instead of storing application authorization state only inside a long-lived client-side token because server-side sessions make revocation straightforward and allow the application to reject a revoked user immediately.

---

### 3. Authorization is enforced by the backend

The dashboard hides controls that a user should not use, but UI visibility is not treated as a security boundary.

The API performs authorization before exposing container data or running terminal commands. A container user requesting an unassigned container ID receives `403`, including direct-ID requests that bypass the normal dashboard flow.

This design was chosen because any frontend-only authorization can be bypassed by sending API requests directly.

---

### 4. Stable container identity uses the LXD UUID

The SQLite registry stores both the LXD UUID and LXD name.

The UUID is treated as the stable identity while the name is retained for human-readable display and LXD operations.

This avoids tying assignments and historical metrics only to a mutable display name.

---

### 5. Quotas represent allocated resources

Per-user quotas are defined for allocated RAM, CPU cores and disk rather than instantaneous runtime consumption.

A quota value of `0` means unlimited at the user-quota level, but host capacity is still enforced.

Container creation and resource updates are validated against both the user's remaining quota and aggregate host capacity.

I chose allocation-based accounting because it is deterministic at provisioning time and prevents over-allocation before a workload begins consuming resources.

---

### 6. Metrics collection is independent from the browser and API

Metrics are collected by a separate Python process rather than by browser polling or API requests.

The default interval is 10 seconds. Disk usage can require more expensive container-side work, so disk measurement is cached and sampled less frequently.

This means opening more dashboard tabs does not increase LXD polling load and metric collection continues when no browser is open.

---

### 7. Terminal execution uses pylxd instead of a host shell

Terminal commands are executed inside the selected LXD container using `pylxd`.

The application does not build a host shell command containing user input.

Access is checked before execution, privileged containers are blocked from this terminal path, execution has a timeout, and output is capped.

This does not make arbitrary command execution inside a container harmless, but it significantly reduces the chance that the web terminal itself becomes a host-shell injection path.

---

### 8. The API and dashboard bind to loopback

The Falcon API listens on `127.0.0.1:8000` and the Astro production server listens on `127.0.0.1:4321`.

The dashboard proxies `/api/*` requests to Falcon.

For the assessment environment this keeps the backend from being directly exposed to the LAN. A production deployment should place the dashboard behind an HTTPS reverse proxy and keep the API private.

---

## Security Design

### Authentication

Google OAuth 2.0 is used for sign-in.

The implementation includes:

- invite-only accounts
- explicit bootstrap administrator
- stable Google subject identifier (`google_sub`)
- one-time OAuth state
- PKCE
- session expiry
- revoked-user checks
- logout that invalidates the server-side session

### Session security

Session tokens are random opaque values.

Only the SHA-256 hash of the session token is stored in the database.

The session cookie is configured with:

- `HttpOnly`
- `SameSite=Lax`
- configurable `Secure`

For local HTTP development `SESSION_COOKIE_SECURE=false` is necessary. For an HTTPS deployment it should be changed to `true`.

### CSRF protection

Mutating authenticated requests use double-submit CSRF protection.

The server requires the CSRF cookie and matching `X-CSRF-Token` header for protected state-changing requests.

### Authorization

Authorization is enforced server-side.

Container users can access only containers explicitly assigned to them. Direct access to an unassigned container returns `403`.

Administrator-only APIs protect container creation, lifecycle management, deletion, resource-limit changes, user management and assignment management.

### LXD privilege decision

The API and collector require local LXD access through the `lxd` group.

This is a significant privilege: access to the LXD daemon should be treated as effectively root-equivalent in the threat model.

The current assessment implementation reduces exposure by keeping LXD access out of the Astro dashboard and applying systemd hardening, but the API and collector still have powerful LXD access.

For a higher-security production design I would isolate LXD operations behind a narrow local privileged broker with a small allow-listed interface instead of giving the main API process direct LXD daemon access.

### systemd hardening

The supplied services use hardening options including:

```text
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
RestrictSUIDSGID=true
UMask=0077
```

The API and collector receive the `lxd` supplementary group only where required. The dashboard does not require LXD group membership.

---

## Metrics Design

The metrics collector samples LXD independently every 10 seconds and stores time-series samples using TinyFlux.

The main measurement is:

```text
container_metrics
```

Tags include container UUID, container name and state.

Fields include:

- CPU percentage
- CPU usage time
- memory used
- memory limit
- memory percentage
- process count
- RX/TX byte counters
- RX/TX rate
- uptime
- disk used
- disk allocation where available
- disk percentage where available

Raw metrics retention is currently configured for 48 hours.

Historical API responses are reduced to a bounded number of points before being sent to the browser, avoiding unnecessarily large chart payloads.

Disk usage is measured less frequently because it can require more expensive container-side work.

---

## Failure and Recovery Testing

### Collector independence from API and browser

I stopped both the API service and Astro dashboard while leaving the collector running.

Observed state:

```text
API:       inactive
Dashboard: inactive
Collector: active
```

During that period the collector continued inserting one metric point approximately every 10 seconds.

This demonstrated that collection is independent from browser/API availability.

### LXD outage test

To create a real LXD outage I stopped both:

```text
snap.lxd.daemon.unix.socket
snap.lxd.daemon.service
```

`lxc list` then failed with a Unix socket connection-refused error.

During the outage the collector logged LXD connection failures but remained alive:

```text
MainPID=89855
NRestarts=0
ActiveState=active
```

The collector logged:

```text
[collector] LXD unavailable: ... Connection refused
[collector] inserted 0 point(s)
```

After LXD was started again, the same collector process automatically resumed valid inserts:

```text
[collector] inserted 1 point(s)
```

No collector restart was required.

---

## Resource Measurements

Resource usage was measured with all three production-style systemd services active, the dashboard running from the Astro production build, one LXD test container running, and no intentional browser interaction during the measurement window.

The test environment was Ubuntu 24.04 under WSL2 with 4 logical CPUs and approximately 8 GiB RAM.

### Measurement method

Memory was taken from systemd `MemoryCurrent`.

CPU usage was calculated using the change in systemd `CPUUsageNSec` over a 30-second idle window:

```text
CPU % = CPU time consumed during interval / 30 seconds × 100
```

### 30-second idle measurement

| Service | MemoryCurrent | CPU over 30 s |
| --- | ---: | ---: |
| Falcon API | 30.42 MiB | 0.021% |
| Metrics collector | 54.29 MiB | 4.716% |
| Astro dashboard | 33.96 MiB | 0.006% |
| **Total** | **118.67 MiB** | **4.743%** |

The collector accounts for nearly all measured idle CPU because it deliberately wakes every 10 seconds to query LXD and record metrics.

This is a point-in-time development measurement rather than a benchmark across multiple hosts or large numbers of containers. The cost will vary with container count, disk-measurement work and host characteristics.

An earlier process-level `ps` snapshot also showed that the production Astro server used substantially less resident memory than the Astro development server, which is why final measurements were taken using the production systemd deployment.

---

## Testing

The final backend regression suite completed:

```text
26/26 PASS
```

The suite covers:

- LXD connectivity
- authentication and sessions
- OAuth state behavior
- Google identity handling
- revoked-user behavior
- user management
- role authorization
- CSRF rejection
- assignments
- direct-ID authorization
- quota validation
- aggregate host-capacity validation
- quota accounting
- historical metrics authorization
- terminal execution and authorization
- container creation
- resource updates
- live resource updates
- lifecycle actions
- safe deletion
- database cleanup
- assignment cleanup
- audit behavior

The terminal test confirmed that a command executed in the expected LXD container and that an unassigned user receives `403`.

The metrics test confirmed that an assigned user can retrieve historical metrics and loses access after assignment removal.

The frontend was checked with:

```bash
npm run astro -- check
npm run build
```

The final production Astro build completed successfully.

The three systemd service files were also checked with `systemd-analyze verify`, and all three services were confirmed `enabled` and `active`.

The dashboard returned HTTP `200` from `http://127.0.0.1:4321/`.

---

## Issues Encountered and Solutions

### 1. LXD API and metric edge cases

Some LXD data is not available in exactly the same form for every container state or storage configuration.

Disk usage was one example. LXD's storage information could report incomplete values, so I added a slower container-side fallback with caching rather than performing expensive disk work on every 10-second collector cycle.

### 2. Quota validation needed both user and host checks

Checking only the user's quota was not enough because multiple users could collectively allocate more RAM, CPU or disk than the host could support.

The validation was extended to calculate aggregate explicit allocations and enforce host-level limits as well as per-user limits.

### 3. Direct container-ID authorization

A list endpoint that filters containers is not sufficient security by itself because a user can manually call a detail endpoint with another ID.

Direct container access was tested separately so unassigned and random IDs return `403` before container information is exposed.

### 4. Systemd deployment script bug

An early version of the deployment installer split a Bash parameter expansion across lines:

```text
SERVICE_USER="${
    HSM_USER:-${SUDO_USER:-$USER}
}"
```

This passed a basic syntax check but failed at runtime with `bad substitution`.

It was corrected to:

```text
SERVICE_USER="${HSM_USER:-${SUDO_USER:-$USER}}"
```

The deployment was then rebuilt, installed and verified successfully.

### 5. LXD socket activation during outage testing

Stopping only `snap.lxd.daemon.service` did not create a real outage because the active Unix socket automatically started the daemon again.

The test was corrected by stopping both the activating socket and the daemon. This produced a real `connection refused` condition and allowed collector resilience to be verified accurately.

### 6. Development server resource usage was misleading

An Astro development process consumed much more memory than the production server.

I added a production Astro build and systemd service, then repeated resource measurement against the production process rather than reporting development-server memory as the final footprint.

### 7. Environment configuration became stale

The initial `.env.example` contained placeholder variables that were no longer used by the implementation and omitted `HSM_BACKEND_URL`, which the Astro proxy actually uses.

I audited `backend/config.py` and the Astro proxy, removed stale configuration entries and aligned `.env.example` with the current code.

### 8. Secret handling mistake during development

A local environment backup containing OAuth credentials was accidentally staged in Git history during development. GitHub push protection blocked the push.

The secret file was removed from tracking, added to `.gitignore`, and the affected Git history was rewritten before pushing.

The lesson from this was that deleting a secret from the latest working tree is not enough once it has entered Git history. Credentials that were exposed should also be revoked/rotated. Before final submission, the affected OAuth client secret should be rotated if that has not already been done.

### 9. Long terminal heredoc pastes were unreliable

Large Markdown pastes into the interactive terminal became corrupted while creating documentation.

I stopped using long terminal heredocs for the final README and instead copied a verified file into the repository, followed by `git diff --check` and content checks.

---

## What I Learned

This project reinforced that container management software is mostly a security and systems problem rather than only a dashboard problem.

Key lessons included:

- LXD daemon access carries much more privilege than a normal application API.
- Frontend role checks are useful for UX but cannot replace backend authorization.
- Stable infrastructure identifiers are important when names can change.
- Allocation quotas and runtime usage are different concepts and should not be mixed.
- Background monitoring should not depend on browser activity.
- Failure testing must prove that the dependency is genuinely unavailable; socket activation can invalidate an intended outage test.
- Resource measurements should use the production deployment, not a development server.
- Secrets require both Git hygiene and credential rotation after exposure.
- Automated tests are especially valuable for authorization paths because direct API requests can bypass the UI.

---

## Bonus Features Implemented

Beyond the minimum browser workflow, the project includes:

- automated backend regression runner
- CSRF protection
- OAuth PKCE and one-time state storage
- hashed server-side session tokens
- aggregate host-capacity validation
- audit logging
- stable LXD UUID registry
- secure terminal timeout and output limits
- privileged-container terminal blocking
- disk-usage fallback and caching
- historical point reduction
- hardened systemd units
- automated production dashboard build in the systemd installer
- explicit LXD outage/recovery testing
- measured production service footprint

---

## Known Limitations

### Raw metric retention

Raw metrics are currently retained for 48 hours. The assignment discusses month-scale operation; a stronger long-term design would add tiered aggregation, for example retaining high-resolution data briefly and hourly aggregates for longer periods.

### External containers and allocation accounting

Containers created outside this application may not have the same explicit resource limits. Aggregate allocation accounting is therefore most reliable for containers managed through this application.

### LXD privilege

The API and collector still require powerful LXD access. systemd hardening reduces some risk but does not change the fundamental privilege level of the LXD daemon.

A production design should consider a smaller privileged broker with a narrow allow-listed protocol.

### Localhost-only deployment

The supplied deployment intentionally binds the API and dashboard to localhost. LAN/Internet exposure, reverse-proxy configuration and TLS termination are outside the implemented scope.

### Browser-level second-account test

Backend tests cover assigned/unassigned container-user behavior, metrics and terminal authorization. A full browser-level OAuth walkthrough using a second real Google account was not included in the automated test suite.

### No alerts or multi-host management

The project does not implement alerting, snapshots, notification delivery or management of multiple LXD hosts.

### Reboot verification

The services are installed and enabled under systemd and were restarted successfully during testing. A full host reboot was not used as a final automated test, so boot persistence is based on the enabled units and systemd configuration rather than a recorded reboot test.

---

## AI Tool Usage

I used ChatGPT as a development assistant during the project.

It was used for:

- breaking the assessment into implementation stages
- discussing architecture and security tradeoffs
- suggesting Falcon service/repository separation
- reviewing authentication and authorization flows
- drafting and reviewing test cases
- helping diagnose LXD, Astro, Git and systemd issues
- suggesting commands for deployment and failure testing
- reviewing resource-measurement methodology
- drafting documentation and this final report

I did not treat AI output as automatically correct.

Examples of AI-assisted output that required correction or validation included:

- a Bash `SERVICE_USER` expression that was formatted incorrectly and failed with `bad substitution`
- an initial LXD outage test that stopped only the daemon and did not account for socket activation
- environment documentation that needed to be compared against the actual implementation
- large Markdown terminal pastes that became corrupted and had to be replaced using a safer file workflow

I validated changes by reading the implementation, running tests, checking HTTP behavior, exercising the LXD operations, inspecting systemd state and logs, and checking Git diffs.

The submitted code remains my responsibility, including AI-assisted sections, and I should be able to explain the purpose and behavior of every line during review.

---

## Final Status

At the time of this report:

- backend regression suite: **26/26 passed**
- Astro type/content check: **passed**
- Astro production build: **passed**
- API systemd service: **active and enabled**
- collector systemd service: **active and enabled**
- dashboard systemd service: **active and enabled**
- systemd unit verification: **passed**
- dashboard local HTTP check: **200**
- API/browser independence test: **passed**
- real LXD outage survival test: **passed**
- automatic collector recovery after LXD return: **passed**
- production idle footprint measured: **118.67 MiB MemoryCurrent total; 4.743% of one logical CPU-equivalent over a 30-second idle window (~1.186% of total CPU capacity on the 4-logical-CPU test host)**

Before submission, any OAuth credential that was previously exposed during development should be rotated if it has not already been rotated.

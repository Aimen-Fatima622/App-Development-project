# NaSCon 26 — Multi-Sport League & Club Operations Platform

Production-style, multi-tenant sports league and club operations platform combining rule-driven league management, fixture scheduling, club roster operations, and a concurrency-safe in-app merchandise store.

---

## Architecture & Technology Stack
- **Backend**: Python 3.12, FastAPI, Uvicorn
- **Security & RBAC**: Custom JWT with 5-tier access control and tenant isolation
- **Fixture Generation**: Custom circle-method round robin, backtracking Swiss, seeded single & double elimination
- **Event Sourcing**: Append-only match event stream with compensating rollback events and HMAC-SHA256 signatures
- **Store & Inventory**: Concurrency-safe stock reservation, mock payment gateway, valid `%PDF` receipt generation
- **Mobile**: Android application with offline SQLite caching, local action queue, and automatic conflict-resolved sync
- **Containerization**: Docker Compose orchestration

---

## Quickstart & Run Instructions

### 1. Start the Complete Backend with Docker Compose
```bash
docker compose up -d --build
```

### 2. Verify Health Readiness Probe
```bash
curl http://localhost:8080/health
# Response: {"status":"ok"}
```

### 3. Interactive API Documentation (Swagger)
Open in your browser:
- [http://localhost:8080/docs](http://localhost:8080/docs)

### 4. Mobile Application (Desk Check & PWA)
Open directly on your laptop or phone browser:
- [http://localhost:8080/mobile](http://localhost:8080/mobile)
- Supports all 9 required screens, 5 demo accounts, offline queueing in Airplane mode, and one-tap conflict sync.

---

## Mandatory Demo Accounts (Section 8.3)
Seeded and active across all startups and resets:

| Role | Email | Password | Scope / Permissions |
| :--- | :--- | :--- | :--- |
| **Platform Super-Admin** | `admin@nascon.test` | `Nascon@26` | Platform-wide root administrator |
| **League Organizer** | `organizer@nascon.test` | `Nascon@26` | Controls `league-alpha-1` in `tenant-alpha` |
| **Club Manager** | `manager@nascon.test` | `Nascon@26` | Manages `club-alpha-1` roster & products |
| **Player** | `player@nascon.test` | `Nascon@26` | `player-alpha-1` self profile access |
| **General Viewer** | `viewer@nascon.test` | `Nascon@26` | Read-only access inside `tenant-alpha` |

---

## Running Automated Tests
```bash
bash ./run_tests.sh
```
Or directly with pytest:
```bash
pytest backend/tests -v
```

---

## Mobile Application
The Android mobile application is available in `mobile/` with the installable APK at:
- `mobile/release/app-release.apk`
It features 9 role-aware screens, offline persistence (Room/SQLite), local action queueing, and automatic synchronization against `POST /audit/v1/offline-sync`.

# Requirements Traceability Matrix (TRACEABILITY.md)

This document maps every Functional Requirement (FR) and Non-Functional Requirement (NFR) from the NaSCon '26 Problem Specification to the implementing source code files and automated test suites.

| Requirement ID | Requirement Description | Source Implementation | Automated Tests |
| :--- | :--- | :--- | :--- |
| **FR-1.1** | Multi-Sport Taxonomy & Event-Sourced Scoring | `backend/app/sports.py`, `backend/app/scoring.py` | `backend/tests/test_audit_scoring.py` |
| **FR-1.2** | League and Tournament Setup | `backend/app/scoring.py` (`register_league`) | `backend/tests/test_audit_standings.py` |
| **FR-1.3** | Fixture Scheduling (Round-robin, Swiss, Single & Double Elim) | `backend/app/fixtures.py` | `backend/tests/test_audit_fixtures.py` |
| **FR-1.4** | Automated Standings, H2H Mini-League & Qualification | `backend/app/standings.py` | `backend/tests/test_audit_standings.py` |
| **FR-2.1** | Club Profiles & Multi-Tenant Isolation | `backend/app/state.py`, `backend/app/rbac.py` | `backend/tests/test_audit_rbac.py` |
| **FR-2.2** | Roster, Transfers, Loans & Immutable Audit Trail | `backend/app/roster.py` | `backend/tests/test_audit_roster.py` |
| **FR-2.3** | Concurrency-Safe Store, Mock Payment & PDF Receipt | `backend/app/store.py` | `backend/tests/test_audit_store.py` |
| **FR-5.1** | 5-Tier Role-Based Access Control (RBAC) & Boundary Probes | `backend/app/rbac.py` | `backend/tests/test_audit_rbac.py` |
| **NFR-3** | Concurrency Correctness (Atomic stock reservation) | `backend/app/store.py` (`process_checkout`) | `backend/tests/test_audit_store.py` |
| **NFR-4** | Offline Tolerance & Conflict Sync | `backend/app/offline_sync.py`, `mobile/` | `backend/tests/test_audit_offline_sync.py` |
| **NFR-5** | API Security (OWASP, Rate Limiting, Input Validation) | `backend/app/main.py`, `backend/app/rbac.py` | `backend/tests/test_audit_rbac.py` |
| **NFR-7** | Single-command Reproducibility | `docker-compose.yml`, `backend/Dockerfile` | `backend/tests/test_health.py` |
| **Edge Case 1** | Round-robin with withdrawals & odd teams | `backend/app/fixtures.py` | `backend/tests/test_audit_fixtures.py` |
| **Edge Case 2** | Swiss backtracking rematch-free pairing | `backend/app/fixtures.py` | `backend/tests/test_audit_fixtures.py` |
| **Edge Case 3** | Double elimination bracket reset (GF1 & GF2) | `backend/app/fixtures.py` | `backend/tests/test_audit_fixtures.py` |
| **Edge Case 4** | 3-way tie H2H mini-league tie-breaker | `backend/app/standings.py` | `backend/tests/test_audit_standings.py` |
| **Edge Case 5** | Standings recomputed from scratch after compensating event | `backend/app/scoring.py`, `backend/app/standings.py` | `backend/tests/test_audit_scoring.py` |
| **Edge Case 6** | Deferred transfer during in-progress match | `backend/app/roster.py` | `backend/tests/test_audit_roster.py` |

# Changelog

## 1.6.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.5.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.4.1 — work-in-progress checkpoint

### Added
- **Multiplayer protocol support**: Scaffolding-MC status and ping endpoints
  - `GET /api/protocol/status` - Returns Minecraft server resource info
  - `GET /api/protocol/ping` - Simplified ping variant
  - Default protocol version 20, motd "Sentinel Pilot", max_players 20
- Protocol test coverage: `TestProtocol` with 3 tests in `backend/tests/test_api.py`

### Changed
- `protocol.py` refactored to use `get_settings()` from `app.core.config`
- Updated roadmap status: multiplayer feature completed

### Security
- No new security changes

---

## 1.4.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.3.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.2.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.1.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.0.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## [1.0.1] - 2026-11-01

### Added
- Test coverage for mod upload endpoint (file upload and duplicate detection)
- 2 new backend tests for mod upload functionality

### Changed
- Mod management feature status: planned → done
- All 27 backend tests passing
- All 21 frontend tests passing

### Security
- No new security changes
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-10-22

### Added
- FastAPI backend with health, auth, instances, and mods APIs
- SQLAlchemy models for User, Instance, Mod, and AuditLog
- JWT-based authentication with HttpOnly cookies and CSRF protection
- React + TypeScript + Vite frontend
- Zustand state management for auth, instances, mods, and theme
- Responsive UI with dark/light mode
- Instance management (CRUD, pagination, search, filtering)
- Mod management (CRUD, file upload, enable/disable)
- Dockerfiles for backend and frontend with non-root users
- docker-compose.yaml with backend, frontend, and Keycloak
- GitHub Actions CI workflow (backend tests, frontend build/test, Docker builds)
- Keycloak OIDC integration with realm import guidance
- Comprehensive README with architecture diagram and setup instructions

### Security
- Secure OIDC authorization code flow with PKCE
- HttpOnly, SameSite=Lax cookies
- CSRF protection on state-changing operations
- Role-based access control (viewer, operator, admin)
- Demo mode restricted to localhost
- No hardcoded secrets or credentials

---

Alan Vo · [alanvo.net](https://alanvo.net) · [X: @alanvoasi](https://x.com/alanvoasi)

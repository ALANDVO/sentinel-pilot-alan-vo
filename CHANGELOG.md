# Changelog

## 1.0.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

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
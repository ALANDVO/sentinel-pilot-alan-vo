# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

skeleton

## Roadmap

### skeleton — FastAPI/React skeleton with Docker and CI

Status: done

Acceptance:
- FastAPI app with health endpoint
- React + Vite + TypeScript frontend builds
- Dockerfiles for backend and frontend
- docker-compose with Keycloak
- CI workflow runs backend tests and frontend build/test
- README with install/run steps

Implementation: `backend/app/main.py`, `backend/app/api/health.py`, `backend/app/api/auth.py`, `backend/app/api/instances.py`, `backend/app/api/mods.py`, `backend/app/core/config.py`, `backend/app/core/database.py`, `backend/app/core/security.py`, `backend/app/models/__init__.py`, `frontend/src/main.tsx`, `frontend/src/components/UI.tsx`, `frontend/src/components/Layout.tsx`, `frontend/src/pages/Login.tsx`, `frontend/src/pages/Register.tsx`, `frontend/src/pages/Instances.tsx`, `frontend/src/pages/Mods.tsx`, `frontend/src/pages/Settings.tsx`, `frontend/src/hooks/useAuth.ts`, `frontend/src/hooks/useInstances.ts`, `frontend/src/hooks/useMods.ts`, `frontend/src/hooks/useTheme.ts`, `frontend/src/api/client.ts`, `frontend/src/types/api.ts`, `backend/Dockerfile`, `frontend/Dockerfile`, `compose.yaml`, `.github/workflows/ci.yml`, `pyproject.toml`

Tests: `backend/tests/test_api.py`, `frontend/src/components/UI.test.tsx`

### auth — OIDC authentication with Keycloak

Status: planned

Acceptance:
- Backend session management with HttpOnly cookies
- CSRF protection on writes
- Frontend login/logout flow
- Protected API endpoints
- Demo mode for local development

### instance-management — Minecraft instance management

Status: done

Acceptance:
- Create/read/update/delete instances
- Version detection and listing
- Instance launch configuration

Implementation: `backend/app/api/instances.py`, `backend/app/models/__init__.py`, `frontend/src/pages/Instances.tsx`, `frontend/src/hooks/useInstances.ts`

Tests: `backend/tests/test_api.py::TestInstances`

### mod-management — Mod management with secret decryption

Status: planned

Acceptance:
- Mod installation from files/URLs
- Secret decryption with hardware ID binding
- Mod enable/disable per instance

Implementation: `backend/app/api/mods.py`, `frontend/src/pages/Mods.tsx`, `frontend/src/hooks/useMods.ts`

Tests: `backend/tests/test_api.py::TestMods`

### multiplayer — Multiplayer protocol support

Status: planned

Acceptance:
- Scaffolding-MC protocol support
- LAN/VPN instance sharing

### theme-ui — Dark mode and responsive UI

Status: done

Acceptance:
- Dark/light theme toggle
- Responsive dashboard
- Loading/error/empty states

Implementation: `frontend/src/hooks/useTheme.ts`, `frontend/src/components/UI.tsx`, `frontend/src/components/Layout.tsx`, `frontend/src/styles/index.css`

Tests: `frontend/src/components/UI.test.tsx`


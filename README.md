# Full-Stack Hackathon Starter

A reusable, domain-agnostic starter for building CRUD/business applications fast. Bring your own problem statement — the plumbing is done.

**Stack:** Next.js (App Router) · TypeScript · Tailwind CSS · shadcn/ui · TanStack Query · React Hook Form — FastAPI · SQLAlchemy 2 · Alembic · PostgreSQL · Pydantic v2 · JWT

## What's included

**Backend**
- JWT authentication (access + refresh tokens) — register, login, refresh, me
- User management CRUD
- Role-based access control — roles hold permission strings (e.g. `users:read`); `*` grants everything
- Generic CRUD base (`CRUDBase`) with pagination, filtering, sorting and search
- Centralized env-driven configuration (`app/config/settings.py`)
- Structured logging + request logging
- Global exception handling (consistent `{"detail": ...}` errors)
- Alembic migrations + idempotent seeding (default roles + admin user)

**Frontend**
- Auth context with session restore, login/register/logout
- Axios API client with automatic token refresh on 401
- Route guards: `AuthGuard`, `GuestGuard`, `PermissionGuard`
- Dashboard shell (responsive sidebar + header + user menu)
- Users management page (search, pagination, create/edit/delete dialogs) — a template for every list screen you'll build
- shadcn/ui components, loading skeletons, toast-based error handling

## Quick start

```bash
cp .env.example .env   # adjust values if needed
docker compose up --build
```

- Frontend: http://localhost:3001
- API: http://localhost:8001/api/v1
- API docs: http://localhost:8001/api/v1/docs
- Default admin: `ADMIN_EMAIL` / `ADMIN_PASSWORD` from `.env` (admin@example.com / admin12345)

Set `APP_ENV=production` in `.env` to build/run production images with the same compose file.

### Running without Docker

Backend (requires a running PostgreSQL matching `DATABASE_URL`):

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python -m app.main
```

Frontend:

```bash
cd frontend
yarn install
yarn dev
```

## Project structure

```
├── frontend/
│   └── src/
│       ├── app/                  # Routes: (auth) group, (dashboard) group
│       ├── components/
│       │   ├── ui/               # shadcn/ui components
│       │   └── layout/           # Sidebar, header, nav config
│       ├── features/
│       │   ├── auth/             # Context, guards, forms, API
│       │   └── users/            # Users CRUD: API, hooks, table, dialogs
│       └── lib/                  # Axios client, config, utils, types
├── backend/
│   ├── alembic/                  # Migrations
│   └── app/
│       ├── config/               # settings.py (env-driven), logging.py
│       ├── core/                 # security, deps, crud base, pagination,
│       │                         # exceptions, middleware
│       ├── db/                   # base, session, seed
│       ├── auth/  users/  roles/ # Feature modules (models, schemas, router)
│       ├── api.py                # Router aggregation
│       └── main.py               # App factory
├── docker-compose.yml
└── .env.example
```

## Adding a new entity (the hackathon workflow)

Example: adding `projects`.

**Backend**

1. `app/projects/models.py` — SQLAlchemy model (use `Base`, `TimestampMixin`).
2. `app/projects/schemas.py` — `ProjectCreate`, `ProjectUpdate`, `ProjectRead` (with `from_attributes=True`).
3. `app/projects/router.py` — copy `app/roles/router.py`, swap model/schemas, set permissions (`projects:read` / `projects:write`). `CRUDBase(Project, search_fields=[...])` gives you list/get/create/update/delete with pagination, search, sorting and filtering for free.
4. Register the router in `app/api.py`.
5. Import the models module in `alembic/env.py`, then:
   ```bash
   alembic revision --autogenerate -m "add projects"
   alembic upgrade head
   ```
6. Grant the new permissions to roles (via the roles API or seed).

**Frontend**

1. `src/features/projects/api.ts` + `hooks.ts` — copy from `src/features/users/`.
2. Components: copy `users-table.tsx` / `user-form-dialog.tsx` and adapt columns/fields.
3. Add the page under `src/app/(dashboard)/projects/page.tsx`.
4. Add a nav item in `src/components/layout/nav-items.ts` (with its permission).

## RBAC

- Roles carry a list of permission strings; `*` = full access.
- Seeded roles: `admin` (`*`) and `user` (none) — the default for self-registered users.
- Backend: guard endpoints with `Depends(require_permissions("thing:read"))`.
- Frontend: `<PermissionGuard permissions={["thing:read"]}>` or `hasPermission()` from `useAuth()`.

## Configuration

Everything is environment-driven — see `.env.example` for the full list. Backend settings are validated in `backend/app/config/settings.py`; frontend values come from `NEXT_PUBLIC_*` variables (baked in at build time for production images).

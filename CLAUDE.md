# Project Guidelines: Remembench

## System Architecture
This is an agentic Competitive Intelligence Engine built to track industry-specific events (weather, holidays, promotions, competitors).
- Frontend: Next.js (App Router), React, Tailwind CSS, Recharts
- Backend: Python, FastAPI, SQLAlchemy, asyncpg, Celery, Redis
- Database: PostgreSQL with PostGIS

## Commands

- Setup & Launch: `docker compose up -d --build`
- Frontend Dev: `cd frontend && npm install && npm run dev`
- Backend Dev: `cd backend && source .venv/bin/activate && uvicorn app.main:app --reload`
- Test Backend: `cd backend && python -m pytest tests/ -v`

## Code Style: Frontend (Next.js / React)

- Use standard JavaScript (JS/JSX) - Do not forcefully migrate components to TypeScript unless requested.
- Functional components with React Hooks exclusively.
- Tailwind CSS exclusively for styling (avoid inline styles or custom CSS modules).
- Early returns for error handling and loading states.
- Client-side components must safely mark `'use client'` at the very top.

## Code Style: Backend (Python / FastAPI)

- Enforce Python 3.11+ type hinting on all function signatures (`-> dict`, `-> list[ImpactEventCreate]`, etc).
- Use `app.logging.get_logger` for all structlog-based, machine-readable JSON logging. Do NOT use standard `logging`.
- Maintain asynchronous operation paths (use `async def`, `await`, `asyncio.timeout()`).
- Early returns for validation checks and missing configurations (e.g. if an API key is absent).
- Follow clean architecture boundaries (Adapters -> Services -> Routes).

## Task Workflow

- Read `README.md` first to understand project context.
- When generating reports or plans, refer strictly to `task.md`.
- Before editing deep logic, read the targeted file content fully.
- Always use `difflib` over brute-force string operations where applicable.
- Make all code modifications highly modular so components can be toggled without breaking pipelines.
- Verify changes by running backend tests or asking the user to refresh the Dashboard.

## Debugging Directives
- If stuck, run the command with verbose output or tail the docker logs: `docker compose logs backend -f`
- Clear Context: If confusing edge cases occur, start fresh.
- Always be explicit about paths when using `grep` or `find` across the monorepo splits.

## Deployment Protocol Constraint
CRITICAL RULE: When pushing to remote origins, NEVER implicitly push an active development branch (e.g., `beta-audit-*`) directly to `main` via shortcut commands like `git push origin <branch>:main` unless explicitly requested. Always push parallel matching branches (e.g., `git push origin <branch_name>`).

# Multi-Subject Auth System

Multi-subject authentication and session management system supporting three subject types with multiple credential methods.

## Features

- **Three Subject Types**: Member, Community Staff, Platform Staff (independent login, same email allowed across types)
- **Multi-Credential**: Password (Argon2), OTP (6-digit, email-based), Passkey (WebAuthn)
- **MFA**: TOTP-based two-factor authentication with QR code setup
- **Multi-Device Sessions**: concurrent sessions with device tracking, remote revocation
- **Token Rotation**: access + refresh token pair with automatic rotation
- **Rate Limiting**: brute-force protection on login and OTP endpoints

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, SQLAlchemy (async), Alembic |
| Frontend | React 19, TypeScript, Tailwind CSS, Vite |
| Database | PostgreSQL 16 |
| Cache | Redis 7 |
| Auth | Argon2, py-webauthn, PyOTP |

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.12+
- Node.js 18+
- [uv](https://docs.astral.sh/uv/) (Python package manager)

### Option 1: Docker Compose (full stack)

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: http://localhost:80
- Backend API: http://localhost:8000/docs

### Option 2: Local Development

**1. Start infrastructure**

```bash
docker compose up -d postgres redis
```

**2. Backend**

```bash
cd backend
cp ../.env.example ../.env
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Backend runs at http://localhost:8000. API docs at http://localhost:8000/docs.

**3. Frontend**

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at http://localhost:5173.

### One-liner Setup

```bash
./scripts/dev-setup.sh
```

Then start backend and frontend in two terminals as shown above.

## Demo

An interactive demo script exercises all features via curl:

```bash
# Start backend first, then:
./scripts/demo.sh
```

Covers: registration, password login, OTP flow, multi-device sessions, token refresh, MFA setup/challenge/disable, credential listing, and logout.

## API Endpoints

### Auth

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/{type}/register` | Register new subject |
| POST | `/api/auth/{type}/login/password` | Password login |
| POST | `/api/auth/{type}/login/otp/request` | Request OTP |
| POST | `/api/auth/{type}/login/otp/verify` | Verify OTP and login |
| POST | `/api/auth/{type}/login/passkey/options` | Get WebAuthn auth options |
| POST | `/api/auth/{type}/login/passkey/verify` | Verify WebAuthn and login |
| POST | `/api/auth/refresh` | Refresh access token |
| POST | `/api/auth/logout` | Logout current session |
| GET  | `/api/auth/me` | Get current user info |

`{type}`: `member`, `community-staff`, `platform-staff`

### MFA

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/mfa/setup` | Start TOTP setup (returns QR code) |
| POST | `/api/mfa/confirm` | Confirm TOTP to enable MFA |
| POST | `/api/mfa/verify` | Verify MFA challenge during login |
| POST | `/api/mfa/disable` | Disable MFA |

### Sessions

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/sessions/` | List all active sessions |
| DELETE | `/api/sessions/{id}` | Revoke a session |

### Credentials

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/credentials/` | List credentials |
| POST | `/api/credentials/passkey/register/options` | Start passkey registration |
| POST | `/api/credentials/passkey/register/verify` | Complete passkey registration |
| DELETE | `/api/credentials/{id}` | Deactivate a credential |

## Environment Variables

See `.env.example`:

```
DATABASE_URL=postgresql+asyncpg://auth_user:auth_pass@localhost:5432/auth_db
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=change-me-to-a-random-string
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── models/          # SQLAlchemy models (Subject, Credential, Session)
│   │   ├── routers/         # API routes (auth, mfa, sessions, credentials)
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── services/        # Business logic (auth, otp, passkey, mfa, session)
│   │   └── utils/           # Security helpers, device parser
│   └── alembic/             # Database migrations
├── frontend/
│   └── src/
│       ├── api/             # Axios API clients
│       ├── components/      # React components
│       ├── hooks/           # Auth context hook
│       └── pages/           # Page components
├── scripts/                 # Setup and demo scripts
└── docker-compose.yml
```

#!/bin/bash
set -e

echo "=== Multi-Subject Auth System — Dev Setup ==="

# 1. Start infrastructure
echo "[1/4] Starting PostgreSQL & Redis..."
docker compose up -d postgres redis
sleep 3

# 2. Backend setup
echo "[2/4] Installing backend dependencies..."
cd backend
uv sync
echo "[3/4] Running database migrations..."
uv run alembic revision --autogenerate -m "init" 2>/dev/null || true
uv run alembic upgrade head
cd ..

# 3. Frontend setup
echo "[4/4] Installing frontend dependencies..."
cd frontend
npm install
cd ..

echo ""
echo "=== Setup Complete ==="
echo ""
echo "To start the app:"
echo "  Terminal 1: cd backend && uv run uvicorn app.main:app --reload"
echo "  Terminal 2: cd frontend && npm run dev"
echo ""
echo "  Backend:  http://localhost:8000/docs"
echo "  Frontend: http://localhost:5173"

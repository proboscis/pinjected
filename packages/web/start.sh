
echo "Starting FastAPI backend..."
cd "$(dirname "$0")"
uv sync
uv run python -m uvicorn pinjected_web.main:app --reload --port 8000 &
BACKEND_PID=$!

echo "Starting React frontend..."
cd frontend
npm install
npm start &
FRONTEND_PID=$!

cleanup() {
  echo "Shutting down services..."
  kill $BACKEND_PID
  kill $FRONTEND_PID
  exit 0
}

trap cleanup SIGINT SIGTERM

echo "Services started. Press Ctrl+C to stop."
wait

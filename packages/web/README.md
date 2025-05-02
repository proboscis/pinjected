# Pinjected Web UI

A web UI for visualizing pinjected dependency injection graphs.

## Features

- Show DI graph for a root key in design
- Search variables in the graph
- Check where variables are bound

## Technology Stack

- Backend: FastAPI for the API endpoints
- Frontend: React with React Flow for interactive graph visualization
- Styling: Material-UI components

## Installation

```bash
# Install dependencies
cd packages/web
uv sync
```

## Usage

```bash
# Start the application
cd packages/web
chmod +x start.sh
./start.sh
```

This will start both the FastAPI backend and React frontend. The UI will be accessible at http://localhost:3000.

## Development

### Backend

The backend is built with FastAPI and provides API endpoints for:
- Getting the dependency graph
- Getting node details
- Searching for dependencies

### Frontend

The frontend is built with React and uses:
- React Flow for graph visualization
- Material-UI for UI components
- Axios for API requests

# Cyber Simulation Platform API ("Enter The Breach") Backend

A scalable backend for a multi-user, AI-driven cyber crisis simulation platform. Built with FastAPI, RQ, Redis, and PostgreSQL.

---

## Features

- **FastAPI** REST API with JWT authentication
- **RQ (Redis Queue)** for asynchronous task processing
- **Redis** for state storage and Pub/Sub event streaming
- **PostgreSQL** for user data and credentials
- **WebSockets** for real-time communication
- **Docker & Docker Compose** for containerized deployment

---

## Directory Structure

```plaintext
cyber_sim_game/
├── .env                # Environment variables (do NOT commit)
├── .gitignore
├── Dockerfile          # Build instructions for API, worker, scheduler
├── docker-compose.yml  # Service definitions (api, worker, scheduler, redis, postgres)
├── requirements.txt    # Python dependencies
├── index.html          # Landing / login page
├── simulation.html     # Main simulation UI
├── static/             # Frontend assets (CSS, JS)
│   ├── simulation.css
│   ├── simulation.js
│   └── style.css       # Landing page styles
├── app/                # FastAPI application
│   ├── __init__.py
│   ├── main.py         # App creation, static/template routes
│   ├── auth.py         # JWT auth & password utilities
│   ├── sim_api.py      # Simulation endpoints (/start, /action, /ws)
│   ├── models.py       # Pydantic schemas & SQLAlchemy models
│   ├── db.py           # DB session & Redis client setup
│   ├── dependencies.py # FastAPI dependencies (get_current_user, guest)
│   └── config.py       # Settings (loads from .env)
├── workers/            # Background tasks & simulation logic
│   ├── __init__.py
│   ├── tasks.py        # RQ task definitions
│   ├── simulation_manager.py # Core simulation engine
│   └── rq_config.py    # Queue & Redis connection for tasks
└── venv/               # (ignored) Python virtual environment
```

---

## Technology Stack

- **Backend**: Python 3.11+, FastAPI
- **Async Tasks**: RQ & rq-scheduler
- **Data Store**: PostgreSQL, Redis
- **Realtime**: WebSockets via FastAPI
- **Auth**: JWT (PyJWT or python-jose)
- **Containerization**: Docker, Docker Compose

---

## Prerequisites

- Docker & Docker Compose installed
- (Optional) Python 3.11+ for local development
- Access to a PostgreSQL instance (or use the Docker service)

---

## Environment Variables

Create a `.env` in the project root with at least the following:

```dotenv
# Database
DB_NAME=your_db_name
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=your_db_host        # e.g. postgres or localhost
DB_PORT=5432

# JWT
SECRET_KEY=your_strong_secret
JWT_EXPIRATION_MINUTES=60

# OpenAI (if using LLM integrations)
OPENAI_API_KEY=sk-...

# Redis (optional override)
# REDIS_URL=redis://redis:6379/0
```

> **Note:** Ensure `.env` is listed in `.gitignore`.

---

## Installation & Build

1. **Clone the repository**

   ```bash
   git clone <repo-url>
   cd cyber_sim_game
   ```

2. **Build Docker images**
   ```bash
   docker-compose build
   ```

---

## Running the Platform

Start all services:

```bash
docker-compose up
```

Services:

- **sim-api**: FastAPI server on `:8000`
- **sim-redis**: Redis state store and message broker
- **sim-worker**: RQ worker for background jobs
- **sim-scheduler**: rq-scheduler for periodic tasks
- **sim-postgres**: PostgreSQL database (if defined)

---

### Access Points

- API docs (Swagger UI): `http://localhost:8000/docs`
- Landing / Login: `http://localhost:8000/`
- Simulation UI: `http://localhost:8000/simulation`

---

## Development & Debugging

- **Live reload**: `sim-api` uses Uvicorn `--reload` for code changes in `app/` and `workers/`.
- **Inspect logs**: In the terminal running `docker-compose up`, watch for errors.
- **Shell into a container**:
  ```bash
  docker ps
  docker exec -it sim-worker bash
  pip list
  ```
- **Redis CLI**:
  ```bash
  docker exec -it sim-redis redis-cli
  KEYS sim_state:*
  GET sim_state:<simulation_id>
  SUBSCRIBE sim_events:* (Ctrl+C to exit)
  ```
- **Check RQ queues**:
  ```bash
  docker exec -it sim-redis redis-cli
  LLEN rq:queue:default
  ```
- **Browser dev tools**:
  - **Console**: JS errors & WebSocket logs
  - **Network**: HTTP & WS frames

---

## Extending the Backend

- **Add API routes**: Create new routers under `app/` and include in `main.py`.
- **New tasks**: Define in `workers/tasks.py` and enqueue via RQ.
- **Update simulation logic**: Modify `workers/simulation_manager.py`.

---

## Scalability Considerations

For production-level scale:

- Deploy multiple instances of `api`, `worker`, and `scheduler` behind a load balancer.
- Use managed Redis and PostgreSQL clusters.
- Implement distributed WebSocket management (e.g., RedisPubSub or a broker).
- Orchestrate with Kubernetes or another platform.

---

## Contributing

1. Fork this repo
2. Create a feature branch: `git checkout -b feature/YourFeature`
3. Commit changes: `git commit -m "Add your feature"`
4. Push branch: `git push origin feature/YourFeature`
5. Open a Pull Request

---

<sup>Made with ❤️ by the Enter The Breach dev team</sup>

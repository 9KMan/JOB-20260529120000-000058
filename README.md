# Multi-Tenant SaaS Backend

Production-ready FastAPI backend for a multi-tenant SaaS platform with JWT authentication, PostgreSQL row-level security, WebSocket support, and Apache Kafka event streaming.

## Architecture

```
                     ┌─────────────────────────┐
                     │      FastAPI Backend    │
                     │  (Uvicorn / Gunicorn)   │
                     └──────────┬──────────────┘
                                │
               ┌────────────────┼────────────────┐
               │                │                │
         ┌─────▼──────┐   ┌─────▼──────┐   ┌─────▼──────┐
         │  REST API  │   │  WebSocket  │   │  Auth API   │
         │  /api/v1   │   │  /ws/v1     │   │  /auth/*    │
         └────────────┘   └─────────────┘   └─────────────┘
```

**Multi-tenancy:** PostgreSQL Row-Level Security (RLS) with `tenant_id` foreign key on every table. Tenant context injected via middleware from JWT claims. Zero cross-tenant data leakage.

## Tech Stack

| Component | Technology |
|-----------|------------|
| Framework | FastAPI 0.110+ (Python 3.11+) |
| Database | PostgreSQL 16 + SQLAlchemy 2.0 async |
| Auth | JWT (python-jose) + argon2 password hashing |
| WebSocket | FastAPI WebSockets + Redis Pub/Sub |
| Events | Apache Kafka (aiokafka) |
| Containerization | Docker + docker-compose |

## Installation

```bash
# Clone and install dependencies
cd backend
pip install -r requirements.txt

# Start development stack
docker compose up -d

# Run migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Environment Variables

```env
# Application
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000
SECRET_KEY=<your-secret-key>

# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/saas_db

# JWT
JWT_SECRET_KEY=<your-jwt-secret>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC_PREFIX=saas

# Redis
REDIS_URL=redis://localhost:6379/0

# CORS
ALLOWED_ORIGINS=http://localhost:3000
```

## Data Model

### Tenants
| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| name | VARCHAR(255) | Tenant company name |
| slug | VARCHAR(63) | Unique URL-safe identifier |
| plan | VARCHAR(31) | Subscription plan |
| created_at | TIMESTAMPTZ | Creation timestamp |

### Users (tenant-scoped via RLS)
| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| tenant_id | UUID | FK to tenants |
| email | VARCHAR(255) | Unique per tenant |
| password_hash | VARCHAR(255) | argon2 hash |
| role | VARCHAR(31) | admin/member/viewer |
| is_active | BOOLEAN | Soft-delete flag |
| created_at | TIMESTAMPTZ | Creation timestamp |

### Projects (tenant-scoped via RLS)
| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| tenant_id | UUID | FK to tenants |
| name | VARCHAR(255) | Project name |
| description | TEXT | Optional description |
| status | VARCHAR(31) | active/inactive |
| created_at | TIMESTAMPTZ | Creation timestamp |

## CLI Reference

### Authentication
```bash
# Register new tenant + admin user
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_name": "Acme Corp",
    "tenant_slug": "acme",
    "admin_email": "admin@acme.com",
    "admin_password": "securepassword123"
  }'

# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -c cookies.txt \
  -d '{"email": "admin@acme.com", "password": "securepassword123"}'

# Refresh token
curl -X POST http://localhost:8000/auth/refresh \
  -b cookies.txt
```

### Users API
```bash
# List users (requires JWT)
curl http://localhost:8000/api/v1/users \
  -H "Authorization: Bearer <token>"

# Create user (admin only)
curl -X POST http://localhost:8000/api/v1/users \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@acme.com", "password": "pass123", "role": "member"}'

# Get/Update/Delete user
curl http://localhost:8000/api/v1/users/{id} -H "Authorization: Bearer <token>"
curl -X PUT http://localhost:8000/api/v1/users/{id} -H "Authorization: Bearer <token>" -d '{"role": "admin"}'
curl -X DELETE http://localhost:8000/api/v1/users/{id} -H "Authorization: Bearer <token>"
```

### Projects API
```bash
# List/Create projects
curl http://localhost:8000/api/v1/projects -H "Authorization: Bearer <token>"
curl -X POST http://localhost:8000/api/v1/projects \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "New Project", "description": "A new project"}'

# Get/Update/Delete project
curl http://localhost:8000/api/v1/projects/{id} -H "Authorization: Bearer <token>"
curl -X PUT http://localhost:8000/api/v1/projects/{id} -H "Authorization: Bearer <token>" -d '{"status": "inactive"}'
curl -X DELETE http://localhost:8000/api/v1/projects/{id} -H "Authorization: Bearer <token>"
```

## Quality Guarantees

- **Authentication:** JWT with 15-min access tokens, 7-day refresh tokens, argon2 password hashing
- **Multi-tenancy:** RLS enforced at database level — application bugs cannot cause cross-tenant data leakage
- **API Documentation:** OpenAPI 3.1 auto-generated at `/docs`
- **Event Streaming:** Kafka events published on every entity create/update/delete
- **Containerization:** Full dev stack in one `docker compose up`
- **Testing:** pytest with async fixtures and >80% coverage on core services

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app factory
│   ├── config.py            # pydantic-settings
│   ├── database.py          # async SQLAlchemy
│   ├── models/              # SQLAlchemy models
│   ├── schemas/             # Pydantic v2 schemas
│   ├── api/                 # Route modules
│   ├── ws/                  # WebSocket handlers
│   ├── services/            # Business logic
│   ├── kafka/               # Kafka producer/consumer
│   └── middleware/          # Tenant context
├── tests/                   # pytest fixtures + tests
├── alembic/                 # Database migrations
├── Dockerfile               # Multi-stage build
├── docker-compose.yml       # Full dev stack
└── requirements.txt         # Python dependencies
```

## Output Format

All REST API responses follow this format:

**Single resource:**
```json
{
  "id": "uuid",
  "tenant_id": "uuid",
  "name": "string",
  "...": "..."
}
```

**Paginated list:**
```json
{
  "data": [...],
  "total": 100,
  "page": 1,
  "per_page": 20
}
```

## Limitations

- Refresh tokens stored in HTTP-only cookies (no token rotation)
- WebSocket fan-out via Redis (requires Redis for multi-worker deployments)
- Kafka consumer runs as async task (not a separate service)
- No API rate limiting (recommend nginx/API gateway for production)
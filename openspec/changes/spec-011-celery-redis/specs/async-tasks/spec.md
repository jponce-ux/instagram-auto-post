# Async Tasks Specification

## Purpose

Sistema de colas para ejecutar operaciones pesadas en background, liberando el request-response cycle de FastAPI.

## Requirements

### Requirement: Redis Message Broker

The system MUST provide a Redis container acting as the Celery message broker.

The system SHALL configure Redis with healthcheck and proper network connectivity.

#### Scenario: Redis container healthy

- GIVEN docker-compose is running
- WHEN Redis container starts
- THEN healthcheck passes
- AND Celery can connect to `redis://redis:6379/0`

#### Scenario: Redis connection refused

- GIVEN Redis container is not running
- WHEN Celery worker tries to connect
- THEN worker MUST log connection error and retry

---

### Requirement: Celery Worker Service

The system MUST provide a Celery worker container sharing the FastAPI codebase.

The worker SHALL have access to PostgreSQL and MinIO services.

#### Scenario: Worker starts successfully

- GIVEN docker-compose is running with redis healthy
- WHEN worker container starts
- THEN Celery registers in logs
- AND worker connects to Redis broker

#### Scenario: Worker accesses database

- GIVEN a task requires database access
- WHEN the task executes
- THEN worker MUST connect to PostgreSQL via `DATABASE_URL`
- AND SQLAlchemy async operations work correctly

#### Scenario: Worker accesses MinIO

- GIVEN a task requires file storage
- WHEN the task executes
- THEN worker MUST connect to MinIO
- AND presigned URLs can be generated

---

### Requirement: Celery Configuration

The system MUST configure Celery app in `app/worker.py` with broker URL from environment.

The configuration SHALL support async code execution via `asgiref` or asyncio loop management.

#### Scenario: Broker URL configured

- GIVEN `CELERY_BROKER_URL` environment variable is set
- WHEN Celery app initializes
- THEN broker URL reads from environment
- AND connection established to Redis

#### Scenario: Async task execution

- GIVEN a task uses async SQLAlchemy code
- WHEN task is dispatched
- THEN task MUST execute without blocking
- AND async operations complete successfully

---

### Requirement: Debug Task

The system MUST provide a `debug_task` function that validates the queue subsystem.

The task SHALL accept a name parameter and return a greeting message.

#### Scenario: Debug task executes

- GIVEN Celery worker is running
- WHEN `debug_task.delay("test")` is called from FastAPI
- THEN task is queued in Redis
- AND worker executes task
- AND logs show execution with greeting message

#### Scenario: Debug task from API endpoint

- GIVEN a FastAPI endpoint calls `debug_task.delay(name)`
- WHEN HTTP request is made
- THEN response returns immediately (non-blocking)
- AND task executes in background

---

### Requirement: Task Dispatch from FastAPI

The system MUST allow FastAPI endpoints to dispatch tasks to the queue.

Tasks dispatched SHALL not block the HTTP response.

#### Scenario: Non-blocking dispatch

- GIVEN an endpoint imports `debug_task`
- WHEN endpoint calls `debug_task.delay(data)`
- THEN HTTP response returns immediately
- AND task_id is returned in response (optional)

#### Scenario: Task status check

- GIVEN a task was dispatched with `task_id`
- WHEN client checks task status via AsyncResult
- THEN status (PENDING/STARTED/SUCCESS/FAILURE) is returned
# Nexus Application

## About

nexus is the application monorepo for the Nexus platform. It contains the independently versioned backend services responsible for authentication and user profile management.

## Architecture

The application follows a microservices architecture with separate Auth and Profile services. An API Gateway provides a single entry point and routes requests to the responsible service. Event-driven communication is used for workflows that do not require a synchronous response: Auth publishes user registration events and Profile consumes them to create profile data. Both services persist application data in PostgreSQL.

See [Application Architecture](docs/architecture.md) for the container view.

## Features

- User registration
- Login and bearer token authentication
- Stateless logout
- Current user identity lookup
- Profile retrieval and display name updates
- Avatar upload through Cloudinary
- Asynchronous profile creation from user registration events
- Health checks and Prometheus-compatible metrics endpoints

See [API Documentation](docs/api.md) for endpoints and request examples.

## Tech Stack

- Python 3.13
- FastAPI
- Pydantic and Pydantic Settings
- Psycopg 3 and PostgreSQL
- Boto3 and Amazon SQS
- Cloudinary
- uv
- Ruff and pytest
- Docker

# auth-service

FastAPI service for user authentication.

## Endpoints

- `GET /health` - readiness/liveness health check
- `POST /register` - create user and publish `UserRegistered` event to SQS
- `POST /login` - return bearer token
- `POST /logout` - stateless logout acknowledgement
- `GET /me` - return authenticated user claims

Public route through Envoy Gateway: `/auth/*` rewrites to this service's `/*`.

## Runtime configuration

Expected from Kubernetes Secret `auth-service-secrets`, synced by ESO from `kv/auth-service/config`:

- `DATABASE_URL` - PostgreSQL connection string
- `JWT_SECRET` - HMAC token secret shared with profile-service
- `USER_EVENTS_QUEUE_URL` - SQS queue URL for user lifecycle events
- `TOKEN_TTL_SECONDS` - optional, defaults to `3600`

SQS access is expected through the `apps/auth-service` Kubernetes service account IRSA role.

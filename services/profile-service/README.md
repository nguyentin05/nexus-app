# profile-service

FastAPI service for user profile data and avatar upload.

## Endpoints

- `GET /health` - readiness/liveness health check
- `GET /me` - return current user's profile
- `PATCH /me` - update display name
- `POST /avatar` - upload avatar image to Cloudinary and store `avatar_url`

Public route through Envoy Gateway: `/profile/*` rewrites to this service's `/*`.

## Runtime configuration

Expected from Kubernetes Secret `profile-service-secrets`, synced by ESO from `kv/profile-service/config`:

- `DATABASE_URL` - PostgreSQL connection string
- `JWT_SECRET` - same HMAC token secret used by auth-service
- `USER_EVENTS_QUEUE_URL` - SQS queue URL consumed for `UserRegistered` events
- `CLOUDINARY_CLOUD_NAME`
- `CLOUDINARY_API_KEY`
- `CLOUDINARY_API_SECRET`
- `CLOUDINARY_FOLDER` - optional, defaults to `nexus/avatars`

SQS access is expected through the `apps/profile-service` Kubernetes service account IRSA role.

# Nexus API

## Overview

Routes requests:

| Public prefix | Service |
| --- | --- |
| /auth | auth-service |
| /profile | profile-service |

## Authentication

Protected endpoints require a bearer token:

```http
Authorization: Bearer <access-token>
```

## Public API

### Authentication

| Method | Path | Authentication | Description |
| --- | --- | --- | --- |
| POST | /auth/register | No | Register an account |
| POST | /auth/login | No | Authenticate and issue an access token |
| POST | /auth/logout | Yes | End the current client session |
| GET | /auth/me | Yes | Return identity data from the token |

### Profile

| Method | Path | Authentication | Description |
| --- | --- | --- | --- |
| GET | /profile/me | Yes | Get the current user profile |
| PATCH | /profile/me | Yes | Update the display name |
| POST | /profile/avatar | Yes | Upload and replace the avatar |

## Operational API

Each service exposes:

| Path | Purpose |
| --- | --- |
| / | Basic service information |
| /health | Health check |
| /metrics | metrics |

## Common Status Codes

| Status | Meaning |
| --- | --- |
| 200 | Request completed |
| 201 | Account created |
| 400 | Invalid request |
| 401 | Missing or invalid bearer token |
| 409 | Email already registered |
| 413 | Avatar exceeds the size limit |
| 422 | Request validation failed |
| 502 | Cloudinary request failed |
| 503 | Required external integration is unavailable |

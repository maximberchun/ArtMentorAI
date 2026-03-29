## ArtMentorAI MVP API contracts (stable)

**Contract version**: `v1` (frozen on 2026-03-17)  
**Applies to**: current backend routes under `/auth`, `/analysis`, `/profile`, `/portfolio`

This document is the **source of truth** for frontend integration. Until an explicit `v2` is introduced, we will avoid breaking changes by:

- only adding **optional** fields
- only adding **new endpoints**
- not changing meanings/types of existing fields

If a breaking change is required, it will ship under a versioned path (example: `/v2/...`) or with an explicit coordinated contract bump.

### Conventions

- **Base URL**: whatever the server is hosted on (example: `http://localhost:8000`)
- **Auth**:
  - Protected endpoints require `Authorization: Bearer <supabase_access_token>`
  - Token verification uses Supabase JWT (RS256, JWKS, issuer/audience checks)
  - `user_id` is derived from token subject (`sub`) and is not trusted from client payloads
- **Timestamps**: ISO-8601 strings (UTC)
- **Errors**: FastAPI default error format, typically:

```json
{ "detail": "Error message" }
```

---

## Auth API

### GET `/auth/me`

Return identity extracted from the verified Supabase access token.

**Headers**

- **`Authorization`** (required): `Bearer <supabase_access_token>`

**Status codes**

- **200**: success
- **401**: missing/invalid/expired token

**Response (200) — `AuthUser`**

```json
{
  "user_id": "9f6dd1db-1f67-4ef2-9f0f-2cbd5d0475f8",
  "email": "alice@example.com",
  "role": "authenticated"
}
```

### POST `/auth/google/url`

Return Supabase authorize URL for Google OAuth server-side flow bootstrap.

**Status codes**

- **200**: success

**Response (200)**

```json
{
  "url": "https://<project-ref>.supabase.co/auth/v1/authorize?provider=google",
  "instructions": "Redirect user to this URL. After auth Supabase redirects to your redirect_uri with ?code=xxx"
}
```

### POST `/auth/google/callback`

Exchange OAuth `code` for Supabase tokens.

**Query params**

- **`code`** (string, required): OAuth authorization code

**Status codes**

- **200**: success
- **500**: upstream exchange failure

**Response (200)**

```json
{
  "access_token": "<jwt>",
  "refresh_token": "<refresh-token-or-null>",
  "expires_in": 3600,
  "token_type": "bearer",
  "user_id": "9f6dd1db-1f67-4ef2-9f0f-2cbd5d0475f8"
}
```

### GET `/auth/providers`

List configured OAuth providers.

**Status codes**

- **200**: success

**Response (200)**

```json
{
  "providers": [
    {
      "id": "google",
      "name": "Google",
      "url": "https://<project-ref>.supabase.co/auth/v1/authorize?provider=google"
    }
  ]
}
```

---

## Analysis API

### POST `/analysis/critique`

Generate a structured critique from an uploaded image and/or a text prompt. The authenticated user is derived from the bearer token and used for profile lookup + vector-memory scoping.

**Content-Type**: `multipart/form-data`

**Headers**

- **`Authorization`** (required): `Bearer <supabase_access_token>`

**Form fields**

- **`file`** (file, optional): image file upload
- **`user_input`** (string, optional): user text comment/description/question

**Validation / status codes**

- **200**: success
- **401**: missing/invalid/expired token
- **400**: invalid file (extension/MIME/empty file) or invalid request
- **413**: file too large (exceeds `MAX_FILE_SIZE_MB`)
- **415**: unsupported media type (must be image/*)
- **422**: both `file` and `user_input` missing/blank
- **500**: unexpected server error

**Response (200) — `AnalysisResponse`**

```json
{
  "summary": "Figure drawing with good proportions but perspective errors",
  "score": 7,
  "technical_errors": ["Inconsistent linear perspective", "Right arm slightly disproportionate"],
  "constructive_advice": "Practice head construction with guide lines..."
}
```

**Notes**

- This endpoint returns the critique even if vector DB storage is unavailable (memory is “best effort”).

---

## Profile API

### GET `/profile/me`

Fetch profile for the authenticated user.

**Headers**

- **`Authorization`** (required): `Bearer <supabase_access_token>`

**Status codes**

- **200**: success
- **401**: missing/invalid/expired token
- **404**: profile not found
- **500**: storage error

**Response (200) — `UserProfile`**

```json
{
  "user_id": "alice",
  "goals": ["draw portraits"],
  "preferred_styles": ["anime"],
  "disliked_styles": [],
  "favorite_artists": ["Sargent"],
  "experience_level": "beginner"
}
```

### PUT `/profile/me`

Create or update profile for the authenticated user.

**Headers**

- **`Authorization`** (required): `Bearer <supabase_access_token>`

**Request body (JSON) — `UserProfileBase`**

```json
{
  "goals": ["draw portraits"],
  "preferred_styles": ["anime"],
  "disliked_styles": [],
  "favorite_artists": ["Sargent"],
  "experience_level": "beginner"
}
```

**Status codes**

- **200**: success
- **401**: missing/invalid/expired token
- **500**: storage error

**Response (200) — `UserProfile`**

Same shape as GET.

### Deprecated compatibility routes

- `GET /profile/{user_id}` and `PUT /profile/{user_id}` are deprecated.
- They only work when `{user_id}` equals the authenticated token user id; otherwise:
  - **403**: forbidden

---

## Portfolio API

### POST `/portfolio/upload`

Bulk upload portfolio images for a user. This stores **metadata** (not image bytes) as `portfolio_item` points in the vector DB.

**Content-Type**: `multipart/form-data`

**Headers**

- **`Authorization`** (required): `Bearer <supabase_access_token>`

**Form fields**

- **`files`** (file[], required): one or more image files
- **`tags`** (string, optional): comma-separated tags applied to all files (example: `"figure, anatomy, graphite"`)

**Status codes**

- **200**: success
- **401**: missing/invalid/expired token
- **400**: invalid request / missing filenames / zero files
- **413**: file too large
- **415**: unsupported media type
- **500**: server error saving to vector DB
- **503**: vector DB unavailable

**Response (200) — `PortfolioUploadResponse`**

```json
{ "ids": ["6d7b4f3d-1c2b-4d83-8f05-2a7c9bd7a2f1", "b9d9c1b3-2d0d-4c1f-8f5a-77c55d0f2b0e"] }
```

### GET `/portfolio/history/me`

Get unified history for the authenticated user (critiques + portfolio items), newest first.

**Headers**

- **`Authorization`** (required): `Bearer <supabase_access_token>`

**Query params**

- **`limit`** (int, default 100, min 1, max 500)
- **`type_filter`** (string, optional): `"critique"` or `"portfolio_item"`

**Status codes**

- **200**: success
- **401**: missing/invalid/expired token
- **500**: server error retrieving from vector DB
- **503**: vector DB unavailable

**Response (200) — `PortfolioHistoryItem[]`**

Each list entry is a normalized view of the Qdrant payload with an `id` attached.

Critique example:

```json
{
  "id": "f0e2b48d-0b64-4ae6-9c58-8b6c2f2b4f55",
  "type": "critique",
  "user_id": "alice",
  "filename": "sketch.png",
  "timestamp": "2026-03-17T10:11:12.123456+00:00",
  "tags": [],
  "description": "",
  "score": 7,
  "summary": "Figure drawing with good proportions but perspective errors",
  "advice": "Practice head construction with guide lines...",
  "goals_snapshot": "Goals: draw portraits | Experience level: beginner",
  "level_estimate": 4
}
```

Portfolio item example:

```json
{
  "id": "6d7b4f3d-1c2b-4d83-8f05-2a7c9bd7a2f1",
  "type": "portfolio_item",
  "user_id": "alice",
  "filename": "study-01.jpg",
  "timestamp": "2026-03-17T10:11:12.123456+00:00",
  "tags": ["figure", "anatomy"],
  "description": "",
  "score": null,
  "summary": null,
  "advice": null,
  "goals_snapshot": null,
  "level_estimate": null
}
```

### GET `/portfolio/item/{item_id}`

Fetch one stored item (critique or portfolio item) by id for the authenticated user.

**Headers**

- **`Authorization`** (required): `Bearer <supabase_access_token>`

**Status codes**

- **200**: success
- **401**: missing/invalid/expired token
- **404**: not found
- **503**: vector DB unavailable

**Response (200)**

Same shape as a single `PortfolioHistoryItem`.

### Deprecated compatibility route

- `GET /portfolio/history/{user_id}` is deprecated.
- It only works when `{user_id}` equals the authenticated token user id; otherwise:
  - **403**: forbidden


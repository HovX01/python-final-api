# Product Requirements Document (PRD)
**Project**: Subscription Platform – API Backend  
**Backend**: Django + Django REST Framework + PostgreSQL  
**Infra**: Docker (docker-compose)  
**Frontend**: React SPA (or similar) – separate project, consumes this API  
**Payments**: Stripe (subscriptions)  
**Auth**: JWT (access + refresh) using `djangorestframework-simplejwt`  
- Access token: short-lived, stored in React memory  
- Refresh token: long-lived, stored in secure httpOnly cookie

---

## 0. Glossary

- **User** – Authenticated end user of the platform.  
- **Admin** – Internal user with elevated permissions.  
- **User type** – Business classification: `basic` or `pro`.  
- **App** – A domain object the user creates and manages (limited by plan).  
- **Subscription** – Stripe subscription state mapped to `user_type`.  
- **Client** – Frontend React SPA consuming the API.  

---

## 1. Overview & Objectives

### 1.1 Problem

We need a reusable backend service that:

- Provides secure registration, login, email verification, and password reset.  
- Integrates with Stripe for recurring subscription billing.  
- Enforces usage limits (number of Apps) based on user type: `basic` vs `pro`.  
- Allows admins to control user access (disable/enable).  
- Exposes a clean REST API for a React SPA frontend.  

### 1.2 Objectives

- Provide an API-only backend using Django + DRF + JWT auth.  
- Support Stripe subscriptions that automatically upgrade/downgrade users.  
- Enforce App limits per user type.  
- Run in Docker and be easy to deploy across environments.  

### 1.3 KPIs

- Email verification rate after registration.  
- Conversion rate from `basic` to `pro`.  
- Number of active subscriptions and churn rate.  
- Error rate for auth and billing endpoints.  

---

## 2. Scope

### 2.1 In Scope (v1)

- API-only backend, no server-rendered HTML.  
- JWT-based auth (SimpleJWT) with:
  - Short-lived access tokens (e.g. 5–15 minutes).  
  - Long-lived refresh tokens (days/weeks) stored in httpOnly cookie.  
- Email verification and password reset.  
- User types: `basic`, `pro`.  
- Admin user management (disable/enable).  
- Stripe subscription integration (no PayPal or other gateways).  
- App CRUD with limits based on user type:
  - one-to-many: owner → Apps  
  - many-to-many: collaborator access via join table.  
- Dockerization (docker-compose for Dev/Prod scaffold).  

### 2.2 Out of Scope (v1)

- Frontend React SPA implementation.  
- Multi-gateway or onetime payments.  
- Multi-tenant / team billing hierarchy.  
- Complex analytics UI.  

---

## 3. High-Level Architecture

### 3.1 Components

- **Django API service**
  - Django + DRF  
  - Auth: SimpleJWT  
  - Stripe integration (Checkout + Billing Portal + Webhooks)  
  - PostgreSQL database  

- **PostgreSQL**
  - Primary persistence for users, apps, subscriptions, tokens metadata.  

- **React SPA (external)**
  - Handles UI, routing, forms, and calls Django API endpoints.  
  - Manages access token in memory (e.g. React Context, Redux, or React Query).  

- **Stripe**
  - Products and Prices for subscription plans (e.g. `pro_monthly`).  
  - Checkout for new subscriptions.  
  - Billing Portal for managing payment methods and cancellation.  
  - Webhooks back to Django for subscription lifecycle events.  

### 3.2 Auth Architecture (Option 1)

- **Access token**:
  - JWT, short-lived (5–15 minutes).  
  - Returned in login response JSON.  
  - Stored in React memory only (not persisted in localStorage/sessionStorage).  
  - Sent on each authenticated API request via `Authorization: Bearer <access_token>`.  

- **Refresh token**:
  - JWT, longer-lived (days or weeks).  
  - Sent from backend as httpOnly, Secure cookie (`refresh_token` or similar).  
  - Not accessible via JavaScript.  
  - Used by `/auth/token/refresh/` endpoint to obtain new access tokens.  

- **CORS & Cookies**:
  - API configured with CORS to allow the React domain.  
  - Refresh endpoint expects the refresh token sent via cookie.  

---

## 4. Users & Roles

### 4.1 Roles

1. **Guest**
   - Not authenticated.
   - Can register, log in, request password reset.

2. **User**
   - Authenticated end user.
   - Has `user_type` (`basic`, `pro`).
   - Owns Apps and may have collaborator access to other Apps.
   - Controls subscription via Stripe flows.

3. **Admin**
   - Authenticated with `is_staff` (or dedicated role).  
   - Can list users, view subscriptions, and disable/enable users.  

---

## 5. Data Model (Conceptual)

### 5.1 User

Core Django `User`-like model (either custom or extending `AbstractUser`):

- `id` (UUID or integer)  
- `email` (unique, required; used for login)  
- `password_hash`  
- `is_active` (bool; indicates email verified)  
- `is_staff` (bool; admin flag)  
- `is_disabled_by_admin` (bool; default `False`)  
- `user_type` (enum: `basic`, `pro`; default `basic`)  
- `date_joined`  
- `last_login`  

### 5.2 Subscription

- `id`  
- `user` (FK → User, one-to-one or one-to-many; assume latest active subscription is current)  
- `provider` (fixed string: `'stripe'`)  
- `stripe_customer_id`  
- `stripe_subscription_id`  
- `status` (enum, subset of Stripe statuses: `incomplete`, `trialing`, `active`, `past_due`, `canceled`, `incomplete_expired`)  
- `plan_id` (internal ID: e.g. `pro_monthly`)  
- `current_period_start` (datetime)  
- `current_period_end` (datetime)  
- `cancel_at_period_end` (bool)  
- `created_at`, `updated_at`  

### 5.3 App

- `id`  
- `name`  
- `description` (optional)  
- `owner` (FK → User)  
- `created_at`, `updated_at`  

### 5.4 AppUser (Many-to-Many)

Used to model collaborators on Apps.

- `id`  
- `app` (FK → App)  
- `user` (FK → User)  
- `role` (enum: `owner`, `editor`, `viewer`)  
- `invited_at`  

In Django this will be configured as:

- `App.collaborators = ManyToManyField(User, through=AppUser, related_name="shared_apps")`  

### 5.5 User Type Limits

Configuration (in Django settings or database):

| User type | Max owned apps | Description                     |
|-----------|----------------|---------------------------------|
| basic     | 3              | Free/low tier                   |
| pro       | 50             | Higher or configurable limit    |

Over-limit behavior:

- If `owned_apps_count >= max_owned_apps(user_type)`, the user:
  - Cannot create new Apps (API returns `403` with `APP_LIMIT_REACHED`).  
  - Still can view/update existing Apps.  

---

## 6. Authentication & Security Requirements

### 6.1 Registration & Email Verification

**Endpoint:** `POST /api/v1/auth/register/`

- Request body:
  ```json
  {
    "email": "user@example.com",
    "password": "MySecurePass123"
  }
  ```
- Behavior:
  - Create user with:
    - `email` normalized
    - `is_active = False`
    - `user_type = 'basic'`
  - Generate an email verification token (time-limited, single-use).  
  - Send verification email with link referencing frontend route:
    - e.g. `https://frontend.app/verify-email?token=...`  

**Endpoint:** `POST /api/v1/auth/verify-email/`

- Request body:
  ```json
  {
    "token": "VERIFICATION_TOKEN"
  }
  ```
- Behavior:
  - Validate token.
  - Activate user (`is_active = True`) if valid.  

### 6.2 Login

**Endpoint:** `POST /api/v1/auth/login/`

- Request:
  ```json
  {
    "email": "user@example.com",
    "password": "MySecurePass123"
  }
  ```
- Behavior:
  - Check credentials.
  - Ensure:
    - `is_active` is `True` (email verified).  
    - `is_disabled_by_admin` is `False`.  
  - Use SimpleJWT to:
    - Generate `access` token (short-lived).  
    - Generate `refresh` token (long-lived).  
  - Response:
    - JSON: includes only the `access` token and basic user info.  
    - Set `refresh` token as httpOnly secure cookie:  
      - Name: `refresh_token` (configurable).  
      - Attributes:
        - `HttpOnly`
        - `Secure` (enabled in production)
        - `SameSite=Lax` or `Strict` (configurable)
        - Reasonable `Max-Age` (e.g. 7–30 days)

- Response example:
  ```json
  {
    "access": "ACCESS.JWT.TOKEN",
    "user": {
      "id": 1,
      "email": "user@example.com",
      "user_type": "basic"
    }
  }
  ```

### 6.3 Token Refresh

**Endpoint:** `POST /api/v1/auth/token/refresh/`

- Request:
  - No body required; refresh token is sent via httpOnly cookie.  
- Behavior:
  - Read refresh token from cookie.
  - Validate token via SimpleJWT.
  - If valid:
    - Issue new `access` token.
  - If invalid/expired:
    - Return `401 Unauthorized`.  

- Response:
  ```json
  {
    "access": "NEW.ACCESS.JWT.TOKEN"
  }
  ```

### 6.4 Logout

**Endpoint:** `POST /api/v1/auth/logout/`

- Behavior:
  - Clear refresh token cookie (set expired cookie).  
  - Optionally blacklist refresh token (if using SimpleJWT blacklist).  

### 6.5 Forgot & Reset Password

**Endpoint:** `POST /api/v1/auth/forgot-password/`

- Request:
  ```json
  { "email": "user@example.com" }
  ```
- Behavior:
  - Generate reset token.
  - Send email with frontend link:
    - `https://frontend.app/reset-password?token=...`  

**Endpoint:** `POST /api/v1/auth/reset-password/`

- Request:
  ```json
  {
    "token": "RESET_TOKEN",
    "new_password": "NewSecurePass123"
  }
  ```
- Behavior:
  - Validate token.
  - Set new password.
  - Invalidate old sessions if necessary.

### 6.6 Current User

**Endpoint:** `GET /api/v1/me/`

- Auth: `Authorization: Bearer <access_token>`  
- Response includes:
  - `id`, `email`, `user_type`, `is_disabled_by_admin`  
  - Subscription summary fields if present.

### 6.7 Security Considerations

- Passwords stored with Django’s password hasher.  
- JWT signing key stored securely in environment variable.  
- Short access token lifetime to minimize risk.  
- Refresh token stored only in httpOnly cookie (not accessible to JS).  
- Rate limiting for login and sensitive endpoints (optional v1, recommended later).  
- Force HTTPS in production.  

---

## 7. Subscriptions & Billing (Stripe Only)

### 7.1 Plan & Price Configuration

- Stripe products and prices are configured in Stripe dashboard.  
- Backend maintains mapping:
  - Example:
    - `pro_monthly` → `price_xxx`  
- `plan_id` refers to internal ID like `pro_monthly`.

### 7.2 Create Stripe Checkout Session

**Endpoint:** `POST /api/v1/subscriptions/stripe/checkout/`

- Auth required.  
- Request:
  ```json
  {
    "plan_id": "pro_monthly",
    "success_url": "https://frontend.app/billing/success?session_id={CHECKOUT_SESSION_ID}",
    "cancel_url": "https://frontend.app/billing/canceled"
  }
  ```
- Behavior:
  - Validate `plan_id`.  
  - Ensure a `stripe_customer_id` exists for user (create if not).  
  - Create a Stripe Checkout Session in subscription mode.  
- Response:
  ```json
  { "checkout_url": "https://checkout.stripe.com/c/session_..." }
  ```

### 7.3 Stripe Billing Portal

**Endpoint:** `POST /api/v1/subscriptions/stripe/portal/`

- Auth required.  
- Behavior:
  - Create a Stripe Billing Portal Session for the user’s `stripe_customer_id`.  
  - Return URL for frontend.  
- Response:
  ```json
  { "url": "https://billing.stripe.com/session/..." }
  ```

### 7.4 Stripe Webhook

**Endpoint:** `POST /api/v1/subscriptions/stripe/webhook/`

- No auth, secured via Stripe signature header.  
- Must handle at minimum:
  - `checkout.session.completed`  
  - `customer.subscription.created`  
  - `customer.subscription.updated`  
  - `customer.subscription.deleted`  
  - `invoice.payment_succeeded`  
  - `invoice.payment_failed`  

**Behavior:**

- On active or trialing subscription:
  - Upsert `Subscription` record (link to user via `stripe_customer_id`).  
  - Set:
    - `status = 'active'` or `trialing`  
    - `plan_id`  
    - `current_period_start` / `current_period_end`  
  - Set `user.user_type = 'pro'`.  

- On canceled or expired subscription:
  - Update `Subscription.status` accordingly.
  - Decide downgrade logic:
    - Either:
      - Downgrade `user.user_type = 'basic'` immediately on cancellation, OR
      - Wait until `current_period_end` (config option).  

- On payment failure:
  - Update `Subscription.status = 'past_due'`.  
  - (Optional) Send email about payment issue.  

### 7.5 Get Current Subscription

**Endpoint:** `GET /api/v1/subscriptions/me/`

- Auth required.  
- Response:
  ```json
  {
    "status": "active",
    "plan_id": "pro_monthly",
    "current_period_start": "2025-11-01T00:00:00Z",
    "current_period_end": "2025-12-01T00:00:00Z",
    "cancel_at_period_end": false
  }
  ```

---

## 8. Apps & Limits

### 8.1 List Apps

**Endpoint:** `GET /api/v1/apps/`

- Returns apps where:
  - `owner = current_user` OR
  - `current_user` is in `AppUser` collaborators.  
- Pagination: standard DRF pagination (page/size or limit/offset).

### 8.2 Create App (Limit Enforcement)

**Endpoint:** `POST /api/v1/apps/`

- Request:
  ```json
  { "name": "My First App", "description": "Optional description" }
  ```
- Behavior:
  - Count Apps where `owner = current_user`.  
  - Get max allowed apps for `current_user.user_type`.  
  - If `count >= max`:
    - Return `403 Forbidden`:
      ```json
      {
        "code": "APP_LIMIT_REACHED",
        "message": "You have reached the maximum number of apps for your plan."
      }
      ```
  - Else, create new App, set `owner = current_user`.  

### 8.3 Retrieve / Update / Delete App

**Endpoints:**
- `GET /api/v1/apps/{id}/`
- `PATCH /api/v1/apps/{id}/`
- `DELETE /api/v1/apps/{id}/`

**Permissions:**

- Owner or collaborator:
  - `GET`: owner or any collaborator.  
  - `PATCH`/`DELETE`: owner or collaborators with `role` allowing edits.  

### 8.4 Manage Collaborators

**List collaborators**
- `GET /api/v1/apps/{id}/collaborators/`

**Add collaborator**
- `POST /api/v1/apps/{id}/collaborators/`
  ```json
  { "user_id": 123, "role": "editor" }
  ```

**Remove collaborator**
- `DELETE /api/v1/apps/{id}/collaborators/{user_id}/`

Only the owner can change collaborators in v1.

---

## 9. Admin Features

### 9.1 List Users

**Endpoint:** `GET /api/v1/admin/users/`

- Admin-only (permission restricted).  
- Filters:
  - `email` (partial)  
  - `user_type`  
  - `is_disabled_by_admin`  
  - `subscription_status` (optional)  

### 9.2 Get User Detail

**Endpoint:** `GET /api/v1/admin/users/{id}/`

- Returns user info including:
  - Basic profile (email, user_type, flags)  
  - Subscription summary  
  - Counts of owned apps  

### 9.3 Update User (Disable/Enable)

**Endpoint:** `PATCH /api/v1/admin/users/{id}/`

- Request:
  ```json
  { "is_disabled_by_admin": true }
  ```
- Behavior:
  - When `true`:
    - User login fails.  
    - All authenticated requests fail via permission check.  

---

## 10. API Design Guidelines

- **Base Path:** `/api/v1/`.  
- **Content type:** JSON for requests/responses.  
- **Auth:** `Authorization: Bearer <access_token>`.  
- **Error format:**
  ```json
  {
    "code": "ERROR_CODE",
    "message": "Human-readable message."
  }
  ```
- **Pagination:**  
  - Include `count`, `next`, `previous`, `results` fields (DRF default).  

Generate and serve OpenAPI/Swagger docs (e.g. using `drf-spectacular`) at:

- `GET /api/schema/` (raw schema)  
- `GET /api/schema/swagger-ui/` (UI)  

---

## 11. Environments & Docker

### 11.1 Environments

- `local`: Dev env, DEBUG = True, Stripe test keys.  
- `staging`: Pre-prod env, DEBUG = False, Stripe test keys.  
- `production`: Live env, DEBUG = False, Stripe live keys.  

### 11.2 docker-compose (High-Level)

Services:

- `web` – Django API (gunicorn).  
- `db` – PostgreSQL.  
- `nginx` – Reverse proxy (optional in dev, required in prod).  
- `worker` (optional) – Celery worker for async tasks like sending emails.  

Important environment variables:

- `DJANGO_SECRET_KEY`  
- `DEBUG`  
- `DATABASE_URL` or equivalent `POSTGRES_*` variables  
- `ALLOWED_HOSTS`  
- `STRIPE_SECRET_KEY`  
- `STRIPE_WEBHOOK_SECRET`  
- `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_PORT`, `EMAIL_USE_TLS`  

---

## 12. Security & Compliance

- Strong password policy (configurable).  
- Secure JWT secret and Stripe keys via environment variables.  
- HTTPS enforced in production (via Nginx/Load Balancer).  
- Validate Stripe webhook signature for all events.  
- Limit logged PII; do not log raw tokens.  
- Optionally support user account deletion / anonymization for privacy compliance.  

---

## 13. Logging, Monitoring & Analytics

- Log:
  - Auth events (login success/failure, registration, verification).  
  - Subscription lifecycle events (created/updated/canceled, payment failures).  
  - App limit enforcement (when user hits limit).  
- Health check endpoint:
  - `GET /health/` → returns `200` with basic status.  

---

## 14. Acceptance Criteria (MVP)

1. **Auth & User Flow**
   - New user can register, receive verification email, verify, and log in.  
   - Login returns access token in JSON and sets refresh token in httpOnly cookie.  
   - React app can call `/auth/token/refresh/` and get new access token using cookie.  
   - Logout clears refresh cookie and blocks further refresh.  

2. **Admin**
   - Admin can list users and disable any user.  
   - Disabled user cannot log in or access authenticated endpoints.  

3. **Stripe Integration**
   - User can initiate Stripe Checkout from frontend, complete payment, and webhook upgrades user to `pro`.  
   - Billing Portal URL can be generated for existing Stripe customers.  
   - Canceling subscription via Stripe results in user being downgraded to `basic` according to configured logic.  

4. **App Limits**
   - `basic` users cannot create more than configured number of Apps.  
   - `pro` users have higher or effectively unlimited limit.  
   - Over-limit attempts return clear error response.  

5. **Documentation**
   - OpenAPI/Swagger documentation generated and accessible.  
   - Endpoints implement described behavior and data contracts.  

This PRD defines the full behavior for a Django API backend with JWT auth (SimpleJWT), Stripe subscriptions, and usage limits, designed to be consumed by a React SPA.

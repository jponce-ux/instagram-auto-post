# Router Auth Specification

## Purpose

Authentication-based routing logic that guards access to protected resources and redirects users based on their authentication state. All JWT validation uses cookie-based authentication (not HTTPBearer headers).

---

## Requirements

### Requirement: Root Route Conditional Response

The system MUST respond to GET / with different content based on user authentication state.

The system SHALL check for a valid JWT in the `access_token` cookie.

#### Scenario: Authenticated user accesses root

- GIVEN user has valid JWT in cookie named `access_token`
- WHEN user accesses GET /
- THEN system returns 303 redirect to /dashboard

#### Scenario: Unauthenticated user accesses root

- GIVEN user has no or invalid JWT in cookie
- WHEN user accesses GET /
- THEN system returns 200 with landing.html template

---

### Requirement: Dashboard Protection

The system MUST protect all routes under /dashboard with authentication.

#### Scenario: Authenticated user accesses dashboard

- GIVEN user has valid JWT in cookie named `access_token`
- WHEN user accesses any route under /dashboard
- THEN system allows access to the requested route

#### Scenario: Unauthenticated user accesses dashboard

- GIVEN user has no or invalid JWT in cookie
- WHEN user accesses any route under /dashboard
- THEN system returns 303 redirect to / (login page)

---

### Requirement: Auth Route Guards

The system MUST prevent authenticated users from accessing login/register pages.

#### Scenario: Authenticated user accesses login

- GIVEN user has valid JWT in cookie named `access_token`
- WHEN user accesses GET /auth/login
- THEN system returns 303 redirect to /dashboard

#### Scenario: Authenticated user accesses register

- GIVEN user has valid JWT in cookie named `access_token`
- WHEN user accesses GET /auth/register
- THEN system returns 303 redirect to /dashboard

#### Scenario: Unauthenticated user accesses login

- GIVEN user has no or invalid JWT in cookie
- WHEN user accesses GET /auth/login
- THEN system allows access to login page

#### Scenario: Unauthenticated user accesses register

- GIVEN user has no or invalid JWT in cookie
- WHEN user accesses GET /auth/register
- THEN system allows access to registration page

---

### Requirement: Logout

The system MUST provide a logout mechanism that clears the authentication cookie.

#### Scenario: User logs out

- GIVEN user is authenticated
- WHEN user accesses GET /auth/logout
- THEN system clears `access_token` cookie
- AND returns 303 redirect to /

---

### Requirement: Landing Page

The system MUST display a landing page for unauthenticated users at the root route.

#### Scenario: Landing page content

- GIVEN user has no or invalid JWT
- WHEN user accesses GET /
- THEN system displays landing.html
- AND landing page provides login/register CTAs
- NOTE: Full content defined in SPEC-017; this spec only requires the page to exist and be served

---

## Coverage

- Happy paths: Covered (authenticated/unauthenticated scenarios for each route)
- Edge cases: Covered (redirect loops prevented via auth guards on login/register)
- Error states: Covered (invalid JWT treated as unauthenticated)

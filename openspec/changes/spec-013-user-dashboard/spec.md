# User Dashboard Specification

## Purpose

The User Dashboard is the central visual interface for authenticated users to manage linked Instagram accounts and create posts. It provides a protected, mobile-first HTML interface using Jinja2 templates, Tailwind CSS (CDN), and HTMX for interactive features.

## Requirements

### Requirement: Dashboard Authentication Guard

The system SHALL protect all dashboard routes by requiring a valid JWT token in the Authorization header. Requests without a valid JWT MUST receive a 401 Unauthorized response.

#### Scenario: Authenticated user accesses dashboard

- GIVEN a user has a valid JWT token
- WHEN the user sends GET /dashboard with Authorization: Bearer <token>
- THEN the system returns 200 OK with the dashboard HTML

#### Scenario: Unauthenticated user denied access

- GIVEN a user has no JWT token or an invalid one
- WHEN the user sends GET /dashboard
- THEN the system returns 401 Unauthorized

### Requirement: Linked Accounts Display

The system SHALL display all Instagram accounts linked to the authenticated user in the Accounts section, showing account username and connection status.

#### Scenario: User views linked accounts

- GIVEN a user is authenticated with linked InstagramAccounts
- WHEN the user navigates to GET /dashboard/accounts
- THEN the system displays a list showing each account's username and connection status

#### Scenario: User has no linked accounts

- GIVEN a user is authenticated with no linked accounts
- WHEN the user navigates to GET /dashboard/accounts
- THEN the system displays an empty state with a "Connect your first account" message

### Requirement: OAuth Connection Flow

The system SHALL provide an OAuth button that redirects the user to Instagram's authorization endpoint to link a new account.

#### Scenario: User initiates OAuth flow

- GIVEN a user is authenticated and clicks "Connect Instagram Account"
- WHEN the user clicks the OAuth button
- THEN the system redirects to Instagram OAuth authorization URL

### Requirement: Post Creation Form

The system SHALL provide a post creation form with image upload and caption fields. The form MUST use HTMX for async submission and support progressive file upload.

#### Scenario: User creates post with image and caption

- GIVEN a user is authenticated and viewing the post form
- WHEN the user selects an image file, enters a caption, and submits
- THEN the system uploads the image to storage, creates a post with PENDING status, and displays success feedback

#### Scenario: User submits form without image

- GIVEN a user is authenticated and viewing the post form
- WHEN the user submits without selecting an image
- THEN the system displays a validation error "Image is required"

#### Scenario: User submits form without caption

- GIVEN a user is authenticated and viewing the post form
- WHEN the user submits with an image but no caption
- THEN the system creates the post (caption MAY be empty per Instagram API)

### Requirement: Post History Display

The system SHALL display a list of the user's posts with their current status (PENDING, PROCESSING, PUBLISHED, FAILED).

#### Scenario: User views post history

- GIVEN a user is authenticated with existing posts
- WHEN the user navigates to the dashboard history section
- THEN the system displays all posts with image thumbnail, caption preview, and status badge

#### Scenario: User has no posts

- GIVEN a user is authenticated with no posts
- WHEN the user navigates to the dashboard history section
- THEN the system displays an empty state "No posts yet"

### Requirement: HTMX Polling for History Updates

The system SHALL automatically refresh the post history every 10 seconds using HTMX polling to display status updates without page reload.

#### Scenario: History auto-refreshes

- GIVEN a user is authenticated and viewing the history section
- WHEN 10 seconds elapse
- THEN HTMX triggers GET /dashboard/posts/feed and swaps updated content

### Requirement: Mobile Responsive Design

The system SHALL render the dashboard interface responsively on mobile devices using Tailwind CSS with mobile-first breakpoints.

#### Scenario: Dashboard renders on mobile

- GIVEN a user accesses the dashboard from a mobile viewport (< 768px)
- WHEN the page loads
- THEN elements stack vertically, use appropriate touch targets (44px min), and hide non-essential elements

#### Scenario: Dashboard renders on desktop

- GIVEN a user accesses the dashboard from a desktop viewport (>= 768px)
- WHEN the page loads
- THEN elements display in multi-column layout with full feature visibility

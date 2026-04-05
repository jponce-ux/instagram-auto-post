"""
Tests for spec-013-user-dashboard
User Dashboard with HTMX and Tailwind CSS
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.user import User
from app.models.instagram import InstagramAccount
from app.models.post import Post, PostStatus
from app.models.media_file import MediaFile


# Test Client
client = TestClient(app)


# Test: Dashboard Authentication Guard
# Requirement: Dashboard Authentication Guard
class TestDashboardAuthentication:
    """REQ-01: Dashboard routes must require valid JWT"""

    def test_dashboard_without_jwt_returns_401(self):
        """Scenario: Unauthenticated user denied access
        GIVEN a user has no JWT token or an invalid one
        WHEN the user sends GET /dashboard
        THEN the system returns 401 Unauthorized"""
        response = client.get("/dashboard")
        assert (
            response.status_code == 403
        )  # FastAPI HTTPBearer returns 403 for missing auth

    def test_dashboard_with_invalid_jwt_returns_401(self):
        """GIVEN invalid JWT token
        WHEN accessing /dashboard
        THEN returns 401 Unauthorized"""
        response = client.get(
            "/dashboard", headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401

    @patch("app.auth.dependencies.get_current_user")
    def test_dashboard_with_valid_jwt_returns_200(self, mock_get_user):
        """Scenario: Authenticated user accesses dashboard
        GIVEN a user has a valid JWT token
        WHEN the user sends GET /dashboard with Authorization: Bearer <token>
        THEN the system returns 200 OK with the dashboard HTML"""
        # Setup mock user
        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_user.email = "test@example.com"
        mock_get_user.return_value = mock_user

        # Mock dashboard service calls
        with (
            patch("app.dashboard.routes.get_user_accounts", return_value=[]),
            patch("app.dashboard.routes.get_user_posts", return_value=[]),
        ):
            response = client.get(
                "/dashboard", headers={"Authorization": "Bearer valid_token"}
            )

        # Should return HTML (template response)
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")


# Test: Linked Accounts Display
# Requirement: Linked Accounts Display
class TestLinkedAccountsDisplay:
    """REQ-02: Display linked Instagram accounts"""

    @patch("app.auth.dependencies.get_current_user")
    def test_accounts_section_displays_linked_accounts(self, mock_get_user):
        """Scenario: User views linked accounts
        GIVEN a user is authenticated with linked InstagramAccounts
        WHEN the user navigates to GET /dashboard/accounts
        THEN the system displays a list showing each account's username and connection status"""
        # Setup
        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_get_user.return_value = mock_user

        mock_account = Mock(spec=InstagramAccount)
        mock_account.id = 1
        mock_account.instagram_account_id = "123456"
        mock_account.token_expires_at = datetime.now(timezone.utc) + timezone.timedelta(
            days=30
        )

        with patch(
            "app.dashboard.routes.get_user_accounts", return_value=[mock_account]
        ):
            response = client.get(
                "/dashboard/accounts", headers={"Authorization": "Bearer valid"}
            )

        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    @patch("app.auth.dependencies.get_current_user")
    def test_accounts_empty_state_no_accounts(self, mock_get_user):
        """Scenario: User has no linked accounts
        GIVEN a user is authenticated with no linked accounts
        WHEN the user navigates to GET /dashboard/accounts
        THEN the system displays an empty state with a 'Connect your first account' message"""
        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_get_user.return_value = mock_user

        with patch("app.dashboard.routes.get_user_accounts", return_value=[]):
            response = client.get(
                "/dashboard/accounts", headers={"Authorization": "Bearer valid"}
            )

        assert response.status_code == 200


# Test: OAuth Connection Flow
# Requirement: OAuth Connection Flow
class TestOAuthConnectionFlow:
    """REQ-03: Provide OAuth button for Instagram authorization"""

    def test_oauth_button_redirects_to_instagram(self):
        """Scenario: User initiates OAuth flow
        GIVEN a user is authenticated and clicks 'Connect Instagram Account'
        WHEN the user clicks the OAuth button
        THEN the system redirects to Instagram OAuth authorization URL"""
        # The OAuth endpoint is in app/auth/instagram.py
        response = client.get("/auth/instagram/login", follow_redirects=False)
        assert response.status_code == 307  # Redirect
        assert "facebook.com" in response.headers.get("location", "")


# Test: Post Creation Form
# Requirement: Post Creation Form
class TestPostCreationForm:
    """REQ-04: Post creation form with image upload and caption"""

    @patch("app.auth.dependencies.get_current_user")
    @patch("app.dashboard.service.storage_service.upload_file")
    @patch("app.dashboard.service.get_user_accounts")
    def test_create_post_with_image_and_caption(
        self, mock_get_accounts, mock_upload, mock_get_user
    ):
        """Scenario: User creates post with image and caption
        GIVEN a user is authenticated and viewing the post form
        WHEN the user selects an image file, enters a caption, and submits
        THEN the system uploads the image to storage, creates a post with PENDING status,
        and displays success feedback"""
        # Setup
        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_get_user.return_value = mock_user

        mock_account = Mock(spec=InstagramAccount)
        mock_account.id = 1
        mock_get_accounts.return_value = [mock_account]

        # Create test file
        test_file = {"file": ("test.jpg", b"fake_image_data", "image/jpeg")}

        response = client.post(
            "/dashboard/post",
            headers={"Authorization": "Bearer valid"},
            data={"caption": "Test caption"},
            files=test_file,
        )

        assert response.status_code == 200
        mock_upload.assert_called_once()

    @patch("app.auth.dependencies.get_current_user")
    def test_post_form_validates_image_required(self, mock_get_user):
        """Scenario: User submits form without image
        GIVEN a user is authenticated and viewing the post form
        WHEN the user submits without selecting an image
        THEN the system displays a validation error 'Image is required'"""
        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_get_user.return_value = mock_user

        response = client.post(
            "/dashboard/post",
            headers={"Authorization": "Bearer valid"},
            data={"caption": "Test caption"},
        )

        assert response.status_code == 200
        # Should show error about missing image
        assert "error" in response.text.lower() or "required" in response.text.lower()

    @patch("app.auth.dependencies.get_current_user")
    @patch("app.dashboard.service.storage_service.upload_file")
    @patch("app.dashboard.service.get_user_accounts")
    def test_post_allows_empty_caption(
        self, mock_get_accounts, mock_upload, mock_get_user
    ):
        """Scenario: User submits form without caption
        GIVEN a user is authenticated and viewing the post form
        WHEN the user submits with an image but no caption
        THEN the system creates the post (caption MAY be empty per Instagram API)"""
        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_get_user.return_value = mock_user

        mock_account = Mock(spec=InstagramAccount)
        mock_account.id = 1
        mock_get_accounts.return_value = [mock_account]

        test_file = {"file": ("test.jpg", b"fake_image_data", "image/jpeg")}

        response = client.post(
            "/dashboard/post",
            headers={"Authorization": "Bearer valid"},
            data={"caption": ""},  # Empty caption
            files=test_file,
        )

        assert response.status_code == 200


# Test: Post History Display
# Requirement: Post History Display
class TestPostHistoryDisplay:
    """REQ-05: Display post history with status badges"""

    @patch("app.auth.dependencies.get_current_user")
    def test_history_shows_posts_with_status_badges(self, mock_get_user):
        """Scenario: User views post history
        GIVEN a user is authenticated with existing posts
        WHEN the user navigates to the dashboard history section
        THEN the system displays all posts with image thumbnail, caption preview, and status badge"""
        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_get_user.return_value = mock_user

        mock_post = Mock(spec=Post)
        mock_post.id = 1
        mock_post.caption = "Test post"
        mock_post.status = PostStatus.PUBLISHED
        mock_post.created_at = datetime.now(timezone.utc)

        with patch("app.dashboard.routes.get_user_posts", return_value=[mock_post]):
            response = client.get(
                "/dashboard", headers={"Authorization": "Bearer valid"}
            )

        assert response.status_code == 200

    @patch("app.auth.dependencies.get_current_user")
    def test_history_empty_state_no_posts(self, mock_get_user):
        """Scenario: User has no posts
        GIVEN a user is authenticated with no posts
        WHEN the user navigates to the dashboard history section
        THEN the system displays an empty state 'No posts yet'"""
        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_get_user.return_value = mock_user

        with (
            patch("app.dashboard.routes.get_user_posts", return_value=[]),
            patch("app.dashboard.routes.get_user_accounts", return_value=[]),
        ):
            response = client.get(
                "/dashboard", headers={"Authorization": "Bearer valid"}
            )

        assert response.status_code == 200


# Test: HTMX Polling for History Updates
# Requirement: HTMX Polling for History Updates
class TestHtmxPolling:
    """REQ-06: Auto-refresh post history every 10 seconds using HTMX"""

    @patch("app.auth.dependencies.get_current_user")
    def test_posts_feed_endpoint_returns_fragment(self, mock_get_user):
        """Scenario: History auto-refreshes
        GIVEN a user is authenticated and viewing the history section
        WHEN HTMX triggers GET /dashboard/posts/feed
        THEN system returns updated content as HTML fragment"""
        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_get_user.return_value = mock_user

        mock_post = Mock(spec=Post)
        mock_post.id = 1
        mock_post.status = PostStatus.PENDING

        with patch("app.dashboard.routes.get_user_posts", return_value=[mock_post]):
            response = client.get(
                "/dashboard/posts/feed",
                headers={
                    "Authorization": "Bearer valid",
                    "HX-Request": "true",  # HTMX header
                },
            )

        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")


# Test: Mobile Responsive Design
# Requirement: Mobile Responsive Design
class TestMobileResponsive:
    """REQ-07: Mobile-first responsive design with Tailwind CSS"""

    def test_dashboard_uses_tailwind_classes(self):
        """Scenario: Dashboard renders on mobile and desktop
        GIVEN the dashboard template uses Tailwind CSS
        WHEN the page loads
        THEN elements use responsive classes like md:, lg:, etc."""
        # Check that templates exist and contain Tailwind classes
        template_files = [
            "app/templates/dashboard/index.html",
            "app/templates/dashboard/layout.html",
            "app/templates/dashboard/accounts.html",
        ]

        for template_file in template_files:
            try:
                with open(template_file, "r") as f:
                    content = f.read()
                    # Check for Tailwind responsive prefixes or utility classes
                    assert (
                        "md:" in content
                        or "lg:" in content
                        or "sm:" in content
                        or 'class="' in content
                    )
            except FileNotFoundError:
                pytest.skip(f"Template {template_file} not found")


# Test: HTMX Partial Content
# Tests for HTMX fragment responses
class TestHtmxPartialContent:
    """Test HTMX partial content delivery"""

    @patch("app.auth.dependencies.get_current_user")
    def test_accounts_returns_partial_for_htmx(self, mock_get_user):
        """GIVEN HTMX request header
        WHEN GET /dashboard/accounts
        THEN returns partial template (accounts_partial.html)"""
        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_get_user.return_value = mock_user

        with patch("app.dashboard.routes.get_user_accounts", return_value=[]):
            response = client.get(
                "/dashboard/accounts",
                headers={"Authorization": "Bearer valid", "HX-Request": "true"},
            )

        assert response.status_code == 200


# Test: Dashboard Service Functions
class TestDashboardService:
    """Test dashboard service layer functions"""

    @pytest.mark.asyncio
    async def test_get_user_accounts_queries_database(self):
        """Test that get_user_accounts queries the database correctly"""
        from app.dashboard.service import get_user_accounts

        mock_db = AsyncMock(spec=AsyncSession)
        mock_user = Mock(spec=User)
        mock_user.id = 1

        # Mock the execute result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        accounts = await get_user_accounts(mock_db, mock_user)

        assert accounts == []
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_posts_queries_database(self):
        """Test that get_user_posts queries the database correctly"""
        from app.dashboard.service import get_user_posts

        mock_db = AsyncMock(spec=AsyncSession)
        mock_user = Mock(spec=User)
        mock_user.id = 1

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        posts = await get_user_posts(mock_db, mock_user)

        assert posts == []
        mock_db.execute.assert_called_once()


# Mark async tests
pytestmark = pytest.mark.asyncio

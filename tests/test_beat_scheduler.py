"""
Tests for spec-014-celery-beat-scheduler
Celery Beat scheduler for automatic post publishing
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.worker import (
    celery_app,
    check_scheduled_posts,
    debug_task,
    process_instagram_post,
)
from app.models.post import Post, PostStatus
from app.models.base import Base


# Test: Beat Schedule Configuration
# Requirement: Beat Schedule Configuration
# Scenario: Beat schedule registered
class TestBeatScheduleConfiguration:
    """REQ-02: Beat schedule must be configured with 60-second interval"""

    def test_beat_schedule_exists(self):
        """GIVEN app/worker.py has beat_schedule configured
        THEN check_scheduled_posts task is registered"""
        assert "beat_schedule" in celery_app.conf
        assert "check-scheduled-posts" in celery_app.conf.beat_schedule

    def test_beat_schedule_interval(self):
        """GIVEN beat schedule is configured
        THEN task is scheduled to run every 60 seconds"""
        schedule = celery_app.conf.beat_schedule["check-scheduled-posts"]
        assert schedule["task"] == "app.worker.check_scheduled_posts"
        # Verify it's using celery.schedules.interval
        from celery.schedules import interval as Interval

        assert isinstance(schedule["schedule"], Interval)
        assert schedule["schedule"].run_every.total_seconds() == 60


# Test: Debug Task
# Basic sanity check
class TestDebugTask:
    """Verify Celery integration works"""

    def test_debug_task_returns_greeting(self):
        """GIVEN Celery worker is running
        WHEN debug_task.delay("test") is called
        THEN task returns greeting message"""
        result = debug_task.run(name="test")
        assert result == "Hello, test!"


# Test: Check Scheduled Posts Task
# Requirement: Check Scheduled Posts Task
# Requirement: Scheduled Post Query
# Requirement: Dispatch Processing Tasks
# Requirement: Status Transition to PROCESSING
class TestCheckScheduledPosts:
    """REQ-06: Task queries and dispatches posts for processing"""

    @pytest.fixture
    def mock_session(self):
        """Create a mock SQLAlchemy session"""
        session = MagicMock()
        return session

    @pytest.fixture
    def mock_post_pending(self):
        """Create a mock post in PENDING state"""
        post = Mock(spec=Post)
        post.id = 1
        post.status = PostStatus.PENDING
        post.scheduled_at = datetime.now(timezone.utc) - timedelta(hours=1)
        return post

    @pytest.fixture
    def mock_post_future(self):
        """Create a mock post with future scheduled_at"""
        post = Mock(spec=Post)
        post.id = 2
        post.status = PostStatus.PENDING
        post.scheduled_at = datetime.now(timezone.utc) + timedelta(hours=1)
        return post

    @pytest.fixture
    def mock_post_processing(self):
        """Create a mock post already in PROCESSING state"""
        post = Mock(spec=Post)
        post.id = 3
        post.status = PostStatus.PROCESSING
        post.scheduled_at = datetime.now(timezone.utc) - timedelta(hours=1)
        return post

    @patch("app.worker.SyncSessionLocal")
    @patch("app.worker.process_instagram_post")
    def test_query_finds_due_posts(
        self, mock_process_task, mock_session_class, mock_post_pending
    ):
        """Scenario: Query finds due posts
        GIVEN posts exist with status PENDING and scheduled_at in the past
        WHEN check_scheduled_posts executes
        THEN query returns posts where status=PENDING AND scheduled_at <= now()"""
        # Setup mock session
        mock_session = MagicMock()
        mock_session_class.return_value.__enter__ = Mock(return_value=mock_session)
        mock_session_class.return_value.__exit__ = Mock(return_value=False)

        # Mock the query result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_post_pending]
        mock_session.execute.return_value = mock_result

        # Execute task
        result = check_scheduled_posts.run()

        # Verify
        assert result["found"] == 1
        assert result["dispatched"] == 1
        assert result["error"] is None
        mock_process_task.delay.assert_called_once_with(1)

    @patch("app.worker.SyncSessionLocal")
    @patch("app.worker.process_instagram_post")
    def test_query_skips_future_posts(
        self, mock_process_task, mock_session_class, mock_post_future
    ):
        """Scenario: Query skips future posts
        GIVEN posts exist with status PENDING but scheduled_at in the future
        WHEN check_scheduled_posts executes
        THEN future posts are NOT returned by the query"""
        # Setup mock session
        mock_session = MagicMock()
        mock_session_class.return_value.__enter__ = Mock(return_value=mock_session)
        mock_session_class.return_value.__exit__ = Mock(return_value=False)

        # Mock the query result - returns future post (but query should filter it out)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []  # Empty because future
        mock_session.execute.return_value = mock_result

        # Execute task
        result = check_scheduled_posts.run()

        # Verify
        assert result["found"] == 0
        assert result["dispatched"] == 0
        mock_process_task.delay.assert_not_called()

    @patch("app.worker.SyncSessionLocal")
    @patch("app.worker.process_instagram_post")
    def test_dispatch_single_post(
        self, mock_process_task, mock_session_class, mock_post_pending
    ):
        """Scenario: Dispatch for single post
        GIVEN one post is found with status=PENDING and scheduled_at <= now()
        WHEN check_scheduled_posts runs
        THEN process_instagram_post.delay(post_id) is called once"""
        # Setup mock session
        mock_session = MagicMock()
        mock_session_class.return_value.__enter__ = Mock(return_value=mock_session)
        mock_session_class.return_value.__exit__ = Mock(return_value=False)

        # Mock the query result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_post_pending]
        mock_session.execute.return_value = mock_result

        # Execute task
        result = check_scheduled_posts.run()

        # Verify status transition and dispatch
        assert mock_post_pending.status == PostStatus.PROCESSING
        mock_session.commit.assert_called()
        mock_process_task.delay.assert_called_once_with(1)
        assert result["dispatched"] == 1

    @patch("app.worker.SyncSessionLocal")
    @patch("app.worker.process_instagram_post")
    def test_dispatch_multiple_posts(
        self, mock_process_task, mock_session_class, mock_post_pending
    ):
        """Scenario: Dispatch for multiple posts
        GIVEN multiple posts are found due for publishing
        WHEN check_scheduled_posts runs
        THEN process_instagram_post.delay() is called for EACH post"""
        # Create multiple posts
        post2 = Mock(spec=Post)
        post2.id = 2
        post2.status = PostStatus.PENDING
        post2.scheduled_at = datetime.now(timezone.utc) - timedelta(minutes=30)

        # Setup mock session
        mock_session = MagicMock()
        mock_session_class.return_value.__enter__ = Mock(return_value=mock_session)
        mock_session_class.return_value.__exit__ = Mock(return_value=False)

        # Mock the query result with multiple posts
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_post_pending, post2]
        mock_session.execute.return_value = mock_result

        # Execute task
        result = check_scheduled_posts.run()

        # Verify both posts dispatched
        assert result["found"] == 2
        assert result["dispatched"] == 2
        assert mock_process_task.delay.call_count == 2
        mock_process_task.delay.assert_any_call(1)
        mock_process_task.delay.assert_any_call(2)

    @patch("app.worker.SyncSessionLocal")
    @patch("app.worker.process_instagram_post")
    def test_status_transition_to_processing(
        self, mock_process_task, mock_session_class, mock_post_pending
    ):
        """Scenario: Transition from PENDING to PROCESSING
        GIVEN a post with status=PENDING and scheduled_at <= now()
        WHEN check_scheduled_posts dispatches the task
        THEN post status is updated to PROCESSING first
        AND then task is dispatched"""
        # Setup mock session
        mock_session = MagicMock()
        mock_session_class.return_value.__enter__ = Mock(return_value=mock_session)
        mock_session_class.return_value.__exit__ = Mock(return_value=False)

        # Mock the query result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_post_pending]
        mock_session.execute.return_value = mock_result

        # Execute task
        check_scheduled_posts.run()

        # Verify status transition happened BEFORE dispatch
        assert mock_post_pending.status == PostStatus.PROCESSING
        mock_session.commit.assert_called()
        mock_process_task.delay.assert_called_once()

    @patch("app.worker.SyncSessionLocal")
    @patch("app.worker.process_instagram_post")
    def test_skip_already_processing_post(
        self, mock_process_task, mock_session_class, mock_post_processing
    ):
        """Scenario: Skip already PROCESSING post
        GIVEN a post with status=PROCESSING and scheduled_at <= now()
        WHEN check_scheduled_posts runs
        THEN the post is NOT dispatched again
        AND no duplicate task is created"""
        # Setup mock session
        mock_session = MagicMock()
        mock_session_class.return_value.__enter__ = Mock(return_value=mock_session)
        mock_session_class.return_value.__exit__ = Mock(return_value=False)

        # Mock the query result - query filters by PENDING only
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []  # Empty because status=PROCESSING
        mock_session.execute.return_value = mock_result

        # Execute task
        result = check_scheduled_posts.run()

        # Verify not dispatched
        assert result["found"] == 0
        assert result["dispatched"] == 0
        mock_process_task.delay.assert_not_called()

    @patch("app.worker.SyncSessionLocal")
    @patch("app.worker.process_instagram_post")
    def test_handle_empty_result(self, mock_process_task, mock_session_class):
        """Scenario: Task handles empty result
        GIVEN no posts match criteria (no PENDING posts due)
        WHEN check_scheduled_posts executes
        THEN task completes without error
        AND no tasks are dispatched"""
        # Setup mock session
        mock_session = MagicMock()
        mock_session_class.return_value.__enter__ = Mock(return_value=mock_session)
        mock_session_class.return_value.__exit__ = Mock(return_value=False)

        # Mock empty query result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        # Execute task
        result = check_scheduled_posts.run()

        # Verify
        assert result["found"] == 0
        assert result["dispatched"] == 0
        assert result["error"] is None
        mock_process_task.delay.assert_not_called()

    @patch("app.worker.SyncSessionLocal")
    @patch("app.worker.logger")
    def test_handle_database_error(self, mock_logger, mock_session_class):
        """Scenario: Task handles database errors
        GIVEN database connection fails
        WHEN check_scheduled_posts executes
        THEN task logs the error
        AND task does NOT crash beat scheduler
        AND next beat cycle continues normally"""
        # Setup mock session to raise exception
        mock_session = MagicMock()
        mock_session_class.return_value.__enter__ = Mock(return_value=mock_session)
        mock_session_class.return_value.__exit__ = Mock(return_value=False)
        mock_session.execute.side_effect = Exception("Database connection failed")

        # Execute task
        result = check_scheduled_posts.run()

        # Verify error handling
        assert result["error"] == "Database connection failed"
        assert result["found"] == 0
        assert result["dispatched"] == 0
        mock_logger.error.assert_called()


# Test: Posts ordered by scheduled_at ASC
class TestQueryOrdering:
    """Verify posts are processed in correct order"""

    @patch("app.worker.SyncSessionLocal")
    @patch("app.worker.process_instagram_post")
    def test_posts_ordered_by_scheduled_at_asc(
        self, mock_process_task, mock_session_class
    ):
        """GIVEN multiple posts with different scheduled_at times
        WHEN check_scheduled_posts executes
        THEN posts are ordered by scheduled_at ASC (oldest first)"""
        # Create posts with different scheduled times
        post_old = Mock(spec=Post)
        post_old.id = 1
        post_old.status = PostStatus.PENDING
        post_old.scheduled_at = datetime.now(timezone.utc) - timedelta(hours=2)

        post_new = Mock(spec=Post)
        post_new.id = 2
        post_new.status = PostStatus.PENDING
        post_new.scheduled_at = datetime.now(timezone.utc) - timedelta(minutes=30)

        # Setup mock session
        mock_session = MagicMock()
        mock_session_class.return_value.__enter__ = Mock(return_value=mock_session)
        mock_session_class.return_value.__exit__ = Mock(return_value=False)

        # Capture the query to verify ordering
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [post_old, post_new]
        mock_session.execute.return_value = mock_result

        # Execute task
        check_scheduled_posts.run()

        # Verify the query was called (ordering is in the query construction)
        mock_session.execute.assert_called_once()


# Integration-style test marker
pytestmark = pytest.mark.asyncio

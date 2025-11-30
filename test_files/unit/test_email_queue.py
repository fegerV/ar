"""
Unit tests for persistent email queue.
Tests enqueue/dequeue logic, retry increments, DB persistence, and error handling.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from app.services.email_queue import EmailQueue, EmailQueueJob, EmailJobStatus


class TestEmailQueueJob:
    """Test EmailQueueJob class."""
    
    def test_job_creation(self):
        """Test basic job creation."""
        job = EmailQueueJob(
            to=["test@example.com"],
            subject="Test Subject",
            body="Test body",
            html="<p>Test body</p>",
        )
        
        assert job.id is not None
        assert job.to == ["test@example.com"]
        assert job.subject == "Test Subject"
        assert job.body == "Test body"
        assert job.html == "<p>Test body</p>"
        assert job.status == EmailJobStatus.PENDING
        assert job.attempts == 0
        assert job.last_error is None
    
    def test_job_to_dict(self):
        """Test job serialization to dictionary."""
        job = EmailQueueJob(
            to=["test@example.com", "other@example.com"],
            subject="Test",
            body="Body",
            html="<p>HTML</p>",
            template_id="template-123",
            variables={"name": "John"},
        )
        
        job_dict = job.to_dict()
        
        assert job_dict["id"] == job.id
        assert job_dict["to"] == "test@example.com,other@example.com"
        assert job_dict["subject"] == "Test"
        assert job_dict["body"] == "Body"
        assert job_dict["html"] == "<p>HTML</p>"
        assert job_dict["template_id"] == "template-123"
        assert '"name": "John"' in job_dict["variables"]
        assert job_dict["status"] == "pending"
        assert job_dict["attempts"] == 0
    
    def test_job_from_dict(self):
        """Test job deserialization from dictionary."""
        job_dict = {
            "id": "test-job-123",
            "recipient_to": "test@example.com,other@example.com",
            "subject": "Test",
            "body": "Body",
            "html": "<p>HTML</p>",
            "template_id": "template-123",
            "variables": '{"name": "John"}',
            "status": "pending",
            "attempts": 2,
            "last_error": "SMTP error",
            "created_at": datetime(2024, 1, 1, 12, 0, 0),
            "updated_at": datetime(2024, 1, 1, 12, 5, 0),
        }
        
        job = EmailQueueJob.from_dict(job_dict)
        
        assert job.id == "test-job-123"
        assert job.to == ["test@example.com", "other@example.com"]
        assert job.subject == "Test"
        assert job.body == "Body"
        assert job.html == "<p>HTML</p>"
        assert job.template_id == "template-123"
        assert job.variables == {"name": "John"}
        assert job.status == EmailJobStatus.PENDING
        assert job.attempts == 2
        assert job.last_error == "SMTP error"


class TestEmailQueue:
    """Test EmailQueue class."""
    
    @pytest.fixture
    def mock_email_service(self):
        """Mock email service."""
        service = Mock()
        service._send_email_sync = AsyncMock()
        return service
    
    @pytest.fixture
    def mock_database(self):
        """Mock database."""
        db = Mock()
        db.create_email_job = Mock(return_value="job-123")
        db.update_email_job = Mock(return_value=True)
        db.get_next_pending_email_job = Mock(return_value=None)
        db.get_all_pending_email_jobs = Mock(return_value=[])
        db.get_failed_email_jobs = Mock(return_value=[])
        db.get_email_queue_stats = Mock(return_value={
            "pending": 0,
            "sending": 0,
            "sent": 0,
            "failed": 0,
            "total": 0,
        })
        return db
    
    @pytest.fixture
    def email_queue(self, mock_email_service, mock_database):
        """Create email queue instance."""
        return EmailQueue(
            email_service=mock_email_service,
            database=mock_database,
            worker_count=2,
        )
    
    @pytest.mark.asyncio
    async def test_enqueue(self, email_queue, mock_database):
        """Test enqueueing an email job."""
        job_id = await email_queue.enqueue(
            to=["test@example.com"],
            subject="Test",
            body="Body",
            html="<p>HTML</p>",
        )
        
        assert job_id == "job-123"
        assert mock_database.create_email_job.called
        assert email_queue.queue.qsize() == 1
    
    @pytest.mark.asyncio
    async def test_dequeue_from_memory(self, email_queue):
        """Test dequeueing from in-memory queue."""
        # Add job to queue
        await email_queue.enqueue(
            to=["test@example.com"],
            subject="Test",
            body="Body",
        )
        
        # Dequeue
        job = await email_queue.dequeue()
        
        assert job is not None
        assert job.to == ["test@example.com"]
        assert job.subject == "Test"
    
    @pytest.mark.asyncio
    async def test_dequeue_from_database(self, email_queue, mock_database):
        """Test dequeueing from database when memory queue is empty."""
        # Mock database to return a pending job
        mock_database.get_next_pending_email_job.return_value = {
            "id": "db-job-123",
            "recipient_to": "test@example.com",
            "subject": "DB Test",
            "body": "Body from DB",
            "html": None,
            "template_id": None,
            "variables": None,
            "status": "pending",
            "attempts": 0,
            "last_error": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        
        # Dequeue (memory queue is empty, should load from DB)
        job = await email_queue.dequeue()
        
        assert job is not None
        assert job.id == "db-job-123"
        assert job.subject == "DB Test"
        assert mock_database.get_next_pending_email_job.called
    
    @pytest.mark.asyncio
    async def test_process_job_success(self, email_queue, mock_database, mock_email_service):
        """Test successful job processing."""
        job = EmailQueueJob(
            to=["test@example.com"],
            subject="Test",
            body="Body",
        )
        
        # Process job
        success = await email_queue._process_job(job)
        
        assert success is True
        assert job.status == EmailJobStatus.SENT
        assert job.attempts == 1
        assert mock_email_service._send_email_sync.called
        assert mock_database.update_email_job.called
    
    @pytest.mark.asyncio
    async def test_process_job_failure_with_retry(self, email_queue, mock_database, mock_email_service):
        """Test job processing failure with retry."""
        # Mock email service to raise exception
        mock_email_service._send_email_sync.side_effect = Exception("SMTP error")
        
        job = EmailQueueJob(
            to=["test@example.com"],
            subject="Test",
            body="Body",
        )
        
        # Process job (should fail)
        success = await email_queue._process_job(job)
        
        assert success is False
        assert job.status == EmailJobStatus.PENDING  # Ready for retry
        assert job.attempts == 1
        assert job.last_error == "SMTP error"
        assert mock_database.update_email_job.called
    
    @pytest.mark.asyncio
    async def test_process_job_permanent_failure(self, email_queue, mock_database, mock_email_service):
        """Test job processing with permanent failure after max attempts."""
        # Mock email service to raise exception
        mock_email_service._send_email_sync.side_effect = Exception("SMTP error")
        
        job = EmailQueueJob(
            to=["test@example.com"],
            subject="Test",
            body="Body",
        )
        job.attempts = 2  # One more attempt will hit max (3)
        
        # Process job (should permanently fail)
        success = await email_queue._process_job(job)
        
        assert success is False
        assert job.status == EmailJobStatus.FAILED  # Permanently failed
        assert job.attempts == 3
        assert job.last_error == "SMTP error"
    
    @pytest.mark.asyncio
    async def test_retry_failed_jobs(self, email_queue, mock_database):
        """Test retrying failed jobs."""
        # Mock database to return failed jobs
        mock_database.get_failed_email_jobs.return_value = [
            {
                "id": "failed-1",
                "recipient_to": "test@example.com",
                "subject": "Failed 1",
                "body": "Body",
                "html": None,
                "template_id": None,
                "variables": None,
                "status": "failed",
                "attempts": 1,
                "last_error": "SMTP error",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
            {
                "id": "failed-2",
                "recipient_to": "test2@example.com",
                "subject": "Failed 2",
                "body": "Body",
                "html": None,
                "template_id": None,
                "variables": None,
                "status": "failed",
                "attempts": 2,
                "last_error": "SMTP error",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
        ]
        
        # Retry failed jobs
        count = await email_queue.retry_failed_jobs(max_jobs=10)
        
        assert count == 2
        assert mock_database.get_failed_email_jobs.called
        assert mock_database.update_email_job.call_count == 2
        assert email_queue.queue.qsize() == 2
    
    @pytest.mark.asyncio
    async def test_get_stats(self, email_queue, mock_database):
        """Test getting queue statistics."""
        mock_database.get_email_queue_stats.return_value = {
            "pending": 5,
            "sending": 1,
            "sent": 100,
            "failed": 2,
            "total": 108,
        }
        
        stats = await email_queue.get_stats()
        
        assert stats["pending"] == 5
        assert stats["sending"] == 1
        assert stats["sent"] == 100
        assert stats["failed"] == 2
        assert stats["total"] == 108
        # Workers count is 0 when not started (no workers created yet)
        assert stats["workers"] == 0
        assert stats["running"] is False
    
    @pytest.mark.asyncio
    async def test_reload_pending_jobs(self, email_queue, mock_database):
        """Test reloading pending jobs from database."""
        # Mock database to return pending jobs
        mock_database.get_all_pending_email_jobs.return_value = [
            {
                "id": "pending-1",
                "recipient_to": "test@example.com",
                "subject": "Pending 1",
                "body": "Body",
                "html": None,
                "template_id": None,
                "variables": None,
                "status": "pending",
                "attempts": 0,
                "last_error": None,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
            {
                "id": "pending-2",
                "recipient_to": "test2@example.com",
                "subject": "Pending 2",
                "body": "Body",
                "html": None,
                "template_id": None,
                "variables": None,
                "status": "pending",
                "attempts": 0,
                "last_error": None,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
        ]
        
        # Reload jobs
        await email_queue._reload_pending_jobs()
        
        assert email_queue.queue.qsize() == 2
        assert mock_database.get_all_pending_email_jobs.called

"""
Email Queue Service with Database Persistence for Vertex AR.
Provides durable async queue for email delivery that survives restarts.
"""
import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum

from logging_setup import get_logger

logger = get_logger(__name__)


class EmailJobStatus(Enum):
    """Email job status."""
    PENDING = "pending"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"


class EmailQueueJob:
    """Represents an email job in the persistent queue."""
    
    def __init__(
        self,
        to: List[str],
        subject: str,
        body: str,
        html: Optional[str] = None,
        template_id: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None,
        job_id: Optional[str] = None,
        status: str = "pending",
        attempts: int = 0,
        last_error: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = job_id or str(uuid.uuid4())
        self.to = to
        self.subject = subject
        self.body = body
        self.html = html
        self.template_id = template_id
        self.variables = variables or {}
        self.status = EmailJobStatus(status) if isinstance(status, str) else status
        self.attempts = attempts
        self.last_error = last_error
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.max_attempts = 3
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary for database storage."""
        return {
            "id": self.id,
            "to": ",".join(self.to),
            "subject": self.subject,
            "body": self.body,
            "html": self.html,
            "template_id": self.template_id,
            "variables": json.dumps(self.variables) if self.variables else None,
            "status": self.status.value,
            "attempts": self.attempts,
            "last_error": self.last_error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EmailQueueJob":
        """Create job from database row."""
        # Handle both 'to' and 'recipient_to' column names (database uses recipient_to)
        to_field = data.get("recipient_to") or data.get("to", "")
        return cls(
            job_id=data["id"],
            to=to_field.split(",") if to_field else [],
            subject=data["subject"],
            body=data["body"],
            html=data.get("html"),
            template_id=data.get("template_id"),
            variables=json.loads(data["variables"]) if data.get("variables") else None,
            status=data["status"],
            attempts=data["attempts"],
            last_error=data.get("last_error"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


class EmailQueue:
    """
    Persistent email queue with async worker pool.
    Survives application restarts by storing jobs in the database.
    """
    
    def __init__(self, email_service, database, worker_count: int = 3):
        """
        Initialize email queue.
        
        Args:
            email_service: EmailService instance for sending emails
            database: Database instance for persistence
            worker_count: Number of concurrent workers (default: 3)
        """
        self.email_service = email_service
        self.database = database
        self.worker_count = worker_count
        
        # In-memory queue for fast dequeue operations
        self.queue: asyncio.Queue = asyncio.Queue()
        
        # Worker management
        self.workers: List[asyncio.Task] = []
        self.running = False
        self._shutdown_event = asyncio.Event()
        
        logger.info(f"EmailQueue initialized with {worker_count} workers")
    
    async def enqueue(
        self,
        to: List[str],
        subject: str,
        body: str,
        html: Optional[str] = None,
        template_id: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Enqueue an email job.
        
        Args:
            to: List of recipient email addresses
            subject: Email subject
            body: Plain text body
            html: Optional HTML body
            template_id: Optional template ID
            variables: Optional template variables
        
        Returns:
            Job ID
        """
        job = EmailQueueJob(
            to=to,
            subject=subject,
            body=body,
            html=html,
            template_id=template_id,
            variables=variables,
        )
        
        # Persist to database
        job_id = self.database.create_email_job(job)
        
        # Add to in-memory queue for immediate processing
        await self.queue.put(job)
        
        logger.info(f"Email job enqueued: {job_id} (to: {len(to)} recipients)")
        
        return job_id
    
    async def dequeue(self) -> Optional[EmailQueueJob]:
        """
        Dequeue next pending job.
        
        Returns:
            EmailQueueJob or None if queue is empty
        """
        try:
            # Try to get from in-memory queue (non-blocking)
            job = await asyncio.wait_for(self.queue.get(), timeout=1.0)
            return job
        except asyncio.TimeoutError:
            # If in-memory queue is empty, load from database
            job_dict = self.database.get_next_pending_email_job()
            if job_dict:
                return EmailQueueJob.from_dict(job_dict)
            return None
    
    async def _process_job(self, job: EmailQueueJob) -> bool:
        """
        Process a single email job.
        
        Args:
            job: EmailQueueJob to process
        
        Returns:
            True if successful, False otherwise
        """
        # Update status to sending
        job.status = EmailJobStatus.SENDING
        job.attempts += 1
        job.updated_at = datetime.utcnow()
        self.database.update_email_job(job)
        
        try:
            # Send email via EmailService directly (bypass queue)
            # We use the internal _send_email_sync method
            from app.email_service import EmailMessage
            
            email_msg = EmailMessage(
                to_addresses=job.to,
                subject=job.subject,
                body=job.body,
                html_body=job.html,
                priority=5,  # Normal priority
            )
            
            # Send directly (synchronous, with metrics)
            await self.email_service._send_email_sync(email_msg)
            
            # Mark as sent
            job.status = EmailJobStatus.SENT
            job.updated_at = datetime.utcnow()
            self.database.update_email_job(job)
            
            logger.info(f"Email job {job.id} sent successfully")
            return True
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Email job {job.id} failed (attempt {job.attempts}): {error_msg}")
            
            # Update job with error
            job.last_error = error_msg
            job.updated_at = datetime.utcnow()
            
            if job.attempts >= job.max_attempts:
                # Permanently failed
                job.status = EmailJobStatus.FAILED
                logger.error(f"Email job {job.id} permanently failed after {job.attempts} attempts")
            else:
                # Retry - put back to pending
                job.status = EmailJobStatus.PENDING
                logger.warning(f"Email job {job.id} will be retried (attempt {job.attempts}/{job.max_attempts})")
            
            self.database.update_email_job(job)
            return False
    
    async def _worker(self, worker_id: int):
        """
        Worker coroutine that processes jobs from the queue.
        
        Args:
            worker_id: Worker identifier for logging
        """
        logger.info(f"Email queue worker {worker_id} started")
        
        while self.running:
            try:
                # Check shutdown signal
                if self._shutdown_event.is_set():
                    break
                
                # Get next job
                job = await self.dequeue()
                
                if job:
                    logger.debug(f"Worker {worker_id} processing job {job.id}")
                    await self._process_job(job)
                else:
                    # No jobs available, sleep briefly
                    await asyncio.sleep(1.0)
                    
            except asyncio.CancelledError:
                logger.info(f"Worker {worker_id} cancelled")
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}", exc_info=e)
                await asyncio.sleep(5.0)  # Back off on error
        
        logger.info(f"Email queue worker {worker_id} stopped")
    
    async def start_workers(self):
        """Start worker pool."""
        if self.running:
            logger.warning("Workers already running")
            return
        
        self.running = True
        self._shutdown_event.clear()
        
        # Reload pending jobs from database into memory queue
        await self._reload_pending_jobs()
        
        # Start workers
        for i in range(self.worker_count):
            worker = asyncio.create_task(self._worker(i + 1))
            self.workers.append(worker)
        
        logger.info(f"Started {self.worker_count} email queue workers")
    
    async def stop_workers(self):
        """Stop worker pool gracefully."""
        if not self.running:
            logger.warning("Workers not running")
            return
        
        logger.info("Stopping email queue workers...")
        self.running = False
        self._shutdown_event.set()
        
        # Cancel all workers
        for worker in self.workers:
            worker.cancel()
        
        # Wait for workers to finish
        await asyncio.gather(*self.workers, return_exceptions=True)
        
        self.workers.clear()
        logger.info("Email queue workers stopped")
    
    async def _reload_pending_jobs(self):
        """Reload pending jobs from database into memory queue."""
        pending_jobs = self.database.get_all_pending_email_jobs()
        
        for job_dict in pending_jobs:
            job = EmailQueueJob.from_dict(job_dict)
            await self.queue.put(job)
        
        logger.info(f"Reloaded {len(pending_jobs)} pending email jobs from database")
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get queue statistics.
        
        Returns:
            Dictionary with queue stats
        """
        stats = self.database.get_email_queue_stats()
        stats["workers"] = len(self.workers)
        stats["running"] = self.running
        stats["memory_queue_size"] = self.queue.qsize()
        
        return stats
    
    async def retry_failed_jobs(self, max_jobs: int = 10) -> int:
        """
        Retry failed jobs.
        
        Args:
            max_jobs: Maximum number of jobs to retry
        
        Returns:
            Number of jobs requeued
        """
        failed_jobs = self.database.get_failed_email_jobs(limit=max_jobs)
        
        count = 0
        for job_dict in failed_jobs:
            job = EmailQueueJob.from_dict(job_dict)
            
            # Reset to pending if under max attempts
            if job.attempts < job.max_attempts:
                job.status = EmailJobStatus.PENDING
                job.updated_at = datetime.utcnow()
                self.database.update_email_job(job)
                
                # Add to memory queue
                await self.queue.put(job)
                count += 1
                
                logger.info(f"Requeued failed job {job.id}")
        
        logger.info(f"Requeued {count} failed email jobs")
        return count


# Singleton instance (will be initialized in main.py)
email_queue: Optional[EmailQueue] = None


def get_email_queue() -> Optional[EmailQueue]:
    """Get the email queue instance."""
    return email_queue

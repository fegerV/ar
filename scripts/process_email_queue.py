#!/usr/bin/env python3
"""
Email Queue Management CLI Tool for Vertex AR.
Provides commands to manually manage the persistent email queue.
"""
import argparse
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "vertex-ar"))

from app.config import settings
from app.database import Database
from app.email_service import email_service
from app.services.email_queue import EmailQueue, EmailQueueJob
from logging_setup import get_logger

logger = get_logger(__name__)


async def drain_queue(queue: EmailQueue, max_jobs: int = None):
    """
    Drain the email queue by processing all pending jobs.
    
    Args:
        queue: EmailQueue instance
        max_jobs: Maximum number of jobs to process (None = all)
    """
    logger.info("Starting queue drain operation...")
    
    processed = 0
    succeeded = 0
    failed = 0
    
    while True:
        if max_jobs and processed >= max_jobs:
            break
        
        # Get next job
        job = await queue.dequeue()
        if not job:
            break
        
        processed += 1
        logger.info(f"Processing job {processed}: {job.id} (to: {job.to})")
        
        # Process job
        success = await queue._process_job(job)
        if success:
            succeeded += 1
        else:
            failed += 1
    
    logger.info(f"Drain complete: {processed} processed, {succeeded} succeeded, {failed} failed")
    
    return {
        "processed": processed,
        "succeeded": succeeded,
        "failed": failed,
    }


async def retry_failed(queue: EmailQueue, max_jobs: int = 10):
    """
    Retry failed jobs in the queue.
    
    Args:
        queue: EmailQueue instance
        max_jobs: Maximum number of jobs to retry
    """
    logger.info(f"Retrying up to {max_jobs} failed jobs...")
    
    count = await queue.retry_failed_jobs(max_jobs)
    
    logger.info(f"Requeued {count} failed jobs")
    
    return {"requeued": count}


async def show_stats(queue: EmailQueue):
    """
    Show queue statistics.
    
    Args:
        queue: EmailQueue instance
    """
    stats = await queue.get_stats()
    
    print("\n" + "=" * 60)
    print("EMAIL QUEUE STATISTICS")
    print("=" * 60)
    print(f"Pending:       {stats['pending']}")
    print(f"Sending:       {stats['sending']}")
    print(f"Sent:          {stats['sent']}")
    print(f"Failed:        {stats['failed']}")
    print(f"Total:         {stats['total']}")
    print(f"Memory Queue:  {stats['memory_queue_size']}")
    print(f"Workers:       {stats['workers']}")
    print(f"Running:       {stats['running']}")
    print("=" * 60 + "\n")
    
    return stats


async def list_failed(database: Database, limit: int = 10):
    """
    List failed jobs.
    
    Args:
        database: Database instance
        limit: Maximum number of jobs to list
    """
    failed_jobs = database.get_failed_email_jobs(limit)
    
    print("\n" + "=" * 60)
    print(f"FAILED EMAIL JOBS (showing {len(failed_jobs)} of max {limit})")
    print("=" * 60)
    
    if not failed_jobs:
        print("No failed jobs found.")
    else:
        for i, job_dict in enumerate(failed_jobs, 1):
            job = EmailQueueJob.from_dict(job_dict)
            print(f"\n{i}. Job ID: {job.id}")
            print(f"   To:       {', '.join(job.to)}")
            print(f"   Subject:  {job.subject}")
            print(f"   Attempts: {job.attempts}/{job.max_attempts}")
            print(f"   Error:    {job.last_error}")
            print(f"   Created:  {job.created_at}")
            print(f"   Updated:  {job.updated_at}")
    
    print("=" * 60 + "\n")


async def cleanup_old_jobs(database: Database, days: int = 30):
    """
    Clean up old sent/failed jobs.
    
    Args:
        database: Database instance
        days: Delete jobs older than this many days
    """
    logger.info(f"Cleaning up jobs older than {days} days...")
    
    count = database.delete_old_email_jobs(days)
    
    logger.info(f"Deleted {count} old jobs")
    
    return {"deleted": count}


async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Email Queue Management CLI for Vertex AR",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  drain       Process all pending jobs in the queue
  retry       Retry failed jobs
  stats       Show queue statistics
  failed      List failed jobs
  cleanup     Clean up old sent/failed jobs

Examples:
  %(prog)s drain --max 100        # Process up to 100 pending jobs
  %(prog)s retry --max 10         # Retry up to 10 failed jobs
  %(prog)s stats                  # Show queue statistics
  %(prog)s failed --limit 20      # List 20 most recent failed jobs
  %(prog)s cleanup --days 30      # Delete jobs older than 30 days
        """
    )
    
    parser.add_argument(
        "command",
        choices=["drain", "retry", "stats", "failed", "cleanup"],
        help="Command to execute"
    )
    
    parser.add_argument(
        "--max",
        type=int,
        default=None,
        help="Maximum number of jobs to process (drain/retry commands)"
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of jobs to list (failed command)"
    )
    
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days for cleanup threshold (cleanup command)"
    )
    
    args = parser.parse_args()
    
    # Initialize database
    database = Database(settings.DB_PATH)
    logger.info(f"Database initialized: {settings.DB_PATH}")
    
    # Initialize email queue (without starting workers)
    queue = EmailQueue(
        email_service=email_service,
        database=database,
        worker_count=1,
    )
    
    # Execute command
    try:
        if args.command == "drain":
            max_jobs = args.max
            logger.info(f"Executing drain command (max: {max_jobs or 'unlimited'})")
            result = await drain_queue(queue, max_jobs)
            print(f"\nProcessed: {result['processed']}")
            print(f"Succeeded: {result['succeeded']}")
            print(f"Failed:    {result['failed']}")
        
        elif args.command == "retry":
            max_jobs = args.max or 10
            logger.info(f"Executing retry command (max: {max_jobs})")
            result = await retry_failed(queue, max_jobs)
            print(f"\nRequeued: {result['requeued']} jobs")
        
        elif args.command == "stats":
            logger.info("Executing stats command")
            await show_stats(queue)
        
        elif args.command == "failed":
            logger.info(f"Executing failed command (limit: {args.limit})")
            await list_failed(database, args.limit)
        
        elif args.command == "cleanup":
            logger.info(f"Executing cleanup command (days: {args.days})")
            result = await cleanup_old_jobs(database, args.days)
            print(f"\nDeleted: {result['deleted']} old jobs")
        
        logger.info("Command completed successfully")
        
    except Exception as e:
        logger.error(f"Command failed: {e}", exc_info=e)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

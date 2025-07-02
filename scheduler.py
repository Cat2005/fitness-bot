"""
Scheduler module for automated daily and weekly tasks.

This module uses APScheduler to handle timed tasks like daily prompts
and weekly recaps at specific times in Europe/London timezone.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from config import TZ

if TYPE_CHECKING:
    from bot import FitnessCoachBot

logger = logging.getLogger(__name__)


class FitnessScheduler:
    """Scheduler for automated fitness bot tasks."""
    
    def __init__(self, bot: FitnessCoachBot) -> None:
        """Initialize the scheduler with bot instance."""
        self.bot = bot
        self.scheduler = BackgroundScheduler(timezone=pytz.timezone(TZ))
        
    def setup_daily_prompt(self) -> None:
        """Set up daily prompt job at 20:30 Europe/London."""
        trigger = CronTrigger(
            hour=20,
            minute=30,
            timezone=pytz.timezone(TZ)
        )
        
        self.scheduler.add_job(
            func=self._send_daily_prompt_job,
            trigger=trigger,
            id='daily_prompt',
            name='Daily Fitness Prompt',
            replace_existing=True
        )
        
        logger.info("Daily prompt job scheduled for 20:30 Europe/London")
        
    def setup_weekly_recap(self) -> None:
        """Set up weekly recap job at 20:00 Europe/London on Sundays."""
        trigger = CronTrigger(
            day_of_week='sun',
            hour=20,
            minute=0,
            timezone=pytz.timezone(TZ)
        )
        
        self.scheduler.add_job(
            func=self._send_weekly_recap_job,
            trigger=trigger,
            id='weekly_recap',
            name='Weekly Fitness Recap',
            replace_existing=True
        )
        
        logger.info("Weekly recap job scheduled for Sundays at 20:00 Europe/London")
        
    def start(self) -> None:
        """Start the scheduler."""
        try:
            self.scheduler.start()
            logger.info("Scheduler started successfully")
        except Exception as e:
            logger.error(f"Error starting scheduler: {e}")
            raise
            
    def stop(self) -> None:
        """Stop the scheduler."""
        try:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")
            
    def _send_daily_prompt_job(self) -> None:
        """Job function to send daily prompt."""
        try:
            import asyncio
            
            # Create a new event loop for the job
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Create a context object for the bot
            context = self._create_context()
            
            # Send the daily prompt
            loop.run_until_complete(self.bot.send_daily_prompt(context))
            
            loop.close()
            
        except Exception as e:
            logger.error(f"Error in daily prompt job: {e}")
            
    def _send_weekly_recap_job(self) -> None:
        """Job function to send weekly recap."""
        try:
            import asyncio
            
            # Create a new event loop for the job
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Create a context object for the bot
            context = self._create_context()
            
            # Send the weekly recap
            loop.run_until_complete(self.bot.send_weekly_recap(context))
            
            loop.close()
            
        except Exception as e:
            logger.error(f"Error in weekly recap job: {e}")
            
    def _create_context(self) -> object:
        """Create a minimal context object for scheduled jobs."""
        # This is a simplified context object for scheduled jobs
        # In a real implementation, you might need to create a proper context
        class SimpleContext:
            def __init__(self, bot_instance):
                self.bot = bot_instance
                
        return SimpleContext(self.bot.application.bot)
        
    def get_job_status(self) -> dict[str, str]:
        """Get the status of scheduled jobs."""
        jobs = self.scheduler.get_jobs()
        status = {}
        
        for job in jobs:
            next_run = job.next_run_time
            status[job.id] = {
                'name': job.name,
                'next_run': next_run.strftime('%Y-%m-%d %H:%M:%S %Z') if next_run else 'Not scheduled'
            }
            
        return status


def start_scheduler(bot: FitnessCoachBot) -> FitnessScheduler:
    """Start the scheduler with daily and weekly jobs."""
    scheduler = FitnessScheduler(bot)
    
    # Set up jobs
    scheduler.setup_daily_prompt()
    scheduler.setup_weekly_recap()
    
    # Start the scheduler
    scheduler.start()
    
    return scheduler 
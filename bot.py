"""
Telegram bot for fitness accountability coaching.

This module handles Telegram bot interactions, processes user responses,
and coordinates with Claude API and Google Docs for data storage.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any

import pytz
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from claude_api import get_daily_summary, get_weekly_recap
from config import CLAUDE_API_KEY, DOC_ID, STRETCH_DOC_ID, TELEGRAM_TOKEN, TZ, USER_CHAT_ID
from google_docs import append_to_doc, get_daily_summaries_from_doc, get_stretch_entry, save_stretch_entry
from scheduler import start_scheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FitnessCoachBot:
    """Main bot class handling Telegram interactions and user state."""
    
    def __init__(self) -> None:
        """Initialize the bot with necessary configurations."""
        self.application = Application.builder().token(TELEGRAM_TOKEN).build()
        self.tz = pytz.timezone(TZ)
        self.awaiting_daily_response = False
        self.awaiting_weekly_response = False
        self.awaiting_stretch_response = False
        self.pending_daily_data: dict[str, Any] = {}
        self.pending_weekly_data: dict[str, Any] = {}
        self.pending_stretch_data: dict[str, Any] = {}
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /start command."""
        if update.effective_chat and update.effective_chat.id != USER_CHAT_ID:
            await update.message.reply_text("Sorry, this bot is not available for your chat.")
            return
            
        await update.message.reply_text(
            "Welcome to your Fitness Coach Bot! 🏋️‍♂️\n\n"
            "I'll check in with you every evening at 20:30 to ask about your workout, "
            "eating habits, and goals. I'll also provide weekly recaps on Sundays.\n\n"
            "Use /help to see available commands."
        )
        
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /help command."""
        if update.effective_chat and update.effective_chat.id != USER_CHAT_ID:
            return
            
        help_text = """
Available commands:
/start - Initialize the bot
/help - Show this help message
/daily - Trigger daily check-in manually
/weekly - Trigger weekly recap manually
/stretch - Trigger stretch check manually
/status - Show current bot status

The bot will automatically:
- Send daily prompts at 20:30 Europe/London
- Send weekly recaps on Sundays at 20:00 Europe/London
- Send stretch reminders at 19:00 Europe/London (if needed)
- Store all data in Google Docs
        """
        await update.message.reply_text(help_text)
        
    async def daily_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Manually trigger daily check-in."""
        if update.effective_chat and update.effective_chat.id != USER_CHAT_ID:
            return
            
        await self.send_daily_prompt(context)
        
    async def weekly_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Manually trigger weekly recap."""
        if update.effective_chat and update.effective_chat.id != USER_CHAT_ID:
            return
            
        await self.send_weekly_recap(context)
        
    async def stretch_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Manually trigger stretch check."""
        if update.effective_chat and update.effective_chat.id != USER_CHAT_ID:
            return
            
        await self.send_stretch_check(context)
        
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show current bot status."""
        if update.effective_chat and update.effective_chat.id != USER_CHAT_ID:
            return
            
        now = datetime.now(self.tz)
        status_text = f"""
Current Status:
- Time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}
- Awaiting daily response: {self.awaiting_daily_response}
- Awaiting weekly response: {self.awaiting_weekly_response}
- Awaiting stretch response: {self.awaiting_stretch_response}
- Next daily prompt: Today at 20:30 Europe/London
- Next weekly recap: Sunday at 20:00 Europe/London
- Next stretch check: Today at 19:00 Europe/London (if needed)
        """
        await update.message.reply_text(status_text)
        
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming text messages from the user."""
        if update.effective_chat and update.effective_chat.id != USER_CHAT_ID:
            return
            
        if not update.message or not update.message.text:
            return
            
        user_text = update.message.text
        
        if self.awaiting_daily_response:
            await self.process_daily_response(user_text, context)
        elif self.awaiting_weekly_response:
            await self.process_weekly_response(user_text, context)
        elif self.awaiting_stretch_response:
            await self.process_stretch_response(user_text, context)
        else:
            await update.message.reply_text(
                "I'm not currently expecting a response. Use /daily to start a daily check-in, "
                "/weekly for a weekly recap, or /stretch for a stretch check."
            )
            
    async def send_daily_prompt(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send the daily evening prompt to the user."""
        try:
            # Check for yesterday's goals from Google Docs
            yesterday = (datetime.now(self.tz) - timedelta(days=1)).date()
            yesterday_goals = []
            
            try:
                # Get yesterday's summary from Google Docs
                daily_summaries = get_daily_summaries_from_doc(DOC_ID, days=2)
                yesterday_str = yesterday.isoformat()
                
                for summary in daily_summaries:
                    if summary.get('date') == yesterday_str:
                        yesterday_goals = summary.get('short_term_goals', [])
                        break
            except Exception as e:
                logger.warning(f"Could not retrieve yesterday's goals: {e}")
            
            prompt = "Good evening! Time for your daily check-in 🌅\n\n"
            
            if yesterday_goals:
                goals_text = ", ".join(yesterday_goals)
                prompt += f"Yesterday you planned: {goals_text}. How did it go?\n\n"
            
            prompt += (
                "Please tell me about your day:\n"
                "• How was your workout today?\n"
                "• How did you feel about what you ate?\n"
                "• Any goals for tomorrow / the next few days?"
            )
            
            await context.bot.send_message(chat_id=USER_CHAT_ID, text=prompt)
            self.awaiting_daily_response = True
            
            logger.info("Daily prompt sent successfully")
            
        except Exception as e:
            logger.error(f"Error sending daily prompt: {e}")
            
    async def send_stretch_check(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send stretch check if user didn't stretch yesterday or has no entry."""
        try:
            # Get yesterday's date
            yesterday = (datetime.now(self.tz) - timedelta(days=1)).date()
            yesterday_str = yesterday.isoformat()
            
            # Check if user stretched yesterday
            yesterday_entry = get_stretch_entry(STRETCH_DOC_ID, yesterday_str)
            
            # If they stretched yesterday, don't send reminder
            if yesterday_entry and yesterday_entry.get('stretched', False):
                logger.info(f"User stretched yesterday ({yesterday_str}), no reminder needed")
                return
                
            # Send stretch reminder
            today = datetime.now(self.tz).date()
            today_str = today.isoformat()
            
            # Check if we already have an entry for today
            today_entry = get_stretch_entry(STRETCH_DOC_ID, today_str)
            if today_entry:
                logger.info(f"Already have stretch entry for today ({today_str}), no reminder needed")
                return
            
            prompt = "🧘‍♂️ Stretch Reminder!\n\n"
            
            if yesterday_entry:
                prompt += "I noticed you didn't stretch yesterday. "
            else:
                prompt += "I don't have a record of you stretching yesterday. "
            
            prompt += (
                "Have you stretched today? Even 5-10 minutes can make a big difference!\n\n"
                "Please reply with 'yes' or 'no' and let me know about your stretching today."
            )
            
            await context.bot.send_message(chat_id=USER_CHAT_ID, text=prompt)
            self.awaiting_stretch_response = True
            self.pending_stretch_data = {'date': today_str}
            
            logger.info("Stretch check sent successfully")
            
        except Exception as e:
            logger.error(f"Error sending stretch check: {e}")
            
    async def process_daily_response(self, user_text: str, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Process the user's daily response with Claude and save to Google Docs."""
        try:
            self.awaiting_daily_response = False
            
            # Get recent history for context (last 3 days)
            history = self._get_recent_history(days=3)
            
            # Get Claude's summary
            await context.bot.send_message(
                chat_id=USER_CHAT_ID, 
                text="Thanks! Processing your response... 🤖"
            )
            
            summary = get_daily_summary(history, user_text)
            
            # Prepare data for Google Docs (no separate goal saving needed)
            today = datetime.now(self.tz).date()
            today_str = today.strftime("%Y-%m-%d")
            doc_content = f"""
Daily Check-in: {today_str}

Raw Response:
{user_text}

Summary:
• Workout: {summary.get('workout', 'Not specified')}
• Eating Feelings: {summary.get('eating_feelings', 'Not specified')}
• Short-term Goals: {', '.join(summary.get('short_term_goals', []))}

---
            """
            
            # Save to Google Docs
            append_to_doc(DOC_ID, f"Daily Check-in: {today_str}", doc_content)
            
            # Send confirmation to user
            response_text = (
                f"Got it! Here's your summary:\n\n"
                f"🏋️ Workout: {summary.get('workout', 'Not specified')}\n"
                f"🍎 Eating: {summary.get('eating_feelings', 'Not specified')}\n"
                f"🎯 Goals: {', '.join(summary.get('short_term_goals', []))}\n\n"
                f"Everything has been saved to your fitness log. Keep up the great work! 💪"
            )
            
            await context.bot.send_message(chat_id=USER_CHAT_ID, text=response_text)
            
            logger.info("Daily response processed successfully")
            
        except Exception as e:
            logger.error(f"Error processing daily response: {e}")
            await context.bot.send_message(
                chat_id=USER_CHAT_ID, 
                text="Sorry, there was an error processing your response. Please try again later."
            )
            
    async def send_weekly_recap(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send weekly recap based on the past 7 days."""
        try:
            # Get past 7 days of summaries
            daily_summaries = self._get_recent_summaries(days=7)
            
            if not daily_summaries:
                await context.bot.send_message(
                    chat_id=USER_CHAT_ID, 
                    text="No daily summaries found for the past week. Start logging your daily check-ins!"
                )
                return
                
            # Get weekly recap from Claude
            await context.bot.send_message(
                chat_id=USER_CHAT_ID, 
                text="Preparing your weekly recap... 📊"
            )
            
            recap = get_weekly_recap(daily_summaries)
            
            # Format recap message
            week_start = (datetime.now(self.tz) - timedelta(days=7)).date()
            recap_text = f"""
🗓️ Weekly Recap: Week of {week_start.strftime('%Y-%m-%d')}

📈 Workout Count: {recap.get('workout_count', 0)}
🍽️ General Eating Feeling: {recap.get('general_eating_feeling', 'Not specified')}
😅 Slip-ups: {recap.get('slip_ups', 'None reported')}

💭 Reflection: {recap.get('suggested_reflection', 'Keep up the good work!')}

How would you rate this week? What are your goals for next week?
            """
            
            await context.bot.send_message(chat_id=USER_CHAT_ID, text=recap_text)
            
            # Save to Google Docs
            week_heading = f"Week of {week_start.strftime('%Y-%m-%d')}"
            append_to_doc(DOC_ID, week_heading, recap_text)
            
            self.awaiting_weekly_response = True
            self.pending_weekly_data = recap
            
            logger.info("Weekly recap sent successfully")
            
        except Exception as e:
            logger.error(f"Error sending weekly recap: {e}")
            await context.bot.send_message(
                chat_id=USER_CHAT_ID, 
                text="Sorry, there was an error generating your weekly recap. Please try again later."
            )
            
    async def process_weekly_response(self, user_text: str, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Process the user's weekly response and save to Google Docs."""
        try:
            self.awaiting_weekly_response = False
            
            # Save weekly response to Google Docs
            week_start = (datetime.now(self.tz) - timedelta(days=7)).date()
            response_content = f"""
Weekly Response: {week_start.strftime('%Y-%m-%d')}

User Rating & Goals:
{user_text}

---
            """
            
            append_to_doc(DOC_ID, f"Weekly Response: {week_start.strftime('%Y-%m-%d')}", response_content)
            
            await context.bot.send_message(
                chat_id=USER_CHAT_ID, 
                text="Thanks for your weekly reflection! Your response has been saved. "
                      "Looking forward to supporting you in the coming week! 🌟"
            )
            
            logger.info("Weekly response processed successfully")
            
        except Exception as e:
            logger.error(f"Error processing weekly response: {e}")
            await context.bot.send_message(
                chat_id=USER_CHAT_ID, 
                text="Sorry, there was an error saving your weekly response. Please try again later."
            )
            
    async def process_stretch_response(self, user_text: str, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Process the user's stretch response and save to Google Docs."""
        try:
            self.awaiting_stretch_response = False
            
            # Determine if user stretched based on response
            user_text_lower = user_text.lower()
            stretched = 'yes' in user_text_lower or 'yeah' in user_text_lower or 'yep' in user_text_lower
            
            # Get today's date
            today = self.pending_stretch_data.get('date', datetime.now(self.tz).date().isoformat())
            
            # Save to Google Docs
            save_stretch_entry(STRETCH_DOC_ID, today, user_text, stretched)
            
            # Send confirmation to user
            if stretched:
                response_text = (
                    "Great job! 🎉 I've recorded that you stretched today. "
                    "Keep up the excellent work with your flexibility routine! 💪"
                )
            else:
                response_text = (
                    "Thanks for the update! 📝 I've recorded your response. "
                    "Remember, even a few minutes of stretching can help prevent stiffness "
                    "and improve your mobility. Consider adding it to your routine tomorrow! 🧘‍♂️"
                )
            
            await context.bot.send_message(chat_id=USER_CHAT_ID, text=response_text)
            
            # Clear pending data
            self.pending_stretch_data = {}
            
            logger.info("Stretch response processed successfully")
            
        except Exception as e:
            logger.error(f"Error processing stretch response: {e}")
            await context.bot.send_message(
                chat_id=USER_CHAT_ID, 
                text="Sorry, there was an error saving your stretch response. Please try again later."
            )
            
    def _get_recent_history(self, days: int) -> str:
        """Get recent history for context from Google Docs."""
        try:
            from google_docs import search_recent_entries
            recent_entries = search_recent_entries(DOC_ID, days)
            
            if not recent_entries:
                return "No recent history available."
            
            # Format the recent entries as context
            history_text = "Recent fitness history:\n"
            for entry in recent_entries[-3:]:  # Last 3 entries for context
                history_text += f"- {entry}\n"
            
            return history_text
            
        except Exception as e:
            logger.error(f"Failed to get recent history: {e}")
            return "Unable to retrieve recent history."
        
    def _get_recent_summaries(self, days: int) -> list[dict[str, Any]]:
        """Get recent daily summaries for weekly recap from Google Docs."""
        try:
            from google_docs import get_daily_summaries_from_doc
            summaries = get_daily_summaries_from_doc(DOC_ID, days)
            
            if not summaries:
                logger.warning("No recent daily summaries found in Google Docs")
                return []
            
            logger.info(f"Retrieved {len(summaries)} daily summaries for weekly recap")
            return summaries
            
        except Exception as e:
            logger.error(f"Failed to get recent summaries: {e}")
            return []
        
    def setup_handlers(self) -> None:
        """Set up all message handlers."""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("daily", self.daily_command))
        self.application.add_handler(CommandHandler("weekly", self.weekly_command))
        self.application.add_handler(CommandHandler("stretch", self.stretch_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
    async def start_bot(self) -> None:
        """Start the bot and scheduler."""
        self.setup_handlers()
        
        # Start scheduler
        start_scheduler(self)
        
        # Start the bot
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        logger.info("Bot started successfully")
        
    async def stop_bot(self) -> None:
        """Stop the bot gracefully."""
        await self.application.updater.stop()
        await self.application.stop()
        await self.application.shutdown()
        
        logger.info("Bot stopped")


async def main() -> None:
    """Main entry point for the bot."""
    bot = FitnessCoachBot()
    try:
        await bot.start_bot()
        
        # Keep the bot running
        import asyncio
        await asyncio.Event().wait()
        
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        await bot.stop_bot()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 
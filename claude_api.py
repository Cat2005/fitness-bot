"""
Claude API integration for fitness coach bot.

This module provides functions to interact with Anthropic's Claude API
for generating daily summaries and weekly recaps based on user input.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import anthropic
from anthropic import Anthropic

from config import CLAUDE_API_KEY, CLAUDE_MODEL, MAX_RETRIES, RETRY_BACKOFF, RETRY_DELAY

logger = logging.getLogger(__name__)

# Initialize Claude client
client = Anthropic(api_key=CLAUDE_API_KEY)


def _clean_json_response(response_text: str) -> str:
    """
    Clean Claude's response by removing markdown code blocks if present.
    
    Args:
        response_text: Raw response text from Claude
        
    Returns:
        str: Clean JSON string ready for parsing
    """
    # Strip whitespace
    text = response_text.strip()
    
    # Remove markdown code blocks if present
    if text.startswith("```json"):
        text = text[7:]  # Remove ```json
    elif text.startswith("```"):
        text = text[3:]  # Remove ```
    
    if text.endswith("```"):
        text = text[:-3]  # Remove trailing ```
    
    return text.strip()


def _retry_with_backoff(func, *args, **kwargs) -> Any:
    """
    Retry a function with exponential backoff.
    
    Args:
        func: Function to retry
        *args: Function arguments
        **kwargs: Function keyword arguments
        
    Returns:
        Function result
        
    Raises:
        Exception: If all retry attempts fail
    """
    last_exception = None
    
    for attempt in range(MAX_RETRIES):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAY * (RETRY_BACKOFF ** attempt)
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                time.sleep(delay)
            else:
                logger.error(f"All {MAX_RETRIES} attempts failed")
    
    raise last_exception


def get_daily_summary(history: str, user_reply: str) -> dict[str, Any]:
    """
    Generate a structured daily summary from user's response.
    
    Args:
        history: Recent history context for the user
        user_reply: User's response to daily prompt
        
    Returns:
        dict: Structured summary with workout, eating_feelings, and short_term_goals
        
    Raises:
        Exception: If API call fails after retries
    """
    prompt = f"""
You are a fitness accountability coach assistant. Analyze the user's daily check-in response and extract key information.

Recent context: {history}

User's response today: {user_reply}

Please provide a JSON response with the following structure:
{{
    "workout": "brief summary of their workout (or lack thereof)",
    "eating_feelings": "brief summary of how they felt about their eating",
    "short_term_goals": ["goal1", "goal2", "goal3"] // extract 1-3 specific goals they mentioned for tomorrow/next few days
}}

Guidelines:
- Be kind and encouraging in your summaries
- Keep workout and eating_feelings to 1-2 sentences each
- Extract concrete, actionable goals from their response
- If they didn't mention something, use "Not specified" rather than making assumptions
- Focus on their actual words and feelings

Respond with ONLY the JSON, no other text.
    """
    
    def _make_request() -> dict[str, Any]:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1000,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        response_text = response.content[0].text.strip()
        
        try:
            # Clean the response to remove markdown code blocks
            cleaned_text = _clean_json_response(response_text)
            return json.loads(cleaned_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response as JSON: {response_text}")
            # Return a fallback structure
            return {
                "workout": "Unable to process workout information",
                "eating_feelings": "Unable to process eating information", 
                "short_term_goals": []
            }
    
    try:
        result = _retry_with_backoff(_make_request)
        logger.info("Daily summary generated successfully")
        return result
    except Exception as e:
        logger.error(f"Failed to generate daily summary: {e}")
        # Return fallback structure
        return {
            "workout": "Unable to process workout information",
            "eating_feelings": "Unable to process eating information",
            "short_term_goals": []
        }


def get_weekly_recap(daily_summaries: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Generate a weekly recap from daily summaries.
    
    Args:
        daily_summaries: List of daily summary dictionaries from the past week
        
    Returns:
        dict: Weekly recap with workout_count, general_eating_feeling, slip_ups, and suggested_reflection
        
    Raises:
        Exception: If API call fails after retries
    """
    summaries_text = ""
    for i, summary in enumerate(daily_summaries, 1):
        summaries_text += f"""
Day {i}:
- Workout: {summary.get('workout', 'Not specified')}
- Eating Feelings: {summary.get('eating_feelings', 'Not specified')}
- Goals: {', '.join(summary.get('short_term_goals', []))}
        """
    
    prompt = f"""
You are a fitness accountability coach. Analyze the past week's daily summaries and provide a comprehensive weekly recap.

Daily summaries from this week:
{summaries_text}

Please provide a JSON response with the following structure:
{{
    "workout_count": number, // count of days where the user had a meaningful workout
    "general_eating_feeling": "brief summary of overall eating patterns/feelings this week",
    "slip_ups": "comma-separated list of foods/eating behaviors they struggled with, or 'None reported' if none",
    "suggested_reflection": "one encouraging sentence about their progress and/or a gentle suggestion for next week"
}}

Guidelines:
- Be encouraging and supportive in tone
- Count workouts only if they seem meaningful (not just "didn't work out" or similar)
- Focus on patterns across the week
- Keep slip_ups factual but non-judgmental
- Make the reflection personal and motivating

Respond with ONLY the JSON, no other text.
    """
    
    def _make_request() -> dict[str, Any]:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1000,
            messages=[
                {
                    "role": "user", 
                    "content": prompt
                }
            ]
        )
        
        response_text = response.content[0].text.strip()
        
        try:
            # Clean the response to remove markdown code blocks
            cleaned_text = _clean_json_response(response_text)
            return json.loads(cleaned_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response as JSON: {response_text}")
            # Return a fallback structure
            return {
                "workout_count": len([s for s in daily_summaries if s.get('workout', '').lower() not in ['not specified', 'none', '']]),
                "general_eating_feeling": "Mixed feelings about eating this week",
                "slip_ups": "Unable to analyze slip-ups",
                "suggested_reflection": "Keep up the great work and stay consistent!"
            }
    
    try:
        result = _retry_with_backoff(_make_request)
        logger.info("Weekly recap generated successfully")
        return result
    except Exception as e:
        logger.error(f"Failed to generate weekly recap: {e}")
        # Return fallback structure
        return {
            "workout_count": len([s for s in daily_summaries if s.get('workout', '').lower() not in ['not specified', 'none', '']]),
            "general_eating_feeling": "Mixed feelings about eating this week",
            "slip_ups": "Unable to analyze slip-ups", 
            "suggested_reflection": "Keep up the great work and stay consistent!"
        }


def test_claude_connection() -> bool:
    """
    Test the connection to Claude API.
    
    Returns:
        bool: True if connection is successful, False otherwise
    """
    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=100,
            messages=[
                {
                    "role": "user",
                    "content": "Hello, please respond with 'Connection successful'"
                }
            ]
        )
        
        response_text = response.content[0].text.strip()
        success = "Connection successful" in response_text
        
        if success:
            logger.info("Claude API connection test successful")
        else:
            logger.warning(f"Claude API connection test failed: {response_text}")
            
        return success
        
    except Exception as e:
        logger.error(f"Claude API connection test failed: {e}")
        return False 
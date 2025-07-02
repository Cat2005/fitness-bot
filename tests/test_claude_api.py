"""
Unit tests for claude_api module.

Tests the Claude API integration with mocked external calls.
"""

from __future__ import annotations

import json
from unittest.mock import Mock, patch

import pytest

from claude_api import get_daily_summary, get_weekly_recap, test_claude_connection


class TestGetDailySummary:
    """Test the get_daily_summary function."""

    @patch('claude_api.client')
    def test_get_daily_summary_success(self, mock_client: Mock) -> None:
        """Test successful daily summary generation."""
        # Mock successful API response
        mock_response = Mock()
        mock_content = Mock()
        mock_content.text = json.dumps({
            "workout": "Great gym session today!",
            "eating_feelings": "Felt good about my meals",
            "short_term_goals": ["Drink more water", "Sleep early"]
        })
        mock_response.content = [mock_content]
        mock_client.messages.create.return_value = mock_response
        
        result = get_daily_summary("Previous context", "Had a great workout and ate well")
        
        expected = {
            "workout": "Great gym session today!",
            "eating_feelings": "Felt good about my meals",
            "short_term_goals": ["Drink more water", "Sleep early"]
        }
        assert result == expected
        mock_client.messages.create.assert_called_once()

    @patch('claude_api.client')
    def test_get_daily_summary_invalid_json(self, mock_client: Mock) -> None:
        """Test handling of invalid JSON response."""
        # Mock API response with invalid JSON
        mock_response = Mock()
        mock_content = Mock()
        mock_content.text = "Invalid JSON response"
        mock_response.content = [mock_content]
        mock_client.messages.create.return_value = mock_response
        
        result = get_daily_summary("Previous context", "Had a workout")
        
        # Should return fallback structure
        expected = {
            "workout": "Unable to process workout information",
            "eating_feelings": "Unable to process eating information",
            "short_term_goals": []
        }
        assert result == expected

    @patch('claude_api._retry_with_backoff')
    def test_get_daily_summary_api_error(self, mock_retry: Mock) -> None:
        """Test handling of API errors."""
        # Mock retry function to raise exception
        mock_retry.side_effect = Exception("API Error")
        
        result = get_daily_summary("Previous context", "Had a workout")
        
        # Should return fallback structure
        expected = {
            "workout": "Unable to process workout information",
            "eating_feelings": "Unable to process eating information",
            "short_term_goals": []
        }
        assert result == expected

    @patch('claude_api.client')
    def test_get_daily_summary_proper_prompt_format(self, mock_client: Mock) -> None:
        """Test that the prompt is properly formatted."""
        # Mock successful API response
        mock_response = Mock()
        mock_content = Mock()
        mock_content.text = json.dumps({
            "workout": "Test workout",
            "eating_feelings": "Test eating",
            "short_term_goals": []
        })
        mock_response.content = [mock_content]
        mock_client.messages.create.return_value = mock_response
        
        history = "Previous workout history"
        user_reply = "Today I did cardio"
        
        get_daily_summary(history, user_reply)
        
        # Verify the prompt contains both history and user reply
        call_args = mock_client.messages.create.call_args
        prompt = call_args[1]['messages'][0]['content']
        assert history in prompt
        assert user_reply in prompt
        assert "JSON response" in prompt


class TestGetWeeklyRecap:
    """Test the get_weekly_recap function."""

    @patch('claude_api.client')
    def test_get_weekly_recap_success(self, mock_client: Mock) -> None:
        """Test successful weekly recap generation."""
        # Mock successful API response
        mock_response = Mock()
        mock_content = Mock()
        mock_content.text = json.dumps({
            "workout_count": 4,
            "general_eating_feeling": "Generally good choices",
            "slip_ups": "Pizza on Friday",
            "suggested_reflection": "Great progress this week!"
        })
        mock_response.content = [mock_content]
        mock_client.messages.create.return_value = mock_response
        
        daily_summaries = [
            {
                "date": "2024-01-01",
                "workout": "Gym session",
                "eating_feelings": "Good",
                "short_term_goals": ["Sleep early"]
            },
            {
                "date": "2024-01-02",
                "workout": "Rest day",
                "eating_feelings": "Ate too much pizza",
                "short_term_goals": ["Drink water"]
            }
        ]
        
        result = get_weekly_recap(daily_summaries)
        
        expected = {
            "workout_count": 4,
            "general_eating_feeling": "Generally good choices",
            "slip_ups": "Pizza on Friday",
            "suggested_reflection": "Great progress this week!"
        }
        assert result == expected
        mock_client.messages.create.assert_called_once()

    @patch('claude_api.client')
    def test_get_weekly_recap_invalid_json(self, mock_client: Mock) -> None:
        """Test handling of invalid JSON response."""
        # Mock API response with invalid JSON
        mock_response = Mock()
        mock_content = Mock()
        mock_content.text = "Invalid JSON response"
        mock_response.content = [mock_content]
        mock_client.messages.create.return_value = mock_response
        
        daily_summaries = [
            {
                "date": "2024-01-01",
                "workout": "Gym session",
                "eating_feelings": "Good",
                "short_term_goals": []
            }
        ]
        
        result = get_weekly_recap(daily_summaries)
        
        # Should return fallback structure with workout count based on summaries
        assert "workout_count" in result
        assert "general_eating_feeling" in result
        assert "slip_ups" in result
        assert "suggested_reflection" in result
        assert result["workout_count"] == 1  # Should count the gym session

    @patch('claude_api._retry_with_backoff')
    def test_get_weekly_recap_api_error(self, mock_retry: Mock) -> None:
        """Test handling of API errors."""
        # Mock retry function to raise exception
        mock_retry.side_effect = Exception("API Error")
        
        daily_summaries = [
            {
                "date": "2024-01-01",
                "workout": "Great workout",
                "eating_feelings": "Good",
                "short_term_goals": []
            },
            {
                "date": "2024-01-02",
                "workout": "not specified",
                "eating_feelings": "Bad",
                "short_term_goals": []
            }
        ]
        
        result = get_weekly_recap(daily_summaries)
        
        # Should return fallback structure
        assert result["workout_count"] == 1  # Should count only the "Great workout"
        assert "general_eating_feeling" in result
        assert result["suggested_reflection"] == "Keep up the great work and stay consistent!"

    @patch('claude_api.client')
    def test_get_weekly_recap_prompt_formatting(self, mock_client: Mock) -> None:
        """Test that weekly recap prompt is properly formatted."""
        # Mock successful API response
        mock_response = Mock()
        mock_content = Mock()
        mock_content.text = json.dumps({
            "workout_count": 1,
            "general_eating_feeling": "Good",
            "slip_ups": "None reported",
            "suggested_reflection": "Keep it up!"
        })
        mock_response.content = [mock_content]
        mock_client.messages.create.return_value = mock_response
        
        daily_summaries = [
            {
                "date": "2024-01-01",
                "workout": "Morning run",
                "eating_feelings": "Satisfied with meals",
                "short_term_goals": ["Early sleep", "More vegetables"]
            }
        ]
        
        get_weekly_recap(daily_summaries)
        
        # Verify the prompt contains summary data
        call_args = mock_client.messages.create.call_args
        prompt = call_args[1]['messages'][0]['content']
        assert "Morning run" in prompt
        assert "Satisfied with meals" in prompt
        assert "Early sleep" in prompt
        assert "More vegetables" in prompt
        assert "Day 1:" in prompt


class TestRetryWithBackoff:
    """Test the _retry_with_backoff function."""

    @patch('claude_api.time.sleep')
    def test_retry_success_first_attempt(self, mock_sleep: Mock) -> None:
        """Test successful execution on first attempt."""
        from claude_api import _retry_with_backoff
        
        def mock_func():
            return "success"
        
        result = _retry_with_backoff(mock_func)
        
        assert result == "success"
        mock_sleep.assert_not_called()

    @patch('claude_api.time.sleep')
    def test_retry_success_second_attempt(self, mock_sleep: Mock) -> None:
        """Test successful execution on second attempt."""
        from claude_api import _retry_with_backoff
        
        call_count = 0
        def mock_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("First failure")
            return "success"
        
        result = _retry_with_backoff(mock_func)
        
        assert result == "success"
        assert call_count == 2
        mock_sleep.assert_called_once()

    @patch('claude_api.time.sleep')
    def test_retry_all_attempts_fail(self, mock_sleep: Mock) -> None:
        """Test when all retry attempts fail."""
        from claude_api import _retry_with_backoff
        
        def mock_func():
            raise Exception("Always fails")
        
        with pytest.raises(Exception, match="Always fails"):
            _retry_with_backoff(mock_func)
        
        # Should sleep for MAX_RETRIES - 1 times
        assert mock_sleep.call_count == 2  # MAX_RETRIES is 3, so 2 sleeps

    @patch('claude_api.time.sleep')
    def test_retry_exponential_backoff(self, mock_sleep: Mock) -> None:
        """Test that retry uses exponential backoff."""
        from claude_api import _retry_with_backoff
        
        def mock_func():
            raise Exception("Always fails")
        
        with pytest.raises(Exception):
            _retry_with_backoff(mock_func)
        
        # Verify exponential backoff pattern
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        assert len(sleep_calls) == 2
        assert sleep_calls[1] > sleep_calls[0]  # Second delay should be longer


class TestTestClaudeConnection:
    """Test the test_claude_connection function."""

    @patch('claude_api.client')
    def test_connection_success(self, mock_client: Mock) -> None:
        """Test successful connection test."""
        # Mock successful API response
        mock_response = Mock()
        mock_content = Mock()
        mock_content.text = "Connection successful"
        mock_response.content = [mock_content]
        mock_client.messages.create.return_value = mock_response
        
        result = test_claude_connection()
        
        assert result is True
        mock_client.messages.create.assert_called_once()

    @patch('claude_api.client')
    def test_connection_wrong_response(self, mock_client: Mock) -> None:
        """Test connection test with wrong response."""
        # Mock API response with unexpected content
        mock_response = Mock()
        mock_content = Mock()
        mock_content.text = "Unexpected response"
        mock_response.content = [mock_content]
        mock_client.messages.create.return_value = mock_response
        
        result = test_claude_connection()
        
        assert result is False

    @patch('claude_api.client')
    def test_connection_api_error(self, mock_client: Mock) -> None:
        """Test connection test with API error."""
        # Mock API error
        mock_client.messages.create.side_effect = Exception("API Error")
        
        result = test_claude_connection()
        
        assert result is False


class TestClaudeApiIntegration:
    """Integration-style tests for Claude API functions."""

    def test_daily_summary_fallback_structure(self) -> None:
        """Test that fallback structures have correct format."""
        with patch('claude_api.client') as mock_client:
            mock_client.messages.create.side_effect = Exception("API Error")
            
            result = get_daily_summary("context", "user input")
            
            # Verify fallback has all required keys
            assert "workout" in result
            assert "eating_feelings" in result
            assert "short_term_goals" in result
            assert isinstance(result["short_term_goals"], list)

    def test_weekly_recap_workout_counting(self) -> None:
        """Test workout counting logic in fallback scenarios."""
        daily_summaries = [
            {"workout": "Great gym session", "eating_feelings": "Good", "short_term_goals": []},
            {"workout": "not specified", "eating_feelings": "Bad", "short_term_goals": []},
            {"workout": "none", "eating_feelings": "OK", "short_term_goals": []},
            {"workout": "", "eating_feelings": "Great", "short_term_goals": []},
            {"workout": "Morning run", "eating_feelings": "Excellent", "short_term_goals": []}
        ]
        
        with patch('claude_api.client') as mock_client:
            mock_client.messages.create.side_effect = Exception("API Error")
            
            result = get_weekly_recap(daily_summaries)
            
            # Should count 2 workouts: "Great gym session" and "Morning run"
            assert result["workout_count"] == 2 
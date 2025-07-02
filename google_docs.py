"""
Google Docs API integration for fitness coach bot.

This module provides functions to append content to Google Docs
using the Google Docs REST v1 API with service account authentication.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import GOOGLE_CREDENTIALS_PATH, MAX_RETRIES, RETRY_BACKOFF, RETRY_DELAY

logger = logging.getLogger(__name__)

# Google Docs API scope
SCOPES = ['https://www.googleapis.com/auth/documents']

# Global service instance
_docs_service = None


def _get_docs_service():
    """
    Get or create Google Docs service instance.
    
    Returns:
        Google Docs service instance
        
    Raises:
        Exception: If service cannot be created
    """
    global _docs_service
    
    if _docs_service is None:
        try:
            credentials = Credentials.from_service_account_file(
                GOOGLE_CREDENTIALS_PATH,
                scopes=SCOPES
            )
            _docs_service = build('docs', 'v1', credentials=credentials)
            logger.info("Google Docs service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Google Docs service: {e}")
            raise
    
    return _docs_service


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
        except HttpError as e:
            last_exception = e
            if e.resp.status in [429, 500, 502, 503, 504]:  # Retryable errors
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAY * (RETRY_BACKOFF ** attempt)
                    logger.warning(f"Attempt {attempt + 1} failed with HTTP {e.resp.status}: {e}. Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    logger.error(f"All {MAX_RETRIES} attempts failed")
            else:
                # Non-retryable error
                logger.error(f"Non-retryable error: {e}")
                break
        except Exception as e:
            last_exception = e
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAY * (RETRY_BACKOFF ** attempt)
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                time.sleep(delay)
            else:
                logger.error(f"All {MAX_RETRIES} attempts failed")
    
    raise last_exception


def get_document_content(doc_id: str) -> dict[str, Any]:
    """
    Get the content of a Google Doc.
    
    Args:
        doc_id: Google Doc ID
        
    Returns:
        dict: Document content and metadata
        
    Raises:
        Exception: If document cannot be retrieved
    """
    def _make_request() -> dict[str, Any]:
        service = _get_docs_service()
        return service.documents().get(documentId=doc_id).execute()
    
    try:
        result = _retry_with_backoff(_make_request)
        logger.info(f"Successfully retrieved document content for {doc_id}")
        return result
    except Exception as e:
        logger.error(f"Failed to get document content: {e}")
        raise


def append_to_doc(doc_id: str, heading: str, content: str) -> None:
    """
    Append content to a Google Doc with a heading.
    
    The content will be inserted at the beginning of the document (after title)
    with the newest entries on top.
    
    Args:
        doc_id: Google Doc ID
        heading: Heading text to add
        content: Content to add under the heading
        
    Raises:
        Exception: If content cannot be appended
    """
    def _make_request() -> None:
        service = _get_docs_service()
        
        # First, get the document to find the insertion point
        doc = service.documents().get(documentId=doc_id).execute()
        
        # Find insertion point (after title, at the beginning of content)
        # We'll insert at index 1 to place content at the very beginning
        insert_index = 1
        
        # Prepare the requests for batch update
        requests = [
            # Insert heading
            {
                'insertText': {
                    'location': {'index': insert_index},
                    'text': f'\n{heading}\n'
                }
            },
            # Style the heading as Heading 2
            {
                'updateParagraphStyle': {
                    'range': {
                        'startIndex': insert_index + 1,
                        'endIndex': insert_index + len(heading) + 1
                    },
                    'paragraphStyle': {
                        'namedStyleType': 'HEADING_2'
                    },
                    'fields': 'namedStyleType'
                }
            },
            # Insert content
            {
                'insertText': {
                    'location': {'index': insert_index + len(heading) + 2},
                    'text': f'{content}\n'
                }
            },
            # Add some spacing after content
            {
                'insertText': {
                    'location': {'index': insert_index + len(heading) + len(content) + 3},
                    'text': '\n'
                }
            }
        ]
        
        # Execute the batch update
        service.documents().batchUpdate(
            documentId=doc_id,
            body={'requests': requests}
        ).execute()
    
    try:
        _retry_with_backoff(_make_request)
        logger.info(f"Successfully appended content to document {doc_id}")
    except Exception as e:
        logger.error(f"Failed to append content to document: {e}")
        raise


def create_fitness_log_doc(title: str = "Fitness Coach Bot Log") -> str:
    """
    Create a new Google Doc for fitness logging.
    
    Args:
        title: Title for the new document
        
    Returns:
        str: Document ID of the created document
        
    Raises:
        Exception: If document cannot be created
    """
    def _make_request() -> str:
        service = _get_docs_service()
        
        # Create the document
        doc = service.documents().create(body={'title': title}).execute()
        doc_id = doc.get('documentId')
        
        # Add initial content
        initial_content = f"""
Welcome to your Fitness Coach Bot Log! 🏋️‍♂️

This document will automatically track your daily check-ins and weekly recaps.
The newest entries will appear at the top.

Created: {time.strftime('%Y-%m-%d %H:%M:%S')}

---

        """
        
        requests = [
            {
                'insertText': {
                    'location': {'index': 1},
                    'text': initial_content
                }
            }
        ]
        
        service.documents().batchUpdate(
            documentId=doc_id,
            body={'requests': requests}
        ).execute()
        
        return doc_id
    
    try:
        result = _retry_with_backoff(_make_request)
        logger.info(f"Successfully created fitness log document: {result}")
        return result
    except Exception as e:
        logger.error(f"Failed to create fitness log document: {e}")
        raise


def test_docs_connection(doc_id: str) -> bool:
    """
    Test the connection to Google Docs API.
    
    Args:
        doc_id: Google Doc ID to test with
        
    Returns:
        bool: True if connection is successful, False otherwise
    """
    try:
        doc = get_document_content(doc_id)
        title = doc.get('title', 'Unknown')
        logger.info(f"Google Docs API connection test successful. Document title: {title}")
        return True
    except Exception as e:
        logger.error(f"Google Docs API connection test failed: {e}")
        return False


def get_doc_url(doc_id: str) -> str:
    """
    Get the URL for a Google Doc.
    
    Args:
        doc_id: Google Doc ID
        
    Returns:
        str: URL to the Google Doc
    """
    return f"https://docs.google.com/document/d/{doc_id}/edit"


def search_recent_entries(doc_id: str, days: int = 7) -> list[str]:
    """
    Search for recent entries in the document.
    
    Args:
        doc_id: Google Doc ID
        days: Number of recent days to search for
        
    Returns:
        list: List of recent entry texts
    """
    try:
        doc = get_document_content(doc_id)
        content = doc.get('body', {}).get('content', [])
        
        # Extract all text content
        full_text = ""
        for element in content:
            if 'paragraph' in element and 'elements' in element['paragraph']:
                for elem in element['paragraph']['elements']:
                    if 'textRun' in elem and 'content' in elem['textRun']:
                        full_text += elem['textRun']['content']
        
        # Split by daily check-in entries
        entries = []
        lines = full_text.split('\n')
        current_entry = []
        
        for line in lines:
            if line.strip().startswith('Daily Check-in:'):
                if current_entry:
                    entries.append('\n'.join(current_entry))
                current_entry = [line.strip()]
            elif line.strip() == '---':
                if current_entry:
                    entries.append('\n'.join(current_entry))
                    current_entry = []
            elif current_entry:
                current_entry.append(line.strip())
        
        # Add the last entry if it exists
        if current_entry:
            entries.append('\n'.join(current_entry))
        
        # Return most recent entries (reverse order since newest are at top)
        recent_entries = entries[:days] if len(entries) >= days else entries
        
        logger.info(f"Found {len(recent_entries)} recent entries")
        return recent_entries
        
    except Exception as e:
        logger.error(f"Failed to search recent entries: {e}")
        return []


def get_daily_summaries_from_doc(doc_id: str, days: int = 7) -> list[dict[str, Any]]:
    """
    Extract structured daily summaries from Google Doc.
    
    Args:
        doc_id: Google Doc ID
        days: Number of recent days to get summaries for
        
    Returns:
        list: List of structured daily summary dictionaries
    """
    try:
        doc = get_document_content(doc_id)
        content = doc.get('body', {}).get('content', [])
        
        # Extract all text content
        full_text = ""
        for element in content:
            if 'paragraph' in element and 'elements' in element['paragraph']:
                for elem in element['paragraph']['elements']:
                    if 'textRun' in elem and 'content' in elem['textRun']:
                        full_text += elem['textRun']['content']
        
        # Parse daily summaries
        summaries = []
        lines = full_text.split('\n')
        
        i = 0
        while i < len(lines) and len(summaries) < days:
            line = lines[i].strip()
            
            if line.startswith('Daily Check-in:'):
                # Extract date from heading
                date_str = line.replace('Daily Check-in:', '').strip()
                
                # Look for the summary section
                summary_data = {
                    'date': date_str,
                    'workout': 'Not specified',
                    'eating_feelings': 'Not specified',
                    'short_term_goals': []
                }
                
                # Parse the summary section
                j = i + 1
                while j < len(lines) and not lines[j].strip().startswith('---'):
                    line_content = lines[j].strip()
                    
                    if line_content.startswith('• Workout:'):
                        summary_data['workout'] = line_content.replace('• Workout:', '').strip()
                    elif line_content.startswith('• Eating Feelings:'):
                        summary_data['eating_feelings'] = line_content.replace('• Eating Feelings:', '').strip()
                    elif line_content.startswith('• Short-term Goals:'):
                        goals_text = line_content.replace('• Short-term Goals:', '').strip()
                        if goals_text and goals_text != 'Not specified':
                            summary_data['short_term_goals'] = [
                                goal.strip() for goal in goals_text.split(',') if goal.strip()
                            ]
                    
                    j += 1
                
                summaries.append(summary_data)
                i = j
            else:
                i += 1
        
        logger.info(f"Extracted {len(summaries)} daily summaries from Google Doc")
        return summaries
        
    except Exception as e:
        logger.error(f"Failed to get daily summaries from doc: {e}")
        return [] 
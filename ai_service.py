#!/usr/bin/env python3
"""
AI Service
Handles AI-related functionality including prompt generation, LLM integration, and API management
"""

import os
import requests
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv
from utils import read_file_content, write_file_content

# Load environment variables from .env file
load_dotenv()


def query_gemini(content: str, gemini_key: str = None) -> str:
    """
    Query Gemini LLM using REST API.
    
    Args:
        content: The text content to send to Gemini
        gemini_key: The Gemini API key (defaults to GEMINI_API_KEY env var)
    
    Returns:
        The response from Gemini
    """
    # Get API key from parameter or environment variable
    api_key = gemini_key or os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("Gemini API key must be provided via --gemini-key argument or GEMINI_API_KEY environment variable")
    
    # Use default model from environment
    model_name = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
    
    headers = {
        'Content-Type': 'application/json',
        'X-goog-api-key': api_key
    }
    
    data = {
        "contents": [{
            "parts": [{
                "text": content
            }]
        }]
    }
    
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    
    result = response.json()
    
    if 'candidates' in result and len(result['candidates']) > 0:
        return result['candidates'][0]['content']['parts'][0]['text']
    else:
        return "No response generated from Gemini"


class AIService:
    """Handles AI operations including prompt generation, LLM communication, and API management"""
    
    def __init__(self, force=False):
        self.force = force
    
    def generate_prompt(self, video_id: str, cache_dir: str, metadata: Dict[str, Any], 
                       flattened_subtitles: str) -> None:

        prompt_content = read_file_content("prompt.txt")
        lines = [prompt_content, ""]
        
        lines.append(f"Title: {metadata.get('title', 'Unknown')}")
        lines.append(f"Channel: {metadata.get('channel_name')}")
        lines.append("Description:")
        lines.append(metadata.get('description', ''))
        lines.append("")        
        lines.append("Subtitles:")
        lines.append(flattened_subtitles)
        
        final_content = '\n'.join(lines)
        
        final_path = os.path.join(cache_dir, video_id, 'final.txt')
        write_file_content(final_path, final_content)
        return final_content
    
    def process_with_gemini(self, video_id: str, cache_dir: str, metadata: Dict[str, Any], 
                           flattened_subtitles: str, gemini_key: str = None) -> str:
        
        # Check if we already have a cached response (unless force is True)
        if not self.force:
            return self._load_cached_response(video_id, cache_dir)
        
        prompt = self.generate_prompt(video_id, cache_dir, metadata, flattened_subtitles)
        
        response = query_gemini(prompt, gemini_key)
        
        # Cache the response
        self._save_response_to_cache(video_id, cache_dir, response)
        
        return response
    
    def _get_title_cache_path(self, video_id: str, cache_dir: str) -> str:
        """Get the cache file path for the title response"""
        video_cache_dir = os.path.join(cache_dir, video_id)
        if not os.path.exists(video_cache_dir):
            os.makedirs(video_cache_dir)
        return os.path.join(video_cache_dir, 'title.txt')
    
    def _load_cached_response(self, video_id: str, cache_dir: str) -> str:
        """Load cached response if it exists"""
        cache_path = self._get_title_cache_path(video_id, cache_dir)
        if os.path.exists(cache_path):
            content = read_file_content(cache_path)
            # If the content is JSON, extract the title
            if content.strip().startswith('{'):
                import json
                try:
                    data = json.loads(content)
                    return data.get('title', content)
                except json.JSONDecodeError:
                    return content
            return content
        return None
    
    def _save_response_to_cache(self, video_id: str, cache_dir: str, response: str) -> None:
        """Save response to cache"""
        cache_path = self._get_title_cache_path(video_id, cache_dir)
        write_file_content(cache_path, response)
    
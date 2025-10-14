#!/usr/bin/env python3
"""
AI Service
Handles AI-related functionality including prompt generation, LLM integration, and API management
"""

import os
import requests
from pathlib import Path
from typing import Dict, Any
from utils import read_file_content, write_file_content


def query_gemini(content: str, model_name: str = "gemini-2.0-flash") -> str:
    """
    Query Gemini LLM using REST API.
    
    Args:
        content: The text content to send to Gemini
        model_name: The Gemini model to use (default: gemini-2.0-flash)
    
    Returns:
        The response from Gemini
    """
    # Hardcoded API key for now
    api_key = "AIzaSyDr5EAUV6MzVwwP349drugnHXEJOeFGUoA"
    
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
    
    def __init__(self):
        pass
    
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
                           flattened_subtitles: str, model_name: str = "gemini-2.0-flash") -> str:
        
        prompt = self.generate_prompt(video_id, cache_dir, metadata, flattened_subtitles)
        
        return query_gemini(prompt, model_name)
    
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
from utils import read_file_content, write_file_content, count_tokens, get_model_token_limit, truncate_text_to_token_limit, get_groq_tpm_limit, parse_groq_rate_limit_error, debug_print

load_dotenv()

# Universal token limit for all API requests
def get_universal_token_limit() -> int:
    """Get the universal token limit for API requests (default: 4000)"""
    return int(os.getenv('MAX_PROMPT_TOKENS', '4000'))

def query_gemini(content: str, api_key: str) -> str:
    if not api_key:
        raise ValueError("Gemini API key must be provided")
    
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


def query_groq(content: str, api_key: str) -> str:
    """Query GROQ LLM using REST API."""
    if not api_key:
        raise ValueError("GROQ API key must be provided")
    
    model_name = os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile')
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    
    data = {
        "messages": [{
            "role": "user",
            "content": content
        }],
        "model": model_name
    }
    
    response = requests.post(url, headers=headers, json=data)
    
    # Capture detailed error information
    if not response.ok:
        error_details = f"HTTP {response.status_code}"
        rate_limit_info = None
        try:
            error_json = response.json()
            if 'error' in error_json:
                error_info = error_json['error']
                error_type = error_info.get('type', 'unknown')
                error_message = error_info.get('message', 'No error message')
                error_details = f"{error_type}: {error_message}"
                # Include code if available
                if 'code' in error_info:
                    error_details += f" (code: {error_info['code']})"
                
                # Try to parse rate limit information from error message
                rate_limit_info = parse_groq_rate_limit_error(error_message)
                if rate_limit_info:
                    debug_print(f"DEBUG: Parsed rate limit from error - TPM Limit: {rate_limit_info.get('tpm_limit')}, "
                              f"Requested: {rate_limit_info.get('tpm_requested')}, "
                              f"Tier: {rate_limit_info.get('service_tier')}")
        except Exception:
            error_details += f": {response.text[:200]}"
        
        raise requests.exceptions.HTTPError(
            f"Groq API error - {error_details} for url: {response.url}"
        )
    
    result = response.json()
    
    if 'choices' in result and len(result['choices']) > 0:
        return result['choices'][0]['message']['content']
    else:
        return "No response generated from GROQ"


def query_openrouter(content: str, api_key: str) -> str:
    """Query OpenRouter LLM using REST API."""
    if not api_key:
        raise ValueError("OpenRouter API key must be provided")
    
    model_name = os.getenv('OPENROUTER_MODEL')
    if not model_name:
        raise ValueError("OPENROUTER_MODEL environment variable must be set")
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}',
        'HTTP-Referer': 'https://github.com/yourusername/rebait',  # Optional: for analytics
        'X-Title': 'Rebait'  # Optional: for analytics
    }
    
    data = {
        "messages": [{
            "role": "user",
            "content": content
        }],
        "model": model_name
    }
    
    response = requests.post(url, headers=headers, json=data)
    
    if not response.ok:
        error_details = f"HTTP {response.status_code}"
        try:
            error_json = response.json()
            if 'error' in error_json:
                error_info = error_json['error']
                error_type = error_info.get('type', 'unknown')
                error_message = error_info.get('message', 'No error message')
                error_details = f"{error_type}: {error_message}"
        except Exception:
            error_details += f": {response.text[:200]}"
        
        raise requests.exceptions.HTTPError(
            f"OpenRouter API error - {error_details} for url: {response.url}"
        )
    
    result = response.json()
    
    if 'choices' in result and len(result['choices']) > 0:
        return result['choices'][0]['message']['content']
    else:
        return "No response generated from OpenRouter"


def query_llm(prompt: str) -> str:
    """
    Generic function to query any LLM API with a prompt string.
    
    Uses the AI_PROVIDER environment variable to determine which API to use.
    Supported providers: 'gemini', 'groq', 'openrouter'
    
    Args:
        prompt: The prompt string to send to the LLM
    
    Returns:
        The response text from the LLM
    
    Raises:
        ValueError: If required API keys or configuration are missing
        requests.exceptions.HTTPError: If the API request fails
    """
    provider = os.getenv('AI_PROVIDER', 'groq').lower()
    
    if provider == 'groq':
        api_key = os.getenv('GROQ_API_KEY')
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable is required when using GROQ provider")
        return query_groq(prompt, api_key)
    
    elif provider == 'gemini':
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required when using Gemini provider")
        return query_gemini(prompt, api_key)
    
    elif provider == 'openrouter':
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is required when using OpenRouter provider")
        model_name = os.getenv('OPENROUTER_MODEL')
        if not model_name:
            raise ValueError("OPENROUTER_MODEL environment variable must be set when using OpenRouter provider")
        return query_openrouter(prompt, api_key)
    
    else:
        raise ValueError(f"Unsupported provider: {provider}. Supported providers are 'gemini', 'groq', and 'openrouter'")


class AIService:
    """Handles AI operations including prompt generation, LLM communication, and API management"""
    
    def __init__(self, api_key: str, force=False):
        self.api_key = api_key
        self.force = force
    
    def generate_prompt(self, video_id: str, cache_dir: str, metadata: Dict[str, Any], 
                       flattened_subtitles: str) -> None:

        script_dir = os.path.dirname(os.path.abspath(__file__))
        prompt_path = os.path.join(script_dir, "prompt.txt")
        prompt_content = read_file_content(prompt_path)
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
                           flattened_subtitles: str, prompt: str = None) -> str:
        
        if not self.force:
            cached_response = self._load_cached_response(video_id, cache_dir)
            if cached_response is not None:
                return cached_response
        
        if prompt is None:
            prompt = self.generate_prompt(video_id, cache_dir, metadata, flattened_subtitles)
        
        # Apply universal token limit before sending to API
        model_name = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')
        token_count = count_tokens(prompt, model_name)
        universal_limit = get_universal_token_limit()
        
        debug_print(f"DEBUG: Final prompt token count: {token_count} tokens (model: {model_name})")
        debug_print(f"DEBUG: Universal token limit: {universal_limit} tokens")
        
        if token_count > universal_limit:
            excess = token_count - universal_limit
            debug_print(f"DEBUG: WARNING: Prompt exceeds universal limit by {excess} tokens! Truncating...")
            # Truncate the prompt to fit within the universal limit
            prompt = truncate_text_to_token_limit(prompt, universal_limit, model_name)
            new_token_count = count_tokens(prompt, model_name)
            debug_print(f"DEBUG: Truncated prompt token count: {new_token_count} tokens")
        
        response = query_gemini(prompt, self.api_key)
        self._save_response_to_cache(video_id, cache_dir, response)
        
        return response
    
    def process_with_llm(self, video_id: str, cache_dir: str, metadata: Dict[str, Any], 
                        flattened_subtitles: str, prompt: str = None) -> str:
        """
        Process with LLM using provider from AI_PROVIDER env var (default: groq).
        Supports Gemini, GROQ, and OpenRouter.
        """
        provider = os.getenv('AI_PROVIDER', 'groq').lower()
        
        if not self.force:
            cached_response = self._load_cached_response(video_id, cache_dir)
            if cached_response is not None:
                return cached_response
        
        if prompt is None:
            prompt = self.generate_prompt(video_id, cache_dir, metadata, flattened_subtitles)
        
        # Apply universal token limit before sending to API
        model_name = None
        if provider == 'groq':
            model_name = os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile')
        elif provider == 'gemini':
            model_name = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')
        elif provider == 'openrouter':
            model_name = os.getenv('OPENROUTER_MODEL')
            if not model_name:
                raise ValueError("OPENROUTER_MODEL environment variable must be set when using OpenRouter provider")
        
        token_count = count_tokens(prompt, model_name)
        universal_limit = get_universal_token_limit()
        
        debug_print(f"DEBUG: Final prompt token count: {token_count} tokens (model: {model_name})")
        debug_print(f"DEBUG: Universal token limit: {universal_limit} tokens")
        
        if token_count > universal_limit:
            excess = token_count - universal_limit
            debug_print(f"DEBUG: WARNING: Prompt exceeds universal limit by {excess} tokens! Truncating...")
            # Truncate the prompt to fit within the universal limit
            prompt = truncate_text_to_token_limit(prompt, universal_limit, model_name)
            new_token_count = count_tokens(prompt, model_name)
            debug_print(f"DEBUG: Truncated prompt token count: {new_token_count} tokens")
        
        if provider == 'groq':
            groq_key = os.getenv('GROQ_API_KEY')
            if not groq_key:
                raise ValueError("GROQ_API_KEY environment variable is required when using GROQ provider")
            response = query_groq(prompt, groq_key)
        elif provider == 'gemini':
            response = query_gemini(prompt, self.api_key)
        elif provider == 'openrouter':
            openrouter_key = os.getenv('OPENROUTER_API_KEY')
            if not openrouter_key:
                raise ValueError("OPENROUTER_API_KEY environment variable is required when using OpenRouter provider")
            response = query_openrouter(prompt, openrouter_key)
        else:
            raise ValueError(f"Unsupported provider: {provider}. Supported providers are 'gemini', 'groq', and 'openrouter'")
        
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
    
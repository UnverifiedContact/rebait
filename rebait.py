#!/usr/bin/env python3

import os
import json
import argparse
import requests
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from metadata_fetcher import YouTubeMetadataFetcher
from ai_service import AIService
from utils import extract_youtube_id, Timer, format_duration, format_video_duration, debug_print

# Load environment variables from .env file
load_dotenv()

def fetch_transcript_from_service(video_id, service_host, service_port, cache_dir, force=False):
    """Fetch transcript from external HTTP service with caching"""
    # Check cache first if not forcing refresh
    if not force:
        cache_path = os.path.join(cache_dir, video_id, 'transcript.json')
        if os.path.exists(cache_path):
            debug_print("DEBUG: Found cached transcript, returning cached result")
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    
    # Make HTTP request to external service
    url = f"http://{service_host}:{service_port}/transcript/{video_id}?force={int(force)}"
    debug_print(f"DEBUG: Making request to: {url}")
    
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    
    transcript_data = response.json()
    debug_print(f"DEBUG: Received {len(transcript_data.get('transcript', transcript_data))} transcript segments")
    
    # Save to cache
    os.makedirs(os.path.join(cache_dir, video_id), exist_ok=True)
    cache_path = os.path.join(cache_dir, video_id, 'transcript.json')
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(transcript_data, f, indent=2, ensure_ascii=False)
    
    return transcript_data

def generate_flattened_text(transcript_data, video_id, cache_dir):
    """Generate flattened text from transcript data"""
    import re
    
    if transcript_data is None:
        return ""
    
    # Extract transcript segments from response format
    transcript_segments = transcript_data['transcript']
    
    regex_pattern = re.compile(r'^\s*>>\s*')
    cache_folder = os.path.join(cache_dir, video_id)
    output_path = os.path.join(cache_folder, 'flattened.txt')
    
    flattened_lines = []
    for segment in transcript_segments:
        text = segment.get('text', '')
        if regex_pattern.match(text):
            # Remove >> prefix for dialogue lines
            clean_text = regex_pattern.sub('', text)
            flattened_lines.append(clean_text)
        elif text.strip():  # Include all non-empty text segments
            flattened_lines.append(text)
    
    flattened_text = '\n'.join(flattened_lines)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(flattened_text)
    
    return flattened_text

def validate_cached_data(video_id, cache_dir, metadata_fetcher):
    """Validate that required cached files exist for AI-only mode. Returns list of missing files."""
    missing_files = []
    
    # Check transcript cache
    transcript_path = os.path.join(cache_dir, video_id, 'transcript.json')
    if not os.path.exists(transcript_path):
        missing_files.append('transcript.json')
    
    # Check metadata cache
    if metadata_fetcher._load_from_cache(video_id) is None:
        missing_files.append('metadata.json')
    
    # Check flattened text cache
    flattened_path = os.path.join(cache_dir, video_id, 'flattened.txt')
    if not os.path.exists(flattened_path):
        missing_files.append('flattened.txt')
    
    return missing_files

def load_cached_data(video_id, cache_dir, metadata_fetcher):
    """Load cached transcript, metadata, and flattened text"""
    video_cache_dir = os.path.join(cache_dir, video_id)
    
    # Load transcript
    transcript_path = os.path.join(video_cache_dir, 'transcript.json')
    with open(transcript_path, 'r', encoding='utf-8') as f:
        transcript = json.load(f)
    
    # Load metadata
    metadata = metadata_fetcher._load_from_cache(video_id)
    
    # Load flattened text
    flattened_path = os.path.join(video_cache_dir, 'flattened.txt')
    with open(flattened_path, 'r', encoding='utf-8') as f:
        flattened_text = f.read()
    
    return transcript, metadata, flattened_text

def fetch_video_data(cache_dir, metadata_fetcher, url, video_id, service_host, service_port, force=False):
    """Fetch transcript and metadata in parallel with timing"""
    def timed_get_transcript():
        with Timer("transcript") as timer:
            result = fetch_transcript_from_service(video_id, service_host, service_port, cache_dir, force)
        return result, timer.duration
    
    def timed_fetch_metadata():
        with Timer("metadata") as timer:
            result = metadata_fetcher.fetch_metadata()
        return result, timer.duration
    
    with ThreadPoolExecutor(max_workers=2) as executor:
        transcript_future = executor.submit(timed_get_transcript)
        metadata_future = executor.submit(timed_fetch_metadata)
        
        transcript, transcript_duration = transcript_future.result()
        metadata, metadata_duration = metadata_future.result()
    
    return transcript, transcript_duration, metadata, metadata_duration

def main():
    parser = argparse.ArgumentParser(description='Fetch YouTube transcripts')
    parser.add_argument('url', help='YouTube video URL')
    parser.add_argument('--cache-dir', default=os.path.join(os.environ.get('TMP', '/tmp'), 'rebait_cache'), help='Cache directory path (default: $TMP/rebait_cache)')
    parser.add_argument('--gemini-key', help='Gemini API key (optional, defaults to GEMINI_API_KEY env var)')
    parser.add_argument('-f', '--force', action='store_true', help='Force refresh all cached data')
    parser.add_argument('-a', '--ai-only', action='store_true', help='Only run the AI step to regenerate title, skip transcript/metadata fetching (requires existing cached data)')
    
    args = parser.parse_args()
    cache_dir = args.cache_dir
    
    video_id = extract_youtube_id(args.url)
    if not video_id:
        print(f"Error: Could not extract video ID from URL: {args.url}")
        return 1
    
    api_key = args.gemini_key or os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("Error: Gemini API key must be provided via --gemini-key argument or GEMINI_API_KEY environment variable")
        return 1
    
    debug_print(f"DEBUG: Using HTTP transcript service...")
    
    # Get transcript service configuration from environment
    service_host = os.getenv('TRANSCRIPT_SERVICE_HOST', 'localhost')
    service_port = os.getenv('TRANSCRIPT_SERVICE_PORT', '5485')
    debug_print(f"DEBUG: Service host: {service_host}, port: {service_port}")
    
    # Get YouTube Data API v3 key from environment
    youtube_api_key = os.getenv('YOUTUBE_V3_API_KEY')
    metadata_fetcher = YouTubeMetadataFetcher(video_id=video_id, cache_dir=cache_dir, force=args.force, youtube_data_api_key=youtube_api_key)

    ai_force = args.force or args.ai_only
    ai_service = AIService(api_key=api_key, force=(ai_force or args.ai_only))
    
    try:
        # Measure total wall-clock time
        with Timer("total") as total_timer:
            if args.ai_only:
                # Validate cached data exists
                missing_files = validate_cached_data(video_id, cache_dir, metadata_fetcher)
                if missing_files:
                    # Fallback to normal mode if cache is missing
                    transcript, transcript_duration, metadata, metadata_duration = \
                        fetch_video_data(cache_dir, metadata_fetcher, args.url, video_id, service_host, service_port, args.force)
                    
                    flattened_text = generate_flattened_text(transcript, video_id, cache_dir)
                else:
                    # Load cached data
                    transcript, metadata, flattened_text = load_cached_data(video_id, cache_dir, metadata_fetcher)
                    transcript_duration = 0  # No time spent fetching
                    metadata_duration = 0    # No time spent fetching
            else:
                # Normal flow: fetch transcript and metadata
                transcript, transcript_duration, metadata, metadata_duration = \
                    fetch_video_data(cache_dir, metadata_fetcher, args.url, video_id, service_host, service_port, args.force)
                
                flattened_text = generate_flattened_text(transcript, video_id, cache_dir)
            
            final_prompt = ai_service.generate_prompt(video_id, cache_dir, metadata, flattened_text)
          
            with Timer("gemini") as gemini_timer:
                gemini_response = ai_service.process_with_gemini(
                    video_id, cache_dir, metadata, flattened_text, final_prompt
                )
        
        total_seconds = total_timer.duration
        
        result = {
            "transcript_time": format_duration(transcript_duration),
            "metadata_time": format_duration(metadata_duration),
            "gemini_time": gemini_timer.get_duration(),
            "total_time": format_duration(total_seconds),
            "video_duration": format_video_duration(int(metadata.get('duration', 0)) if metadata.get('duration', '').strip() else 0),
            "original_title": metadata.get('original_title', ''),
            "title": gemini_response.strip()
        }
        
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

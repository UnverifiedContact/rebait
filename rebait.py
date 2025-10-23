#!/usr/bin/env python3

import os
import json
import argparse
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from transcript_fetcher import YouTubeTranscriptFetcher
from metadata_fetcher import YouTubeMetadataFetcher
from ai_service import AIService
from utils import extract_youtube_id, Timer, format_duration, format_video_duration

def debug_print(message):
    """Print debug message with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]  # Include milliseconds
    print(f"[{timestamp}] {message}")

def validate_cached_data(video_id, transcript_fetcher, metadata_fetcher):
    """Validate that required cached files exist for AI-only mode. Returns list of missing files."""
    missing_files = []
    
    # Check transcript cache
    if transcript_fetcher._load_from_cache(video_id) is None:
        missing_files.append('transcript.json')
    
    # Check metadata cache
    if metadata_fetcher._load_from_cache(video_id) is None:
        missing_files.append('metadata.json')
    
    # Check flattened text cache
    flattened_path = os.path.join(transcript_fetcher.cache_dir, video_id, 'flattened.txt')
    if not os.path.exists(flattened_path):
        missing_files.append('flattened.txt')
    
    return missing_files

def load_cached_data(video_id, cache_dir):
    """Load cached transcript, metadata, and flattened text"""
    video_cache_dir = os.path.join(cache_dir, video_id)
    
    # Load transcript
    transcript_path = os.path.join(video_cache_dir, 'transcript.json')
    with open(transcript_path, 'r', encoding='utf-8') as f:
        transcript = json.load(f)
    
    # Load metadata
    metadata_path = os.path.join(video_cache_dir, 'metadata.json')
    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    
    # Load flattened text
    flattened_path = os.path.join(video_cache_dir, 'flattened.txt')
    with open(flattened_path, 'r', encoding='utf-8') as f:
        flattened_text = f.read()
    
    return transcript, metadata, flattened_text

def fetch_video_data(transcript_fetcher, metadata_fetcher, url, video_id):
    """Fetch transcript and metadata in parallel with timing"""
    def timed_get_transcript():
        with Timer("transcript") as timer:
            result = transcript_fetcher.get_transcript(url)
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
    parser.add_argument('-n', '--no-webshare', action='store_true', help='Do not use webshare credentials')
    
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
    
    webshare_username = None
    webshare_password = None
    if not args.no_webshare:
        debug_print(f"DEBUG: Loading Webshare credentials from environment...")
        webshare_username = os.getenv('WEBSHARE_USERNAME')
        webshare_password = os.getenv('WEBSHARE_PASSWORD')
        debug_print(f"DEBUG: WEBSHARE_USERNAME from env: {webshare_username}")
        debug_print(f"DEBUG: WEBSHARE_PASSWORD from env: {'***' if webshare_password else None}")
        debug_print(f"DEBUG: args.no_webshare: {args.no_webshare}")
    else:
        debug_print(f"DEBUG: Skipping Webshare credentials due to --no-webshare flag")
    
    debug_print(f"DEBUG: About to create YouTubeTranscriptFetcher with username: {webshare_username}")
    
    transcript_fetcher = YouTubeTranscriptFetcher(cache_dir=cache_dir, force=args.force, webshare_username=webshare_username, webshare_password=webshare_password)
    metadata_fetcher = YouTubeMetadataFetcher(video_id=video_id, cache_dir=cache_dir, force=args.force)

    ai_force = args.force or args.ai_only
    ai_service = AIService(api_key=api_key, force=ai_force)
    
    try:
        # Measure total wall-clock time
        with Timer("total") as total_timer:
            if args.ai_only:
                # Validate cached data exists
                missing_files = validate_cached_data(video_id, transcript_fetcher, metadata_fetcher)
                if missing_files:
                    # Fallback to normal mode if cache is missing
                    transcript, transcript_duration, metadata, metadata_duration = \
                        fetch_video_data(transcript_fetcher, metadata_fetcher, args.url, video_id)
                    
                    flattened_text = transcript_fetcher.generate_flattened(transcript, video_id)
                else:
                    # Load cached data
                    transcript, metadata, flattened_text = load_cached_data(video_id, cache_dir)
                    transcript_duration = 0  # No time spent fetching
                    metadata_duration = 0    # No time spent fetching
            else:
                # Normal flow: fetch transcript and metadata
                transcript, transcript_duration, metadata, metadata_duration = \
                    fetch_video_data(transcript_fetcher, metadata_fetcher, args.url, video_id)
                
                flattened_text = transcript_fetcher.generate_flattened(transcript, video_id)
            
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
            "title": gemini_response.strip()
        }
        
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

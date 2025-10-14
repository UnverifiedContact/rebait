#!/usr/bin/env python3

import os
import json
import argparse
from pathlib import Path
from typing import Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from transcript_fetcher import YouTubeTranscriptFetcher
from metadata_fetcher import YouTubeMetadataFetcher
from ai_service import AIService
from utils import extract_youtube_id, Timer, format_duration

def fetch_video_data(transcript_fetcher, metadata_fetcher, url, video_id):
    """Fetch transcript and metadata in parallel with timing"""
    def timed_get_transcript():
        with Timer("transcript") as timer:
            result = transcript_fetcher.get_transcript(url)
        return result, timer.duration
    
    def timed_fetch_metadata():
        with Timer("metadata") as timer:
            result = metadata_fetcher.fetch_metadata(video_id)
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
    
    transcript_fetcher = YouTubeTranscriptFetcher(cache_dir=cache_dir, force=args.force)
    metadata_fetcher = YouTubeMetadataFetcher(cache_dir=cache_dir, force=args.force)
    ai_service = AIService(api_key=api_key, force=args.force)
    
    try:
        # Measure total wall-clock time
        with Timer("total") as total_timer:
            transcript, transcript_duration, metadata, metadata_duration = \
                fetch_video_data(transcript_fetcher, metadata_fetcher, args.url, video_id)
            
            flattened_text = transcript_fetcher.generate_flattened(transcript, video_id)
            ai_service.generate_prompt(video_id, cache_dir, metadata, flattened_text)
          
            with Timer("gemini") as gemini_timer:
                gemini_response = ai_service.process_with_gemini(
                    video_id, cache_dir, metadata, flattened_text
                )
        
        total_seconds = total_timer.duration
        
        result = {
            "transcript_duration": format_duration(transcript_duration),
            "metadata_duration": format_duration(metadata_duration),
            "gemini_duration": gemini_timer.get_duration(),
            "total_duration": format_duration(total_seconds),
            "title": gemini_response.strip()
        }
        
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

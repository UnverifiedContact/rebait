#!/usr/bin/env python3
"""
Rebait - YouTube Transcript Fetcher
A library for fetching and caching YouTube transcripts
"""

import os
import json
import argparse
from pathlib import Path
from typing import Dict, Any
from transcript_fetcher import YouTubeTranscriptFetcher
from metadata_fetcher import YouTubeMetadataFetcher
from ai_service import AIService
from utils import extract_youtube_id, Timer, format_duration


def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(description='Fetch YouTube transcripts')
    parser.add_argument('url', help='YouTube video URL')
    parser.add_argument('--cache-dir', default='cache', help='Cache directory path (default: cache)')
    parser.add_argument('--gemini-model', default='gemini-2.0-flash', help='Gemini model to use (default: gemini-2.0-flash)')
    
    args = parser.parse_args()
    cache_dir = args.cache_dir
    
    # Extract and validate video ID from URL
    video_id = extract_youtube_id(args.url)
    if not video_id:
        print(f"Error: Could not extract video ID from URL: {args.url}")
        return 1
    
    transcript_fetcher = YouTubeTranscriptFetcher(cache_dir=cache_dir)
    metadata_fetcher = YouTubeMetadataFetcher(cache_dir=cache_dir)
    ai_service = AIService()
    
    try:
        transcript_timer = None
        metadata_timer = None
        gemini_timer = None
        
        with Timer("transcript") as transcript_timer:
            transcript = transcript_fetcher.get_transcript(args.url)       
        flattened_text = transcript_fetcher.generate_flattened(transcript['transcript_data'], video_id)

        with Timer("metadata") as metadata_timer:
            metadata = metadata_fetcher.fetch_metadata(video_id)
        ai_service.generate_prompt(video_id, cache_dir, metadata, flattened_text)
      
        with Timer("gemini") as gemini_timer:
            gemini_response = ai_service.process_with_gemini(
                video_id, cache_dir, metadata, flattened_text, args.gemini_model
            )
        
        # Calculate total duration in seconds for formatting
        total_seconds = transcript_timer.duration + metadata_timer.duration + gemini_timer.duration
        
        result = {
            "transcript_duration": transcript_timer.get_duration(),
            "metadata_duration": metadata_timer.get_duration(),
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

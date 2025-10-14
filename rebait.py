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
from utils import extract_youtube_id


def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(description='Fetch YouTube transcripts')
    parser.add_argument('url', help='YouTube video URL')
    parser.add_argument('--cache-dir', default='cache', help='Cache directory path (default: cache)')
    
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
        transcript = transcript_fetcher.get_transcript(args.url)       
        metadata = metadata_fetcher.fetch_metadata(video_id)
        
        print(f"Title: {metadata['title']}")
        print(f"Duration: {metadata['duration']}")
        print(f"Channel: {metadata['channel_name']}")
        print(f"Keywords: {', '.join(metadata['keywords'])}")
        print(f"Description: {metadata['description']}")
        
        # Always create flattened.txt
        flattened_text = transcript_fetcher.generate_flattened(transcript['transcript_data'], video_id)
        
        # Generate final AI prompt
        ai_service.generate_and_save_prompt(video_id, cache_dir, metadata, flattened_text)
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

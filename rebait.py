#!/usr/bin/env python3
"""
Rebait - YouTube Transcript Fetcher
A library for fetching and caching YouTube transcripts
"""

import os
import json
import argparse
from transcript_fetcher import YouTubeTranscriptFetcher
from metadata_fetcher import YouTubeMetadataFetcher


def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(description='Fetch YouTube transcripts')
    parser.add_argument('url', help='YouTube video URL')
    parser.add_argument('--cache-dir', default='cache', help='Cache directory path (default: cache)')
    
    args = parser.parse_args()
    
    fetcher = YouTubeTranscriptFetcher(cache_dir=args.cache_dir)
    
    try:
        result = fetcher.get_transcript(args.url)
        
        # Fetch and display metadata
        metadata_fetcher = YouTubeMetadataFetcher()
        metadata = metadata_fetcher.fetch_metadata(result['video_id'])
        
        print(f"Title: {metadata['title']}")
        print(f"Duration: {metadata['duration']}")
        print(f"Channel: {metadata['channel_name']}")
        print(f"Keywords: {', '.join(metadata['keywords'])}")
        print(f"Description: {metadata['description']}")
        
        # Always create flattened.txt
        cache_folder = os.path.join(fetcher.cache_dir, result['video_id'])
        fetcher.generate_flattened(result['transcript_data'], cache_folder)
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

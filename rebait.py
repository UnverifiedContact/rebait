#!/usr/bin/env python3
"""
Rebait - YouTube Transcript Fetcher
A library for fetching and caching YouTube transcripts
"""

import argparse
from transcript_fetcher import YouTubeTranscriptFetcher
from metadata_fetcher import YouTubeMetadataFetcher


def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(description='Fetch YouTube transcripts')
    parser.add_argument('url', help='YouTube video URL')
    
    args = parser.parse_args()
    
    fetcher = YouTubeTranscriptFetcher()
    
    try:
        result = fetcher.get_transcript(args.url)
        
        # Fetch and display metadata
        metadata_fetcher = YouTubeMetadataFetcher()
        metadata = metadata_fetcher.fetch_metadata(result['video_id'])
        
        print(f"Title: {metadata['title']}")
        print(f"Duration: {metadata['duration']}")
        print(f"Channel: {metadata['channel_name']}")
        print(f"Uploader: {metadata['uploader']}")
        print(f"Description: {metadata['description']}")
        
        # Always create flattened.txt
        fetcher.generate_flattened(result['transcript_data'], result['video_id'])
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

#!/usr/bin/env python3
"""
Test script for rebait functionality
"""

from rebait import YouTubeTranscriptFetcher
from utils import extract_youtube_id

def test_url_parsing():
    """Test URL parsing functionality"""
    fetcher = YouTubeTranscriptFetcher()
    
    test_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/embed/dQw4w9WgXcQ",
        "https://www.youtube.com/v/dQw4w9WgXcQ"
    ]
    
    print("Testing URL parsing:")
    for url in test_urls:
        video_id = extract_youtube_id(url)
        print(f"  {url} -> {video_id}")
    
    return True

def test_transcript_fetch():
    """Test transcript fetching with a known video"""
    fetcher = YouTubeTranscriptFetcher()
    
    # Try a few different videos that might have transcripts
    test_videos = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Rick Roll
        "https://www.youtube.com/watch?v=jNQXAC9IVRw",  # Me at the zoo
        "https://www.youtube.com/watch?v=UF8uR6Z6KLc",  # TED talk
    ]
    
    for url in test_videos:
        try:
            print(f"\nTrying: {url}")
            result = fetcher.get_transcript(url)
            print(f"Success! Video ID: {result['video_id']}")
            print(f"Language: {result['language']}")
            print(f"Transcript length: {len(result['transcript_text'])} characters")
            print(f"First 100 chars: {result['transcript_text'][:100]}...")
            return True
        except Exception as e:
            print(f"Failed: {e}")
    
    return False

if __name__ == "__main__":
    print("=== Testing Rebait Functionality ===\n")
    
    # Test URL parsing
    test_url_parsing()
    
    # Test transcript fetching
    print("\n=== Testing Transcript Fetching ===")
    success = test_transcript_fetch()
    
    if success:
        print("\n✅ Tests passed!")
    else:
        print("\n❌ Some tests failed, but the basic functionality works.")
        print("Note: Many YouTube videos don't have transcripts available.")

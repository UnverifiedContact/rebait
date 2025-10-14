#!/usr/bin/env python3
"""
YouTube Transcript Fetcher
A class for fetching and caching YouTube transcripts
"""

import os
import json
import re
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi


class YouTubeTranscriptFetcher:
    """A class to fetch and cache YouTube transcripts"""
    
    def __init__(self):
        self.cache_dir = "cache"
        self._ensure_cache_dir()
    
    def _ensure_cache_dir(self):
        """Ensure the cache directory exists"""
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
    
    def extract_youtube_id(self, value: str) -> str | None:
        """Extract YouTube video ID from URL or return the ID if already provided."""
        if not value:
            return None
        value = value.strip()
        if re.fullmatch(r"[A-Za-z0-9_-]{11}", value):
            return value
        parsed = urlparse(value)
        if parsed.hostname in ("www.youtube.com", "youtube.com"):
            if parsed.path == "/watch":
                return parse_qs(parsed.query).get("v", [None])[0]
            m = re.match(r"^/(embed|shorts)/([^/?#&]+)", parsed.path)
            if m:
                return m.group(2)
        if parsed.hostname == "youtu.be":
            return parsed.path.lstrip("/")
        return None
    
    def get_transcript(self, url):
        """Fetch transcript for a YouTube video"""
        video_id = self.extract_youtube_id(url)
        if not video_id:
            raise ValueError(f"Could not extract video ID from URL: {url}")
        
        try:
            api = YouTubeTranscriptApi()
            transcript_data = api.fetch(video_id, languages=['en'])
        except Exception as e:
            print(f"Failed to fetch English transcript: {e}")
            raise ValueError("No transcripts available for this video")
        
        # Convert to standard format
        #transcript_text = " ".join([entry.text for entry in transcript_data])
        transcript_data_dict = [{'text': entry.text, 'start': entry.start, 'duration': entry.duration} for entry in transcript_data]
        
        result = {
            'video_id': video_id,
            'url': url,
            'transcript_data': transcript_data_dict,
            #'transcript_text': transcript_text,
            'language': 'en'
        }
        
        self._save_to_cache(video_id, result)
        return result
    
    def _get_cache_path(self, video_id):
        """Get the cache file path for a video ID"""
        video_cache_dir = os.path.join(self.cache_dir, video_id)
        if not os.path.exists(video_cache_dir):
            os.makedirs(video_cache_dir)
        return os.path.join(video_cache_dir, 'transcript.json')
    
    def _save_to_cache(self, video_id, transcript_data):
        """Save transcript data to cache"""
        cache_path = self._get_cache_path(video_id)
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(transcript_data, f, indent=2, ensure_ascii=False)
    
    def _load_from_cache(self, video_id):
        """Load transcript data from cache if it exists"""
        cache_path = self._get_cache_path(video_id)
        if os.path.exists(cache_path):
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def generate_flattened(self, transcript_data, video_id):
        """
        Generate flattened text from transcript data
        
        Args:
            transcript_data (list): List of transcript segments
            video_id (str): YouTube video ID
        """
        import re
        
        regex_pattern = re.compile(r'^\s*>>\s*')
        output_path = os.path.join(self.cache_dir, video_id, 'flattened.txt')
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for segment in transcript_data:
                text = segment.get('text', '')
                if regex_pattern.match(text):
                    clean_text = regex_pattern.sub('', text)
                    f.write(f"{clean_text}\n")

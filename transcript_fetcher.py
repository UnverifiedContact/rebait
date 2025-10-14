#!/usr/bin/env python3
"""
YouTube Transcript Fetcher
A class for fetching and caching YouTube transcripts
"""

import os
import json
from youtube_transcript_api import YouTubeTranscriptApi
from utils import extract_youtube_id


class YouTubeTranscriptFetcher:
    """A class to fetch and cache YouTube transcripts"""
    
    def __init__(self, cache_dir="cache"):
        self.cache_dir = cache_dir
        self._ensure_cache_dir()
    
    def set_cache_dir(self, cache_dir):
        self.cache_dir = cache_dir
        self._ensure_cache_dir()
    
    def _ensure_cache_dir(self):
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
    
    def get_transcript(self, url):
        """Fetch transcript for a YouTube video"""
        video_id = extract_youtube_id(url)
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
        import re
        
        regex_pattern = re.compile(r'^\s*>>\s*')
        cache_folder = os.path.join(self.cache_dir, video_id)
        output_path = os.path.join(cache_folder, 'flattened.txt')
        
        flattened_lines = []
        for segment in transcript_data:
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

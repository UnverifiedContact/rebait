#!/usr/bin/env python3
"""
YouTube Transcript Fetcher
A class for fetching and caching YouTube transcripts
"""

import os
import json
import concurrent.futures
import time
from datetime import datetime
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import WebshareProxyConfig
from utils import extract_youtube_id

def debug_print(message):
    """Print debug message with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]  # Include milliseconds
    print(f"[{timestamp}] {message}")


class YouTubeTranscriptFetcher:
    """A class to fetch and cache YouTube transcripts"""
    
    def __init__(self, cache_dir="cache", force=False, webshare_username=None, webshare_password=None):
        debug_print(f"DEBUG: YouTubeTranscriptFetcher.__init__ called")
        debug_print(f"DEBUG: webshare_username passed: {webshare_username}")
        debug_print(f"DEBUG: webshare_password passed: {'***' if webshare_password else None}")
        self.cache_dir = cache_dir
        self.force = force
        self.webshare_username = webshare_username
        self.webshare_password = webshare_password
        debug_print(f"DEBUG: Final webshare_username: {self.webshare_username}")
        debug_print(f"DEBUG: Final webshare_password: {'***' if self.webshare_password else None}")
        self._ensure_cache_dir()
    
    def set_cache_dir(self, cache_dir):
        self.cache_dir = cache_dir
        self._ensure_cache_dir()
    
    def _ensure_cache_dir(self):
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
    
    def get_transcript(self, url):
        debug_print(f"DEBUG: get_transcript called with URL: {url}")
        video_id = extract_youtube_id(url)
        debug_print(f"DEBUG: Extracted video ID: {video_id}")
        if not video_id:
            raise ValueError(f"Could not extract video ID from URL: {url}")
        
        if not self.force:
            debug_print("DEBUG: Checking cache...")
            cached_data = self._load_from_cache(video_id)
            if cached_data is not None:
                debug_print("DEBUG: Found cached data, returning cached result")
                return cached_data
            debug_print("DEBUG: No cached data found, proceeding to fetch")
        
        # Try concurrent requests if using Webshare proxies, fallback to single request
        debug_print(f"DEBUG: Webshare credentials available: {bool(self.webshare_username and self.webshare_password)}")
        if self.webshare_username and self.webshare_password:
            debug_print("DEBUG: Using Webshare proxies, attempting concurrent requests")
            try:
                transcript_data = self._get_transcript_concurrent(video_id)
                debug_print("DEBUG: Concurrent requests succeeded!")
            except Exception as e:
                debug_print(f"DEBUG: Concurrent requests failed, trying single request: {e}")
                try:
                    debug_print("DEBUG: Attempting single request with Webshare proxies...")
                    transcript_data = self._get_transcript_single(video_id)
                    debug_print("DEBUG: Single request with proxies succeeded!")
                except Exception as e2:
                    debug_print(f"DEBUG: Single request with proxies failed: {e2}")
                    raise ValueError("Failed to download subtitles for this video")
        else:
            debug_print("DEBUG: No Webshare credentials, using single request without proxies")
            try:
                transcript_data = self._get_transcript_single(video_id)
                debug_print("DEBUG: Single request without proxies succeeded!")
            except Exception as e:
                debug_print(f"DEBUG: Single request without proxies failed: {e}")
                raise ValueError("Failed to download subtitles for this video")
        
        transcript_data_dict = [{'text': entry.text, 'start': entry.start, 'duration': entry.duration} for entry in transcript_data]
        
        self._save_to_cache(video_id, transcript_data_dict)
        return transcript_data_dict
    
    def _get_transcript_single(self, video_id):
        """Single transcript fetch attempt"""
        if self.webshare_username and self.webshare_password:
            api = YouTubeTranscriptApi(
                proxy_config=WebshareProxyConfig(
                    proxy_username=self.webshare_username,
                    proxy_password=self.webshare_password
                )
            )
        else:
            api = YouTubeTranscriptApi()
        return api.fetch(video_id, languages=['en'])
    
    def _get_transcript_concurrent(self, video_id, max_concurrent=5):
        """Try multiple concurrent requests to get transcript"""
        import time
        
        debug_print(f"DEBUG: Starting concurrent requests with {max_concurrent} attempts")
        debug_print(f"DEBUG: Video ID: {video_id}")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            futures = []
            
            debug_print(f"DEBUG: Submitting {max_concurrent} concurrent requests...")
            # Submit multiple concurrent requests with staggered timing
            for i in range(max_concurrent):
                debug_print(f"DEBUG: Submitting request {i+1}/{max_concurrent}")
                future = executor.submit(self._single_transcript_attempt, video_id, i+1)
                futures.append(future)
                time.sleep(0.3)  # Small delay between submissions to spread out requests
            
            debug_print(f"DEBUG: Waiting for first successful result from {len(futures)} requests...")
            # Wait for first successful result
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    if result is not None:
                        debug_print(f"DEBUG: SUCCESS! Concurrent request succeeded, cancelling remaining {len(futures)-1} attempts")
                        # Cancel remaining futures
                        for f in futures:
                            f.cancel()
                        return result
                except Exception as e:
                    debug_print(f"DEBUG: Concurrent attempt failed: {e}")
            
            debug_print(f"DEBUG: All {max_concurrent} concurrent attempts failed")
            raise ValueError("All concurrent attempts failed")
    
    def _get_transcript_sequential(self, video_id, max_attempts=5):
        """Sequential requests with delays for Termux/Android environments"""
        import time
        
        print(f"Using sequential requests with {max_attempts} attempts")
        for attempt_id in range(1, max_attempts + 1):
            print(f"Sequential attempt {attempt_id}/{max_attempts}")
            
            # Add delay between attempts to allow IP rotation
            if attempt_id > 1:
                delay = attempt_id * 0.5  # Increasing delay: 0.5s, 1.0s, 1.5s, 2.0s
                print(f"Waiting {delay}s before next attempt...")
                time.sleep(delay)
            
            try:
                result = self._single_transcript_attempt(video_id, attempt_id)
                if result is not None:
                    print(f"Sequential attempt {attempt_id} succeeded!")
                    return result
                else:
                    print(f"Sequential attempt {attempt_id} failed")
            except Exception as e:
                print(f"Sequential attempt {attempt_id} failed with error: {e}")
        
        raise ValueError("All sequential attempts failed")
    
    def _single_transcript_attempt(self, video_id, attempt_id):
        """Single transcript fetch attempt with fresh proxy connection"""
        import time
        import random
        
        debug_print(f"DEBUG: Starting attempt {attempt_id} for video {video_id}")
        
        try:
            # Add small random delay to spread out requests
            delay = random.uniform(0.1, 0.3)
            debug_print(f"DEBUG: Attempt {attempt_id} waiting {delay:.2f}s before request...")
            time.sleep(delay)
            
            debug_print(f"DEBUG: Attempt {attempt_id} creating fresh API instance...")
            debug_print(f"DEBUG: Attempt {attempt_id} using Webshare username: {self.webshare_username}")
            
            # Create fresh API instance for each attempt
            api = YouTubeTranscriptApi(
                proxy_config=WebshareProxyConfig(
                    proxy_username=self.webshare_username,
                    proxy_password=self.webshare_password
                )
            )
            
            debug_print(f"DEBUG: Attempt {attempt_id} calling api.fetch()...")
            transcript_data = api.fetch(video_id, languages=['en'])
            debug_print(f"DEBUG: Attempt {attempt_id} SUCCESS! Got {len(transcript_data)} segments")
            return transcript_data
        except Exception as e:
            debug_print(f"DEBUG: Attempt {attempt_id} FAILED with error: {str(e)[:200]}")
            return None
    
    def _get_cache_path(self, video_id):
        """Get the cache file path for a video ID"""
        video_cache_dir = os.path.join(self.cache_dir, video_id)
        os.makedirs(video_cache_dir, exist_ok=True)
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
                data = json.load(f)
                # Handle both old format (wrapper object) and new format (direct array)
                if isinstance(data, dict) and 'transcript_data' in data:
                    return data['transcript_data']
                elif isinstance(data, list):
                    return data
                else:
                    return data
        return None
    
    def generate_flattened(self, transcript_data, video_id):
        import re
        
        if transcript_data is None:
            return ""
        
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

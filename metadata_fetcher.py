#!/usr/bin/env python3
"""
YouTube Metadata Fetcher
A modular class for fetching YouTube video metadata using innertube API
"""

import requests
import re
import json
import os


class YouTubeMetadataFetcher:
    """Modular metadata fetcher using YouTube innertube API"""
    
    def __init__(self, cache_dir="cache", api_url=None, context=None, force=False):
        self.cache_dir = cache_dir
        self.api_url = api_url or "https://www.youtube.com/youtubei/v1/player?key={api_key}"
        self.context = context or {"client": {"clientName": "ANDROID", "clientVersion": "20.10.38"}}
        self.watch_url = "https://www.youtube.com/watch?v={video_id}"
        self.force = force
        self._ensure_cache_dir()
    
    def set_cache_dir(self, cache_dir):
        self.cache_dir = cache_dir
        self._ensure_cache_dir()
    
    def _ensure_cache_dir(self):
        """Ensure the cache directory exists"""
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
    
    def fetch_metadata(self, video_id):
        if not self.force:
            cached_data = self._load_from_cache(video_id)
            if cached_data is not None:
                return cached_data
        
        metadata = self._fetch_from_api(video_id)
        self._save_to_cache(video_id, metadata)
        
        return metadata
    
    def _fetch_from_api(self, video_id):
        """Fetch video metadata from innertube API"""
        try:
            # Get API key from watch page
            api_key = self._get_api_key(video_id)
            
            response = requests.post(
                self.api_url.format(api_key=api_key),
                json={
                    "context": self.context,
                    "videoId": video_id,
                },
            )
            response.raise_for_status()
            data = response.json()
            
            video_details = data.get('videoDetails', {})
            
            if not video_details:
                raise ValueError(f"Failed to fetch metadata for video {video_id}")
            
            return {
                'title': video_details.get('title', ''),
                'duration': video_details.get('lengthSeconds', ''),
                'description': video_details.get('shortDescription', ''),
                'channel_name': video_details.get('author', ''),
                'channel_id': video_details.get('channelId', ''),
                'keywords': video_details.get('keywords', []),
            }
        except Exception as e:
            print(f"Error fetching metadata: {e}")
            raise ValueError(f"Failed to fetch metadata for video {video_id}: {e}")
    
    def _get_cache_path(self, video_id):
        """Get the cache file path for a video ID"""
        video_cache_dir = os.path.join(self.cache_dir, video_id)
        os.makedirs(video_cache_dir, exist_ok=True)
        return os.path.join(video_cache_dir, 'metadata.json')
    
    def _save_to_cache(self, video_id, metadata):
        """Save metadata to cache"""
        cache_path = self._get_cache_path(video_id)
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    def _load_from_cache(self, video_id):
        """Load metadata from cache if it exists"""
        cache_path = self._get_cache_path(video_id)
        if os.path.exists(cache_path):
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def _get_api_key(self, video_id):
        """Extract innertube API key from watch page"""
        response = requests.get(self.watch_url.format(video_id=video_id))
        response.raise_for_status()
        
        match = re.search(r'"INNERTUBE_API_KEY":\s*"([a-zA-Z0-9_-]+)"', response.text)
        if not match:
            raise ValueError("Could not extract API key")
        
        return match.group(1)

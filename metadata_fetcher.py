#!/usr/bin/env python3
"""
YouTube Metadata Fetcher
A modular class for fetching YouTube video metadata using innertube API
"""

import requests
import re
import json


class YouTubeMetadataFetcher:
    """Modular metadata fetcher using YouTube innertube API"""
    
    INNERTUBE_API_URL = "https://www.youtube.com/youtubei/v1/player?key={api_key}"
    INNERTUBE_CONTEXT = {"client": {"clientName": "ANDROID", "clientVersion": "20.10.38"}}
    WATCH_URL = "https://www.youtube.com/watch?v={video_id}"
    
    def fetch_metadata(self, video_id):
        """Fetch video metadata from innertube API"""
        # Get API key from watch page
        api_key = self._get_api_key(video_id)
        
        # Fetch innertube data
        response = requests.post(
            self.INNERTUBE_API_URL.format(api_key=api_key),
            json={
                "context": self.INNERTUBE_CONTEXT,
                "videoId": video_id,
            },
        )
        response.raise_for_status()
        data = response.json()
        
        # Extract videoDetails
        video_details = data.get('videoDetails', {})
        
        return {
            'title': video_details.get('title', ''),
            'duration': video_details.get('lengthSeconds', ''),
            'description': video_details.get('shortDescription', ''),
            'channel_name': video_details.get('author', ''),
            'channel_id': video_details.get('channelId', ''),
            'keywords': video_details.get('keywords', []),
        }
    
    def _get_api_key(self, video_id):
        """Extract innertube API key from watch page"""
        response = requests.get(self.WATCH_URL.format(video_id=video_id))
        response.raise_for_status()
        
        match = re.search(r'"INNERTUBE_API_KEY":\s*"([a-zA-Z0-9_-]+)"', response.text)
        if not match:
            raise ValueError("Could not extract API key")
        
        return match.group(1)

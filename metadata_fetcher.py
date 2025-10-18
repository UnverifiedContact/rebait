#!/usr/bin/env python3
"""
YouTube Metadata Fetcher
A modular class for fetching YouTube video metadata with multiple fallback methods
"""

import requests
import re
import json
import os
import yt_dlp
from bs4 import BeautifulSoup


class YouTubeMetadataFetcher:
    """Modular metadata fetcher with multiple fallback methods"""
    
    def __init__(self, cache_dir="cache", api_url=None, context=None, force=False):
        self.cache_dir = cache_dir
        self.api_url = api_url or "https://www.youtube.com/youtubei/v1/player?key={api_key}"
        self.context = context or {"client": {"clientName": "WEB", "clientVersion": "2.20251016.01.00"}}
        self.watch_url = "https://www.youtube.com/watch?v={video_id}"
        self.force = force
        self._ensure_cache_dir()
        
        # Initialize yt-dlp options
        self.ytdl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'writethumbnail': False,
            'writeinfojson': False,
        }
    
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
        
        # Try multiple methods in order of preference
        methods = [
            ("innertube_api", self._fetch_from_innertube_api),
            ("yt_dlp", self._fetch_from_ytdlp),
            ("oembed_api", self._fetch_from_oembed_api),
            ("web_scraping", self._fetch_from_web_scraping),
        ]
        
        last_error = None
        for method_name, method_func in methods:
            try:
                print(f"Trying {method_name} for video {video_id}...")
                metadata = method_func(video_id)
                if metadata:
                    self._save_to_cache(video_id, metadata)
                    print(f"Successfully fetched metadata using {method_name}")
                    return metadata
                else:
                    print(f"{method_name} returned empty metadata")
            except Exception as e:
                print(f"{method_name} failed: {e}")
                import traceback
                print(f"Full traceback for {method_name}:")
                traceback.print_exc()
                last_error = e
                continue
        
        # If all methods failed
        raise ValueError(f"All metadata fetching methods failed for video {video_id}. Last error: {last_error}")
    
    def _fetch_from_innertube_api(self, video_id):
        """Fetch video metadata from innertube API"""
        try:
            # Get API key from watch page
            api_key = self._get_api_key(video_id)
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/json',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Content-Type': 'application/json',
                'Origin': 'https://www.youtube.com',
                'Referer': f'https://www.youtube.com/watch?v={video_id}',
                'X-YouTube-Client-Name': '1',
                'X-YouTube-Client-Version': '2.20251016.01.00',
            }
            
            response = requests.post(
                self.api_url.format(api_key=api_key),
                json={
                    "context": self.context,
                    "videoId": video_id,
                },
                headers=headers
            )
            response.raise_for_status()
            
            # Check if response is empty
            if not response.text.strip():
                raise ValueError(f"Empty response from innertube API for video {video_id}")
            
            data = response.json()
            
            # Check for playability issues
            playability_status = data.get('playabilityStatus', {})
            if playability_status.get('status') != 'OK':
                reason = playability_status.get('reason', 'Unknown error')
                raise ValueError(f"Video not playable: {reason}")
            
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
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if not content:
                        print(f"DEBUG: Empty metadata cache file for {video_id}")
                        return None
                    return json.loads(content)
            except json.JSONDecodeError as e:
                print(f"DEBUG: Invalid JSON in metadata cache for {video_id}: {e}")
                return None
            except Exception as e:
                print(f"DEBUG: Error reading metadata cache for {video_id}: {e}")
                return None
        return None
    
    def _get_api_key(self, video_id):
        """Extract innertube API key from watch page"""
        response = requests.get(self.watch_url.format(video_id=video_id))
        response.raise_for_status()
        
        match = re.search(r'"INNERTUBE_API_KEY":\s*"([a-zA-Z0-9_-]+)"', response.text)
        if not match:
            raise ValueError("Could not extract API key")
        
        return match.group(1)
    
    def _fetch_from_ytdlp(self, video_id):
        """Fetch video metadata using yt-dlp"""
        try:
            url = f"https://www.youtube.com/watch?v={video_id}"
            with yt_dlp.YoutubeDL(self.ytdl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                return {
                    'title': info.get('title', ''),
                    'duration': str(info.get('duration', '')),
                    'description': info.get('description', ''),
                    'channel_name': info.get('uploader', ''),
                    'channel_id': info.get('uploader_id', ''),
                    'keywords': info.get('tags', []),
                }
        except Exception as e:
            raise ValueError(f"yt-dlp failed: {e}")
    
    def _fetch_from_oembed_api(self, video_id):
        """Fetch basic metadata using YouTube's oEmbed API"""
        try:
            url = f"https://www.youtube.com/watch?v={video_id}"
            oembed_url = f"https://www.youtube.com/oembed?url={url}&format=json"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            }
            
            response = requests.get(oembed_url, headers=headers)
            response.raise_for_status()
            
            # Check if response is empty
            if not response.text.strip():
                raise ValueError(f"Empty response from oEmbed API for video {video_id}")
            
            data = response.json()
            
            return {
                'title': data.get('title', ''),
                'duration': '',  # oEmbed doesn't provide duration
                'description': '',  # oEmbed doesn't provide description
                'channel_name': data.get('author_name', ''),
                'channel_id': '',  # oEmbed doesn't provide channel ID
                'keywords': [],
            }
        except Exception as e:
            raise ValueError(f"oEmbed API failed: {e}")
    
    def _fetch_from_web_scraping(self, video_id):
        """Fetch basic metadata by scraping the YouTube watch page"""
        try:
            url = f"https://www.youtube.com/watch?v={video_id}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            # Try to extract data from JSON-LD structured data first
            json_ld_pattern = r'<script type="application/ld\+json">(.*?)</script>'
            json_ld_matches = re.findall(json_ld_pattern, response.text, re.DOTALL)
            
            title = ''
            description = ''
            channel_name = ''
            duration = ''
            
            for json_ld in json_ld_matches:
                try:
                    if not json_ld.strip():
                        continue
                    data = json.loads(json_ld)
                    if isinstance(data, dict):
                        if data.get('@type') == 'VideoObject':
                            title = data.get('name', '')
                            description = data.get('description', '')
                            duration = str(data.get('duration', ''))
                            if 'author' in data:
                                channel_name = data['author'].get('name', '')
                        elif isinstance(data, list):
                            for item in data:
                                if item.get('@type') == 'VideoObject':
                                    title = item.get('name', '')
                                    description = item.get('description', '')
                                    duration = str(item.get('duration', ''))
                                    if 'author' in item:
                                        channel_name = item['author'].get('name', '')
                except json.JSONDecodeError:
                    continue
            
            # Fallback to meta tags if JSON-LD didn't work
            if not title:
                soup = BeautifulSoup(response.text, 'html.parser')
                title_element = soup.find('meta', property='og:title')
                title = title_element.get('content', '') if title_element else ''
            
            if not description:
                soup = BeautifulSoup(response.text, 'html.parser')
                desc_element = soup.find('meta', property='og:description')
                description = desc_element.get('content', '') if desc_element else ''
            
            # Try to extract from ytInitialData if available
            yt_initial_data_pattern = r'var ytInitialData = ({.*?});'
            match = re.search(yt_initial_data_pattern, response.text, re.DOTALL)
            if match:
                try:
                    yt_data = json.loads(match.group(1))
                    # Navigate through the complex structure to find video details
                    video_details = self._extract_from_yt_initial_data(yt_data)
                    if video_details:
                        title = video_details.get('title', title)
                        description = video_details.get('description', description)
                        channel_name = video_details.get('channel_name', channel_name)
                        duration = video_details.get('duration', duration)
                except json.JSONDecodeError:
                    pass
            
            # Final fallback: try regex patterns
            if not title:
                title_patterns = [
                    r'"title":"([^"]+)"',
                    r'<title>([^<]+)</title>',
                ]
                for pattern in title_patterns:
                    match = re.search(pattern, response.text)
                    if match:
                        title = match.group(1)
                        break
            
            if not duration:
                duration_patterns = [
                    r'"lengthSeconds":"(\d+)"',
                    r'"duration":"(\d+)"',
                    r'<meta property="video:duration" content="(\d+)"',
                ]
                for pattern in duration_patterns:
                    match = re.search(pattern, response.text)
                    if match:
                        duration = match.group(1)
                        break
            
            return {
                'title': title,
                'duration': duration,
                'description': description,
                'channel_name': channel_name,
                'channel_id': '',
                'keywords': [],
            }
        except Exception as e:
            raise ValueError(f"Web scraping failed: {e}")
    
    def _extract_from_yt_initial_data(self, data):
        """Extract video details from YouTube's ytInitialData structure"""
        try:
            result = {}
            
            # Try to get video details from contents
            contents = data.get('contents', {})
            
            # Method 1: Try twoColumnWatchNextResults
            if 'twoColumnWatchNextResults' in contents:
                results = contents['twoColumnWatchNextResults']
                if 'results' in results and 'results' in results['results']:
                    results_content = results['results']['results']
                    if 'contents' in results_content:
                        for content in results_content['contents']:
                            if 'videoPrimaryInfoRenderer' in content:
                                primary_info = content['videoPrimaryInfoRenderer']
                                title = primary_info.get('title', {}).get('runs', [{}])[0].get('text', '')
                                if title:
                                    result['title'] = title
                            
                            if 'videoSecondaryInfoRenderer' in content:
                                secondary_info = content['videoSecondaryInfoRenderer']
                                if 'owner' in secondary_info:
                                    owner = secondary_info['owner']
                                    if 'videoOwnerRenderer' in owner:
                                        owner_renderer = owner['videoOwnerRenderer']
                                        channel_name = owner_renderer.get('title', {}).get('runs', [{}])[0].get('text', '')
                                        if channel_name:
                                            result['channel_name'] = channel_name
            
            # Method 2: Try to get from playerOverlays
            if 'playerOverlays' in data:
                player_overlays = data['playerOverlays']
                if 'decoratedPlayerBarRenderer' in player_overlays:
                    decorated_bar = player_overlays['decoratedPlayerBarRenderer']
                    if 'decoratedPlayerBarRenderer' in decorated_bar:
                        bar_renderer = decorated_bar['decoratedPlayerBarRenderer']
                        if 'playerBar' in bar_renderer:
                            player_bar = bar_renderer['playerBar']
                            if 'multiMarkersPlayerBarRenderer' in player_bar:
                                markers = player_bar['multiMarkersPlayerBarRenderer']
                                if 'markersList' in markers:
                                    for marker in markers['markersList']:
                                        if 'markerRenderer' in marker:
                                            marker_renderer = marker['markerRenderer']
                                            if 'startTimeMs' in marker_renderer:
                                                duration_ms = marker_renderer['startTimeMs']
                                                if duration_ms:
                                                    result['duration'] = str(int(duration_ms) // 1000)
            
            # Method 3: Try to get from currentVideoEndpoint
            if 'currentVideoEndpoint' in data:
                video_endpoint = data['currentVideoEndpoint']
                if 'watchEndpoint' in video_endpoint:
                    watch_endpoint = video_endpoint['watchEndpoint']
                    if 'videoId' in watch_endpoint:
                        # We already have the video ID, but this confirms it's the right video
                        pass
            
            # Method 4: Try to extract from page structure
            if 'contents' in data:
                contents = data['contents']
                if 'twoColumnWatchNextResults' in contents:
                    results = contents['twoColumnWatchNextResults']
                    if 'results' in results:
                        results_data = results['results']
                        if 'results' in results_data:
                            results_list = results_data['results']
                            if 'contents' in results_list:
                                for content in results_list['contents']:
                                    # Look for video details in various renderers
                                    if 'videoPrimaryInfoRenderer' in content:
                                        primary = content['videoPrimaryInfoRenderer']
                                        if 'title' in primary:
                                            title_obj = primary['title']
                                            if 'runs' in title_obj:
                                                title_text = ''.join([run.get('text', '') for run in title_obj['runs']])
                                                if title_text:
                                                    result['title'] = title_text
                                    
                                    if 'videoSecondaryInfoRenderer' in content:
                                        secondary = content['videoSecondaryInfoRenderer']
                                        if 'owner' in secondary:
                                            owner = secondary['owner']
                                            if 'videoOwnerRenderer' in owner:
                                                owner_renderer = owner['videoOwnerRenderer']
                                                if 'title' in owner_renderer:
                                                    title_obj = owner_renderer['title']
                                                    if 'runs' in title_obj:
                                                        channel_text = ''.join([run.get('text', '') for run in title_obj['runs']])
                                                        if channel_text:
                                                            result['channel_name'] = channel_text
            
            return result
        except (KeyError, IndexError, TypeError, AttributeError) as e:
            print(f"Error extracting from ytInitialData: {e}")
            return {}

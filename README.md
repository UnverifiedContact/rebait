# Rebait - YouTube Transcript Fetcher

A Python library and CLI tool for fetching and caching YouTube video transcripts.

## Features

- Fetch transcripts from YouTube videos using various URL formats
- Automatic caching system to avoid repeated API calls
- Support for multiple languages
- Command-line interface for easy usage
- Library interface for programmatic use
- **Transcript analysis and filtering** with regex patterns
- **Multiple output formats** (WEBVTT, SRT, filtered text files)

## Installation

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Command Line Interface

Basic usage:
```bash
python rebait.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

With options:
```bash
python rebait.py "https://www.youtube.com/watch?v=VIDEO_ID" --display --languages en es fr
```

### As a Library

```python
from rebait import YouTubeTranscriptFetcher

fetcher = YouTubeTranscriptFetcher(cache_dir="my_cache")
result = fetcher.get_transcript("https://www.youtube.com/watch?v=VIDEO_ID")

print(f"Transcript: {result['transcript_text']}")
```

### Transcript Analysis

```python
from rebait import YouTubeTranscriptFetcher

fetcher = YouTubeTranscriptFetcher()

# Analyze dialogue lines (lines starting with >>)
dialogue = fetcher.analyze_transcript("VIDEO_ID", pattern=r'^\s*>>\s*', output_filename='dialogue.txt')

# Analyze music cues
music = fetcher.analyze_transcript("VIDEO_ID", pattern=r'\[Music\]', output_filename='music.txt')

# Custom pattern analysis
custom = fetcher.analyze_transcript("VIDEO_ID", pattern=r'.*[Rr]obocop.*')
```

### Transcript Analysis

```bash
# Fetch transcript and automatically create flattened.txt with dialogue lines
python rebait.py "https://www.youtube.com/watch?v=VIDEO_ID"

# Use custom regex pattern for flattening
python rebait.py "https://www.youtube.com/watch?v=VIDEO_ID" --pattern "\[Music\]"
```

## Cache Structure

Transcripts are cached in the following structure:
```
cache/
└── {youtube_id}/
    ├── transcript.json          # Original transcript data
    └── flattened.txt            # Cleaned dialogue lines (always created)
```

## Supported URL Formats

- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://youtube.com/watch?v=VIDEO_ID`
- `https://youtu.be/VIDEO_ID`
- `https://www.youtube.com/embed/VIDEO_ID`
- `https://www.youtube.com/v/VIDEO_ID`

## Command Line Options

- `url`: YouTube video URL (required)
- `--cache-dir`: Cache directory path (default: cache)
- `--languages`: Preferred languages in order (default: en)
- `--display`: Display transcript text to console

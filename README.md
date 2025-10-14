# Rebait - YouTube De-Clickbaited Video Titles

A Python tool to analyze YouTube video metadata to produce accurate, concise, non-clickbaity titles.

## Features

- **Parallel Processing**: Fetches transcripts and metadata simultaneously for faster execution
- **Intelligent Caching**: Avoids repeated API calls with automatic caching system
- **AI-Powered Analysis**: Uses Google Gemini API to generate intelligent summaries
- **Transcript Filtering**: Automatically filters dialogue lines and creates flattened text
- **Comprehensive Metadata**: Fetches video title, duration, description, and channel information
- **Performance Benchmarking**: Detailed timing information for each operation

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd rebait
```

2. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up Google Gemini API key:
```bash
export GOOGLE_API_KEY="your-api-key-here"
```

## Usage

### Basic Usage

```bash
python rebait.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

### Advanced Options

```bash
# Specify cache directory
python rebait.py "https://www.youtube.com/watch?v=VIDEO_ID" --cache-dir my_cache

# Use different Gemini model
python rebait.py "https://www.youtube.com/watch?v=VIDEO_ID" --gemini-model gemini-1.5-pro
```

### Output Format

The tool outputs JSON with timing information and AI-generated summary:

```json
{
  "transcript_duration": "2.5s",
  "metadata_duration": "1.2s", 
  "gemini_duration": "3.8s",
  "total_duration": "7.5s",
  "title": "AI-generated summary of the video content"
}
```

## How It Works

1. **Parallel Fetching**: Simultaneously fetches transcript and metadata
2. **Caching**: Checks cache first to avoid redundant API calls
3. **Text Processing**: Filters transcript to extract dialogue lines
4. **AI Analysis**: Sends processed content to Gemini for intelligent summarization
5. **Performance Tracking**: Measures and reports timing for each operation

## Cache Structure

```
cache/
└── {youtube_id}/
    ├── transcript.json          # Original transcript data
    ├── metadata.json           # Video metadata
    ├── flattened.txt           # Filtered dialogue lines
    ├── final.txt              # AI-generated summary
    └── gemini_response.txt     # Raw AI response (optional)
```

**Note**: Cache entries may contain different combinations of files depending on processing stage:
- **Complete**: All 5 files present (fully processed)
- **Partial**: Some files missing (processing interrupted or failed)
- **Empty**: Directory exists but no files (failed initial fetch)

## Supported URL Formats

- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://youtube.com/watch?v=VIDEO_ID`
- `https://youtu.be/VIDEO_ID`
- `https://www.youtube.com/embed/VIDEO_ID`
- `https://www.youtube.com/v/VIDEO_ID`

## Requirements

- Python 3.7+
- Google Gemini API key
- Internet connection for API calls

## Performance Benefits

- **Parallel Execution**: Transcript and metadata fetching run simultaneously
- **Smart Caching**: Subsequent runs are significantly faster
- **Efficient Processing**: Only processes new content when cache is empty

## Error Handling

The tool gracefully handles:
- Missing transcripts
- Network connectivity issues
- Invalid YouTube URLs
- API rate limiting

## Development

The codebase is modular with separate components:
- `transcript_fetcher.py`: Handles YouTube transcript API
- `metadata_fetcher.py`: Fetches video metadata
- `ai_service.py`: Manages Gemini API interactions
- `utils.py`: Utility functions and timing
- `rebait.py`: Main CLI interface
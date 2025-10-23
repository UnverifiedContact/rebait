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

4. Set up environment variables:
```bash
# Copy the example environment file
cp env.example .env

# Edit .env with your actual API keys and service configuration
nano .env
```

Required environment variables:
- `GEMINI_API_KEY`: Your Google Gemini API key
- `TRANSCRIPT_SERVICE_HOST`: Host for transcript service (default: localhost)
- `TRANSCRIPT_SERVICE_PORT`: Port for transcript service (default: 5485)
- `YOUTUBE_V3_API_KEY`: Your YouTube Data API v3 key (optional, for metadata)

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

## Configuration

### Transcript Service
The tool now uses an external HTTP service for transcript fetching instead of direct YouTube API calls. Configure the service endpoint using:

- `TRANSCRIPT_SERVICE_HOST`: Hostname or IP of the transcript service (default: localhost)
- `TRANSCRIPT_SERVICE_PORT`: Port number of the transcript service (default: 5485)

The service should respond to GET requests at: `http://{host}:{port}/transcript/{video_id}`

### Environment Variables
All configuration is done through environment variables. See `env.example` for a complete list of available options.

## How It Works

1. **Parallel Fetching**: Simultaneously fetches transcript and metadata
2. **External Service**: Uses HTTP service for transcript fetching
3. **Caching**: Checks cache first to avoid redundant API calls
4. **Text Processing**: Filters transcript to extract dialogue lines
5. **AI Analysis**: Sends processed content to Gemini for intelligent summarization
6. **Performance Tracking**: Measures and reports timing for each operation

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
- `rebait.py`: Main CLI interface with HTTP transcript service integration
- `metadata_fetcher.py`: Fetches video metadata
- `ai_service.py`: Manages Gemini API interactions
- `utils.py`: Utility functions and timing
- `env.example`: Environment variables template
import re
import os
import time
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from typing import Dict, Any, Optional
import tiktoken

# Import static model limits (no API calls needed)
try:
    from groq_model_limits import GROQ_MODEL_LIMITS
except ImportError:
    # Fallback if limits file doesn't exist
    GROQ_MODEL_LIMITS = {}


def extract_youtube_id(value: str) -> str | None:
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


def read_file_content(file_path: str) -> str:
    """Read content from a file as string"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def write_file_content(file_path: str, content: str) -> None:
    """Write content to a file"""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)


class Timer:
    """Simple timer context manager for benchmarking operations"""
    
    def __init__(self, name: str):
        self.name = name
        self.start_time = None
        self.duration = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.duration = time.time() - self.start_time
    
    def get_duration(self) -> str:
        """Get duration formatted in a human-readable way"""
        return format_duration(self.duration or 0.0)


def format_duration(seconds: float) -> str:
    """Format duration in a human-readable way with time unit suffix"""
    if seconds < 1:
        return f"{seconds*1000:.1f}ms"
    elif seconds < 60:
        minutes = int(seconds // 60)
        remaining_seconds = int(round(seconds % 60))
        return f"{minutes}:{remaining_seconds:02d}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        remaining_seconds = int(seconds % 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{remaining_seconds:02d}s"
        else:
            return f"{minutes:02d}:{remaining_seconds:02d}s"

def debug_print(message):
    """Print debug message with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]  # Include milliseconds
    print(f"[{timestamp}] {message}")


def parse_duration_iso8601(duration_iso: str) -> int | None:
    """Parse ISO 8601 duration format (PT4M13S) to seconds"""
    if not duration_iso:
        return None
    
    # Match PT(optional hours)H(optional minutes)M(optional seconds)S
    pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
    match = re.match(pattern, duration_iso)
    
    if not match:
        return None
    
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    
    return hours * 3600 + minutes * 60 + seconds


def format_video_duration(seconds: float) -> str:
    """Format video duration in HH:MM:SS format without time unit suffix"""
    if seconds < 60:
        minutes = int(seconds // 60)
        remaining_seconds = int(round(seconds % 60))
        return f"{minutes}:{remaining_seconds:02d}"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        remaining_seconds = int(seconds % 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{remaining_seconds:02d}"
        else:
            return f"{minutes:02d}:{remaining_seconds:02d}"


def parse_groq_rate_limit_error(error_message: str) -> Optional[Dict[str, Any]]:
    """
    Parse Groq API error message to extract rate limit information.
    
    Example error message:
    "tokens: Request too large for model `meta-llama/llama-4-maverick-17b-128e-instruct` 
     in organization `org_xxx` service tier `on_demand` on tokens per minute (TPM): 
     Limit 6000, Requested 8069, please reduce your message size and try again."
    
    Args:
        error_message: The error message from Groq API
    
    Returns:
        Dictionary with 'tpm_limit', 'tpm_requested', 'service_tier', 'model' if found,
        or None if parsing fails
    """
    import re
    
    # Pattern to match TPM limit information
    tpm_pattern = r'tokens per minute \(TPM\):\s*Limit\s+(\d+),\s*Requested\s+(\d+)'
    tier_pattern = r'service tier\s+`([^`]+)`'
    model_pattern = r'model\s+`([^`]+)`'
    
    tpm_match = re.search(tpm_pattern, error_message)
    tier_match = re.search(tier_pattern, error_message)
    model_match = re.search(model_pattern, error_message)
    
    if tpm_match:
        result = {
            'tpm_limit': int(tpm_match.group(1)),
            'tpm_requested': int(tpm_match.group(2)),
        }
        if tier_match:
            result['service_tier'] = tier_match.group(1)
        if model_match:
            result['model'] = model_match.group(1)
        return result
    
    return None


def get_groq_tpm_limit(model_name: str, api_key: str = None) -> Optional[int]:
    """
    Get the TPM (tokens per minute) limit for a Groq model from static table.
    No API calls - uses pre-fetched limits.
    
    Args:
        model_name: The model name
        api_key: Ignored (kept for compatibility)
    
    Returns:
        TPM limit as integer, or None if unknown
    """
    # Check static limits table first
    if model_name in GROQ_MODEL_LIMITS:
        return GROQ_MODEL_LIMITS[model_name].get('tpm_limit')
    
    # Fallback for unknown models
    model_lower = model_name.lower()
    if "llama-3.3" in model_lower:
        return 12000  # Higher limit for 70b model
    elif "llama" in model_lower or "gpt-oss" in model_lower or "qwen" in model_lower or "kimi" in model_lower:
        return 6000
    elif "groq/compound" in model_lower:
        return 6000
    elif "allam" in model_lower:
        return 6000
    
    # Default fallback
    return 6000


def get_all_groq_models(api_key: str = None) -> Optional[list[str]]:
    """
    Fetch all available Groq models from the API.
    
    Args:
        api_key: Optional Groq API key. If None, tries to get from environment.
    
    Returns:
        List of model IDs (strings), or None if the query fails.
    """
    if not api_key:
        import os
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.getenv('GROQ_API_KEY')
    
    if not api_key:
        return None
    
    try:
        import requests
        headers = {'Authorization': f'Bearer {api_key}'}
        
        # Get all models
        response = requests.get(
            'https://api.groq.com/openai/v1/models',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            models_data = response.json().get('data', [])
            # Filter to only chat completion models (exclude TTS, whisper, guard, safeguard)
            chat_models = [
                m.get('id') for m in models_data 
                if not any(x in m.get('id', '').lower() for x in ['tts', 'whisper', 'guard', 'safeguard'])
            ]
            return sorted(chat_models)
        else:
            return None
    except Exception:
        return None


def get_all_openrouter_models(api_key: str = None) -> Optional[list[str]]:
    """
    Fetch all available OpenRouter models from the API.
    
    Args:
        api_key: Optional OpenRouter API key. If None, tries to get from environment.
    
    Returns:
        List of model IDs (strings), or None if the query fails.
    """
    if not api_key:
        import os
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.getenv('OPENROUTER_API_KEY')
    
    if not api_key:
        return None
    
    try:
        import requests
        headers = {'Authorization': f'Bearer {api_key}'}
        
        # Get all models
        response = requests.get(
            'https://openrouter.ai/api/v1/models',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            models_data = response.json().get('data', [])
            # Extract model IDs
            model_ids = [m.get('id') for m in models_data if m.get('id')]
            return sorted(model_ids)
        else:
            return None
    except Exception:
        return None


def get_groq_model_limits(model_name: str, api_key: str = None) -> Optional[Dict[str, Any]]:
    """
    Query Groq's API to get actual model limits dynamically.
    
    Args:
        model_name: The model name to query
        api_key: Optional Groq API key. If None, tries to get from environment.
    
    Returns:
        Dictionary with 'context_window', 'max_completion_tokens', and 'max_input_tokens' if available,
        or None if the query fails.
    """
    if not api_key:
        import os
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.getenv('GROQ_API_KEY')
    
    if not api_key:
        return None
    
    try:
        import requests
        headers = {'Authorization': f'Bearer {api_key}'}
        
        # Query the specific model endpoint
        response = requests.get(
            f'https://api.groq.com/openai/v1/models/{model_name}',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            model_data = response.json()
            limits = {
                'context_window': model_data.get('context_window'),
                'max_completion_tokens': model_data.get('max_completion_tokens'),
            }
            # Calculate max input tokens (context window minus max completion tokens)
            if limits['context_window'] and limits['max_completion_tokens']:
                limits['max_input_tokens'] = limits['context_window'] - limits['max_completion_tokens']
            return limits
        else:
            return None
    except Exception:
        return None


def get_model_token_limit(model_name: str = None, api_key: str = None, use_api: bool = False) -> Optional[int]:
    """
    Get the token limit (max input tokens) for a given model from static table.
    No API calls - uses pre-fetched limits.
    
    Args:
        model_name: The model name to get the limit for.
                   If None, returns None.
        api_key: Ignored (kept for compatibility)
        use_api: Ignored (kept for compatibility, but no longer makes API calls)
    
    Returns:
        Token limit as an integer (max_input_tokens if available, otherwise context_window),
        or None if unknown
    """
    if not model_name:
        return None
    
    # Check static limits table first (no API calls!)
    if model_name in GROQ_MODEL_LIMITS:
        limits = GROQ_MODEL_LIMITS[model_name]
        # Prefer max_input_tokens (context_window - max_completion_tokens)
        if limits.get('max_input_tokens'):
            return limits['max_input_tokens']
        elif limits.get('context_window'):
            # If max_input_tokens is 0 or missing, use context_window minus safety margin
            return limits['context_window'] - 8192
    
    # Fallback to static mapping for non-Groq models or if not in table
    model_lower = model_name.lower()
    model_limits = {
        # Llama models
        "llama-3.1-8b-instant": 120000,  # 128k - 8k safety margin
        "llama-3.3-70b-versatile": 120000,
        "meta-llama/llama-4-maverick-17b-128e-instruct": 120000,  # 128e = 128k extended
        "meta-llama/llama-4-scout-17b-16e-instruct": 8192,  # 16e = 16k extended, minus safety
        # OpenAI models
        "openai/gpt-oss-120b": 120000,
        "openai/gpt-oss-20b": 120000,
        # Qwen models
        "qwen/qwen3-32b": 120000,
        # Moonshot models
        "moonshotai/kimi-k2-instruct": 120000,
        "moonshotai/kimi-k2-instruct-0905": 120000,
        # Groq compound models
        "groq/compound": 120000,
        "groq/compound-mini": 120000,
        # Allam models
        "allam-2-7b": 4096,  # Smaller model, likely smaller context
        # Gemini models (for reference, though they use different counting)
        "gemini-2.0-flash": 1000000,  # Gemini uses different tokenization
        "gemini-1.5-pro": 2000000,
    }
    
    # Check exact match first
    if model_name in model_limits:
        return model_limits[model_name]
    
    # Check partial matches for model families
    if "llama-4" in model_lower and "128e" in model_lower:
        return 120000
    elif "llama-4" in model_lower and "16e" in model_lower:
        return 8192
    elif "llama" in model_lower:
        return 120000  # Default for Llama 3.x models
    elif "gpt-oss" in model_lower:
        return 120000
    elif "qwen" in model_lower:
        return 120000
    elif "kimi" in model_lower or "moonshot" in model_lower:
        return 120000
    elif "groq/compound" in model_lower:
        return 120000
    elif "gemini" in model_lower:
        return None  # Gemini uses different tokenization, return None to indicate special handling
    elif "allam" in model_lower:
        return 4096
    
    # Default fallback for unknown models
    return None


def truncate_text_to_token_limit(text: str, max_tokens: int, model_name: str = None) -> str:
    """
    Truncate text to fit within a token limit, preserving as much content as possible.
    
    Args:
        text: The text to truncate
        max_tokens: Maximum number of tokens allowed
        model_name: Optional model name for tokenization
    
    Returns:
        Truncated text that fits within the token limit
    """
    if max_tokens <= 0:
        return ""
    
    # Get encoding
    encoding_name = "cl100k_base"
    if model_name:
        model_lower = model_name.lower()
        if "llama" in model_lower or "gpt" in model_lower or "groq" in model_lower:
            encoding_name = "cl100k_base"
        elif "qwen" in model_lower:
            encoding_name = "cl100k_base"
        elif "moonshot" in model_lower or "kimi" in model_lower:
            encoding_name = "cl100k_base"
        elif "allam" in model_lower:
            encoding_name = "cl100k_base"
    
    encoding = tiktoken.get_encoding(encoding_name)
    
    # Encode the text
    tokens = encoding.encode(text)
    
    # If it fits, return as-is
    if len(tokens) <= max_tokens:
        return text
    
    # Truncate tokens and decode back to text
    truncated_tokens = tokens[:max_tokens]
    truncated_text = encoding.decode(truncated_tokens)
    
    return truncated_text


def count_tokens(text: str, model_name: str = None) -> int:
    """
    Count tokens accurately using tiktoken.
    
    Args:
        text: The text to count tokens for
        model_name: Optional model name to determine the correct encoding.
                    If None, uses cl100k_base (GPT-3.5/GPT-4 compatible).
    
    Returns:
        Exact token count as an integer
    """
    try:
        # Map model names to their encodings
        # Most Groq models use cl100k_base (OpenAI-compatible)
        encoding_name = "cl100k_base"  # Default for most models
        
        if model_name:
            model_lower = model_name.lower()
            # Llama models typically use cl100k_base
            if "llama" in model_lower or "gpt" in model_lower or "groq" in model_lower:
                encoding_name = "cl100k_base"
            # Qwen models may use different encoding, but cl100k_base is a safe fallback
            elif "qwen" in model_lower:
                encoding_name = "cl100k_base"
            # Moonshot models
            elif "moonshot" in model_lower or "kimi" in model_lower:
                encoding_name = "cl100k_base"
            # Allam models
            elif "allam" in model_lower:
                encoding_name = "cl100k_base"
        
        # Get the encoding
        encoding = tiktoken.get_encoding(encoding_name)
        
        # Count tokens
        token_count = len(encoding.encode(text))
        return token_count
        
    except Exception as e:
        # Fallback: if tiktoken fails, raise an error rather than estimate
        raise ValueError(f"Failed to count tokens accurately: {e}. Please ensure tiktoken is installed and the model encoding is supported.")


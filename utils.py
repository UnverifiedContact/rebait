import re
import os
from urllib.parse import urlparse, parse_qs


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



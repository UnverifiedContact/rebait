#!/usr/bin/env python3
"""
AI Service
Handles AI-related functionality including prompt generation, LLM integration, and API management
"""

import os
from pathlib import Path
from typing import Dict, Any
from utils import read_file_content, write_file_content

class AIService:
    """Handles AI operations including prompt generation, LLM communication, and API management"""
    
    def __init__(self):
        pass
    
    def generate_prompt(self, video_id: str, cache_dir: str, metadata: Dict[str, Any], 
                       flattened_subtitles: str) -> None:

        prompt_content = read_file_content("prompt.txt")
        lines = [prompt_content, ""]
        
        lines.append(f"Title: {metadata.get('title', 'Unknown')}")
        lines.append(f"Channel: {metadata.get('channel_name')}")
        lines.append("Description:")
        lines.append(metadata.get('description', ''))
        lines.append("")        
        lines.append("Subtitles:")
        lines.append(flattened_subtitles)
        
        final_content = '\n'.join(lines)
        
        final_path = os.path.join(cache_dir, video_id, 'final.txt')
        write_file_content(final_path, final_content)
        return final_content
    
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
    
    def __init__(self, prompt_template_path: str = "prompt.txt"):
        self.prompt_template_path = prompt_template_path
    
    def load_prompt_template(self) -> str:
        """Load prompt template from file"""
        try:
            return read_file_content(self.prompt_template_path).strip()
        except FileNotFoundError:
            print("Warning: prompt.txt not found, using default prompt")
            return "Analyze the following YouTube video content and provide insights:"
    
    def generate_prompt(self, metadata: Dict[str, Any], flattened_subtitles: str, 
                       subtitle_type: str, prompt_content: str) -> str:
        """Generate the final prompt with all consolidated content"""
        lines = [prompt_content, ""]
        
        # Add title
        lines.append(f"Title: {metadata.get('title', 'Unknown')}")
        
        # Add channel (using our metadata structure)
        if metadata.get('channel_name'):
            lines.append(f"Channel: {metadata['channel_name']}")
        
        # Add description
        lines.append("Description:")
        lines.append(metadata.get('description', ''))
        lines.append("")
        
        # Add subtitles
        lines.append(f"Subtitles ({subtitle_type}):")
        lines.append(flattened_subtitles)
        
        return '\n'.join(lines)
    
    def write_final_file(self, video_id: str, cache_dir: str, content: str) -> None:
        """Write the final content to final.txt in the cache directory"""
        final_path = os.path.join(cache_dir, video_id, 'final.txt')
        write_file_content(final_path, content)
        print(f"Generated final AI prompt: {final_path}")
    
    def generate_and_save_prompt(self, video_id: str, cache_dir: str, metadata: Dict[str, Any], 
                                flattened_subtitles: str, subtitle_type: str = "dialogue") -> None:
        """Complete workflow: generate prompt and save to file"""
        prompt_content = self.load_prompt_template()
        final_content = self.generate_prompt(metadata, flattened_subtitles, subtitle_type, prompt_content)
        self.write_final_file(video_id, cache_dir, final_content)
    

#!/usr/bin/env python3
"""
Qualify Module
Analyzes YouTube video titles to identify clickbait, inaccurate, or misleading titles.
"""

import os
import json
import requests
from typing import Dict, List
from utils import read_file_content, write_file_content
from ai_service import query_llm


def qualify() -> None:
    """
    Analyze unqualified YouTube videos to identify clickbait titles.
    
    Performs the following actions:
    1. Calls maintenance/prepare endpoint
    2. Fetches unqualified items from API
    3. Extracts youtube_id and title for each video
    4. Sends prompt to LLM with video list
    5. Parses LLM response for clickbait youtube_ids
    6. Updates items via set-is-clickbait endpoint
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("Step 1: Calling maintenance/prepare endpoint...")
    prepare_url = "http://localhost:5001/api/maintenance/prepare"
    response = requests.get(prepare_url, timeout=30)
    response.raise_for_status()
    print("Step 1: Complete")
    
    print("Step 2: Fetching unqualified items from API...")
    unqualified_url = "http://localhost:5001/api/items/unqualified"
    response = requests.get(unqualified_url, timeout=30)
    response.raise_for_status()
    data = response.json()
    items = data.get('data', [])
    print(f"Step 2: Complete - received {len(items)} items")
    
    print("Step 3: Extracting youtube_id and title for each video...")
    videos_list = []
    for item in items:
        if item.get('youtube_id') and item.get('title'):
            videos_list.append({'youtube_id': item['youtube_id'], 'title': item['title']})
    print(f"Step 3: Complete - extracted {len(videos_list)} videos")
    
    if not videos_list:
        print("No videos to process, exiting")
        return
    
    print("Step 4: Building prompt with video list...")
    videos_json = json.dumps(videos_list, indent=2, ensure_ascii=False)
    
    prompt_path = os.path.join(script_dir, "qualify_prompt.txt")
    prompt_content = read_file_content(prompt_path)
    full_prompt = f"{prompt_content}\n\n{videos_json}"
    
    final_qualify_path = os.path.join(script_dir, "final_qualify.txt")
    write_file_content(final_qualify_path, full_prompt)
    print("Step 4: Complete - prompt saved to final_qualify.txt")
    
    print("Step 5: Sending prompt to LLM...")
    llm_response = query_llm(full_prompt)
    print("Step 5: Complete - received LLM response")
    
    llm_response_path = os.path.join(script_dir, "qualify_llm_response.txt")
    write_file_content(llm_response_path, llm_response)
    print(f"Step 5a: LLM response saved to qualify_llm_response.txt")
    
    print("Step 6: Parsing LLM response for clickbait IDs...")
    clickbait_list = json.loads(llm_response)
    if not isinstance(clickbait_list, list):
        raise ValueError(f"LLM response is not a JSON array: {llm_response}")
    print(f"Step 6: Complete - found {len(clickbait_list)} clickbait IDs")
    
    print("Step 7: Building list of non-clickbait IDs...")
    all_youtube_ids = {video['youtube_id'] for video in videos_list}
    clickbait_youtube_ids = set(clickbait_list)
    not_clickbait_list = list(all_youtube_ids - clickbait_youtube_ids)
    
    print(f"Step 7: Complete - found {len(not_clickbait_list)} non-clickbait IDs")
    
    print("Step 8: Updating clickbait status via API...")
    set_clickbait_url = "http://localhost:5001/api/items/set-is-clickbait"
    
    if clickbait_list:
        payload = {
            'youtube_ids': clickbait_list,
            'is_clickbait': True
        }
        response = requests.post(set_clickbait_url, json=payload, timeout=30)
        response.raise_for_status()
        print(f"Step 8a: Complete - marked {len(clickbait_list)} videos as clickbait")
    
    if not_clickbait_list:
        payload = {
            'youtube_ids': not_clickbait_list,
            'is_clickbait': False
        }
        response = requests.post(set_clickbait_url, json=payload, timeout=30)
        response.raise_for_status()
        print(f"Step 8b: Complete - marked {len(not_clickbait_list)} videos as not clickbait")
    
    print("All steps complete")



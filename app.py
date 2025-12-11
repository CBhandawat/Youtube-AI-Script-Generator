import os
import google.generativeai as genai
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import GenericProxyConfig
import requests
import random
import time
from youtube_transcript_api.proxies import WebshareProxyConfig
from dotenv import load_dotenv

load_dotenv()

PROXY_USERNAME = os.getenv('PROXY_USERNAME')
PROXY_PASSWORD = os.getenv('PROXY_PASSWORD')

if "YOUR_" in PROXY_USERNAME or "YOUR_" in PROXY_PASSWORD:
    print("ERROR: Replace with your actual Webshare username and password!")

# Initialize with Webshare rotating residential proxies
proxy_config = WebshareProxyConfig(
    proxy_username=PROXY_USERNAME,
    proxy_password=PROXY_PASSWORD
)

ytt_api = YouTubeTranscriptApi(proxy_config=proxy_config)  # All fetches auto-use rotating proxies!

# Configure Gemini
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
model = genai.GenerativeModel('models/gemini-2.5-flash-lite')

# Set up YouTube API client
youtube = build('youtube', 'v3', developerKey=os.getenv('YOUTUBE_API_KEY'))

def search_youtube_videos(topic: str, max_results=5) -> list:
    request = youtube.search().list(
        q=topic,
        part='snippet',
        maxResults=max_results,
        type='video',
        order='relevance'
    )
    response = request.execute()
    return [item['id']['videoId'] for item in response['items']]

def get_transcript(video_id: str) -> str | None:
    try:
        fetched = ytt_api.fetch(video_id, languages=['en'])
        if fetched:
            raw = fetched.to_raw_data()
            transcript = ' '.join([entry['text'] for entry in raw])
            print(f"Success for {video_id} ({len(transcript)} chars)")
            return transcript
    except Exception as e:
        if "NoTranscriptFound" in str(e) or "TranscriptsDisabled" in str(e):
            print(f"No English captions for {video_id}")
        else:
            print(f"Error (likely blocked/rotated): {str(e)[:100]} - Auto-rotating next time")
    return None

def generate_script(transcripts: list, topic: str) -> str:
    prompt = f"""
    You are an expert YouTube scriptwriter. Topic: '{topic}'.

    Key transcripts (truncated):

    {'\n\n'.join([f"Source {i+1}:\n{t[:3500]}..." if len(t) > 3500 else f"Source {i+1}:\n{t}" for i, t in enumerate(transcripts)])}

    Write an original, engaging 5-10 min script (800-1500 words).
    Structure: Hook/intro, main insights (synthesize), conclusion + CTA.
    Conversational, retention-optimized.
    """
    response = model.generate_content(prompt)
    return response.text

def main():
    topic = input("Enter the topic: ").strip()
    if not topic:
        return
    
    print(f"Searching for: {topic}")
    video_ids = search_youtube_videos(topic)
    print(f"Video IDs: {video_ids}\n")
    
    transcripts = []
    successful = 0
    
    for i, vid in enumerate(video_ids, 1):
        print(f"[{i}/5] Trying {vid}...")
        transcript = get_transcript(vid)
        if transcript:
            transcripts.append(transcript)
            successful += 1
        time.sleep(3)  # Gentle on proxies
    
    if successful == 0:
        print("\nNo luck. Upgrade to Residential proxies for reliable rotation!")
        return
    
    print(f"\n{successful}/5 fetched. Generating script...")
    script = generate_script(transcripts, topic)
    
    print("\n" + "="*60)
    print("GENERATED SCRIPT")
    print("="*60)
    print(script)
    
    filename = f"script_{topic.replace(' ', '_')[:30]}.txt"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"TOPIC: {topic}\n\n{script}")
    print(f"\nSaved to {filename}")

if __name__ == "__main__":
    main()
"""Synthetic posts with several phrasings per idea, for clustering tests."""
from datetime import datetime, timedelta, timezone
from demand_radar.models import Signal
n = datetime.now(timezone.utc)
T = [
 # habit tracking, several phrasings
 "Is there an app for habit tracking with friends?", "Show HN: habit tracker with streaks and reminders",
 "I'd pay for a habit tracker that syncs to my watch", "Minimal habit tracker for iOS, no subscription",
 "Looking for a daily streak app to build habits", "Daily streak app that shames you publicly",
 "Show HN: daily streak app for language practice", "habit tracking app for ADHD brains",
 "Open source habit tracking in the terminal",
 # calorie / macro
 "Is there an app that counts calories from a photo?", "AI calorie counter from food photos",
 "calorie counter without ads please", "I'd pay for a macro tracker that understands home cooking",
 "Show HN: macro tracker with barcode scanning", "Barcode scanning macro tracker for lifters",
 "food photo calorie estimate accuracy test", "GLP-1 users: food photo logging for protein",
 # screen time
 "Is there an app blocker that actually works?", "Wish there was a doomscrolling blocker with friction",
 "Show HN: doomscrolling blocker that makes you breathe first", "app blocker for focus sessions on Android",
 "phone addiction app blocker for teenagers", "screen time limits app for adults",
 "screen time limits that can't be bypassed",
 # meeting notes
 "Show HN: local AI meeting notes, no cloud", "meeting notes app that joins zoom automatically",
 "AI meeting notes for doctors", "Alternative to Otter for meeting transcription", "meeting transcription on device with whisper",
 "meeting transcription for Teams calls",
 # niche with no taxonomy: plant care
 "Is there an app to remind me to water plants?", "Show HN: plant watering reminder using soil sensor",
 "plant watering reminder with photos", "houseplant identification and plant watering schedule",
 # noise
 "world cup final results", "rust compiler release notes", "new iphone battery test", "world cup schedule leaks",
]
S = [Signal("reddit" if i % 3 else "hackernews", t, f"https://x/{i}", n - timedelta(days=i % 28), "", 50 + 10 * (i % 7), i % 11) for i, t in enumerate(T)]

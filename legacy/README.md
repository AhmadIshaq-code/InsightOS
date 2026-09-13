# Legacy & Archived Utilities

This directory contains standalone and prototype utilities from the original InsightAgent repository that are **not** part of the active core InsightOS MVP architecture:

1. `github_fetcher.py`: Scraped issues from GitHub repositories via the GitHub REST API. Archived because InsightOS is a universal data analytics platform, not an IT issue tracker.
2. `fetch_live_data.py`: Redundant standalone script for fetching public CSV and Google Sheets URLs.
3. `live_handler.py`: Background URL poller and Google Sheets converter for tickets.csv. Archived to eliminate background unmonitored polling loops and file overwriting.
4. `infer.py`: Standalone Groq test script with hardcoded test prompt.

These files are preserved here for reference. None of these files are imported by the active InsightOS backend or frontend.

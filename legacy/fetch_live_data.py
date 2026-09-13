import os
import requests
import pandas as pd
from urllib.parse import urlparse

SUPPORTED_SOURCES = [
    "Google Sheets (via export link, e.g., /export?format=csv)",
    "Raw GitHub Links (raw.githubusercontent.com)",
    "Direct CSV Links (.csv)",
    "Direct JSON Links (.json)"
]

def format_google_sheets_url(url: str) -> str:
    """
    Converts a standard Google Sheets sharing link into a CSV export link.
    e.g., https://docs.google.com/spreadsheets/d/123/edit -> https://docs.google.com/spreadsheets/d/123/export?format=csv
    """
    if "docs.google.com/spreadsheets/d/" in url:
        # Extract the ID and reconstruct
        import re
        match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
        if match:
            sheet_id = match.group(1)
            return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    return url

def is_supported_url(url: str) -> bool:
    """
    Validates if the provided URL matches one of our supported formats.
    """
    parsed = urlparse(url)
    
    # Check for empty URL
    if not parsed.scheme or not parsed.netloc:
        return False
        
    # Check for Google Sheets
    if "docs.google.com/spreadsheets" in url:
        return True
        
    # Check for raw GitHub content
    if "raw.githubusercontent.com" in url:
        return True
        
    # Check file extensions in path
    if parsed.path.lower().endswith('.csv') or parsed.path.lower().endswith('.json'):
        return True
        
    # If no explicit extension, but it's a valid URL, we can attempt to fetch it anyway,
    # but we'll return True here to allow the attempt.
    return True

def fetch_and_save_live_data(url: str, output_path: str = "live_data.csv") -> dict:
    """
    Fetches data from a live URL and saves it locally as a CSV.
    Supports CSV and JSON responses.
    """
    if not is_supported_url(url):
        return {
            "success": False,
            "message": "Unsupported URL format. Please use Google Sheets CSV export, raw GitHub URLs, or direct CSV/JSON links."
        }
        
    url = format_google_sheets_url(url)
        
    try:
        print(f"Fetching live data from: {url}")
        # Add a common User-Agent to avoid simple blocks
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Determine content type
        content_type = response.headers.get('Content-Type', '').lower()
        
        # Parse based on URL or Content-Type
        if url.endswith('.json') or 'application/json' in content_type:
            # Parse JSON
            data = response.json()
            # If JSON is a list of dicts, pandas can handle it directly
            df = pd.json_normalize(data)
        else:
            # Default to CSV parser (works for Google Sheets export and raw CSVs)
            from io import StringIO
            csv_data = StringIO(response.text)
            df = pd.read_csv(csv_data)
            
        # Save to local CSV for the Data Agent to query
        df.to_csv(output_path, index=False)
        print(f"Successfully saved {len(df)} rows to {output_path}")
        
        return {
            "success": True,
            "message": f"Successfully fetched and saved {len(df)} rows.",
            "rows": len(df),
            "columns": list(df.columns)
        }
        
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "message": f"Network error while fetching data: {str(e)}"
        }
    except ValueError as e:
        return {
            "success": False,
            "message": f"Error parsing data (is it valid CSV/JSON?): {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Unexpected error: {str(e)}"
        }

if __name__ == "__main__":
    # Example Usage
    print("Supported Links:")
    for link in SUPPORTED_SOURCES:
        print(f" - {link}")
        
    # Test with a sample public CSV
    sample_url = "https://docs.google.com/spreadsheets/d/1z464k-wT7Mcca8_uwmt4HsOJyol7TuKDe-kjnxhZgA0/edit?usp=sharing"
    print("\nTesting fetch...")
    result = fetch_and_save_live_data(sample_url, "test_live_data.csv")
    print(result)

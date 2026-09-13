import os
import requests
import pandas as pd
import re
from urllib.parse import urlparse

def format_google_sheets_url(url: str) -> str:
    """
    Converts a standard Google Sheets sharing link into a CSV export link.
    """
    if "docs.google.com/spreadsheets/d/" in url:
        match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
        if match:
            sheet_id = match.group(1)
            return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    return url

def convert_live_data_to_csv(url: str, output_path: str = "tickets.csv") -> dict:
    """
    Fetches data from a live URL (Google Sheets, direct CSV/JSON, etc.) 
    and saves it locally as a CSV file.
    """
    original_url = url
    url = format_google_sheets_url(url)
    
    try:
        print(f"Fetching live data from: {url}")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        content_type = response.headers.get('Content-Type', '').lower()
        
        if url.endswith('.json') or 'application/json' in content_type:
            data = response.json()
            df = pd.json_normalize(data)
        else:
            from io import StringIO
            csv_data = StringIO(response.text)
            df = pd.read_csv(csv_data)
            
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
            "message": f"Error parsing data: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Unexpected error: {str(e)}"
        }

import sys
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert live data link to CSV.")
    parser.add_argument("url", nargs="?", default="https://docs.google.com/spreadsheets/d/1z464k-wT7Mcca8_uwmt4HsOJyol7TuKDe-kjnxhZgA0/edit?usp=sharing", help="The live URL to fetch data from.")
    parser.add_argument("--output", "-o", default="tickets.csv", help="The output CSV file path.")
    
    args = parser.parse_args()
    
    print(f"Testing live_handler with URL: {args.url}")
    result = convert_live_data_to_csv(args.url, args.output)
    print(result)

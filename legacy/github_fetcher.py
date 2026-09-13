import requests
import pandas as pd
import re

def parse_github_url(url: str):
    """Extracts owner and repo name from a GitHub URL."""
    # Handle formats like https://github.com/langchain-ai/langchain
    match = re.search(r'github\.com/([^/]+)/([^/]+)', url)
    if match:
        owner = match.group(1)
        repo = match.group(2).replace(".git", "")
        return owner, repo
    return None, None

def fetch_github_issues(url: str, output_csv: str = "tickets.csv"):
    """
    Fetches the latest 100 issues from a GitHub repository 
    and saves them as a CSV for the Data Agent.
    """
    owner, repo = parse_github_url(url)
    if not owner or not repo:
        return {"success": False, "error": "Invalid GitHub URL"}

    print(f"Fetching live issues from {owner}/{repo}...")
    api_url = f"https://api.github.com/repos/{owner}/{repo}/issues?state=all&per_page=100"
    
    # We use a User-Agent to avoid getting blocked by GitHub API
    headers = {"User-Agent": "Enterprise-Insight-Agent"}
    
    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        issues_data = response.json()
        
        parsed_issues = []
        for issue in issues_data:
            # Skip pull requests (GitHub API returns PRs in the issues endpoint)
            if "pull_request" in issue:
                continue
                
            labels = [label["name"] for label in issue.get("labels", [])]
            assignees = [user["login"] for user in issue.get("assignees", [])]
            
            parsed_issues.append({
                "Ticket ID": issue["number"],
                "Created Date": issue["created_at"],
                "Title": issue["title"],
                "Description": (issue["body"] or "")[:200].replace('\n', ' ') + "...", # Truncated for speed
                "Status": issue["state"],
                "Assignee": ", ".join(assignees) if assignees else "Unassigned",
                "Labels": ", ".join(labels) if labels else "None"
            })
            
        if not parsed_issues:
            return {"success": False, "error": "No issues found in this repository."}
            
        # Convert to Pandas DataFrame and save to CSV
        df = pd.DataFrame(parsed_issues)
        df.to_csv(output_csv, index=False)
        print(f"Successfully saved {len(parsed_issues)} issues to {output_csv}.")
        
        return {"success": True, "count": len(parsed_issues), "message": f"Fetched {len(parsed_issues)} issues."}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    # Test the fetcher with Langchain's actual repo!
    test_url = "https://github.com/langchain-ai/langchain"
    result = fetch_github_issues(test_url)
    print(result)

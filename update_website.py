import os
import re
import json
import requests 
from github import Github
from time import sleep

# --- Configuration ---
SOURCE_HTML_FILE = 'index.html'
CITIES_FILE = 'replacement_word.txt'
# This MUST EXACTLY MATCH the placeholder text in your source index.html
SEARCH_TERM = 'Oklahoma City' 
REPO_PREFIX = 'The-'
REPO_SUFFIX = '-Software-Guild'
# ---------------------

def read_file(filename):
    """Reads the content of a file."""
    if not os.path.exists(filename):
        raise FileNotFoundError(f"Required file not found: {filename}")
    with open(filename, 'r', encoding='utf-8') as f:
        return f.read()

def main():
    """Main execution function."""
    
    # 1. Get Environment Variables (City and Token)
    city_input = os.environ.get('CITY_INPUT')
    token = os.environ.get('GH_TOKEN')

    if not city_input or not token:
        raise EnvironmentError("Missing CITY_INPUT or GH_TOKEN environment variables. Cannot proceed.")

    # 2. Read Cities and Validate Input
    cities_data = read_file(CITIES_FILE)
        
    all_cities = [c.strip() for c in cities_data.splitlines() if c.strip()]
    
    if city_input not in all_cities:
        raise ValueError(f"City '{city_input}' not found in {CITIES_FILE}.")

    # 3. Define New Repository Details
    city = city_input
    repo_name_base = f"{city.replace(' ', '')}"
    new_repo_name = f"{REPO_PREFIX}{repo_name_base}{REPO_SUFFIX}"
    print(f"Targeting new repository: {new_repo_name}")
    
    # 4. Read and Modify HTML Content
    base_html_content = read_file(SOURCE_HTML_FILE)
    
    # *** THIS IS THE CRITICAL REPLACEMENT LINE ***
    # It attempts to replace all occurrences of SEARCH_TERM with the input city.
    new_content = base_html_content.replace(SEARCH_TERM, city)
    
    # Replace the title tag
    new_site_title = f"{REPO_PREFIX.strip('-')} {city} {REPO_SUFFIX.strip('-')}"
    new_content = re.sub(r'<title>.*?</title>', f'<title>{new_site_title}</title>', new_content, flags=re.IGNORECASE)
    
    # 5. Connect to GitHub and Create/Get Repo
    try:
        # Suppress the DeprecationWarning
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            g = Github(token)
        user = g.get_user()
        
        # Get or Create Repository
        repo = None
        repo_exists = False
        try:
            repo = user.get_repo(new_repo_name)
            repo_exists = True
            print(f"Repository {new_repo_name} already exists. Proceeding to update.")
        except Exception:
            print(f"Repository {new_repo_name} does not exist. Creating new repository.")
            repo = user.create_repo(
                name=new_repo_name,
                description=f"GitHub Pages site for {city} Software Guild",
                private=False,
                auto_init=True
            )
            sleep(5) 

        # 6. Commit 'index.html' and '.nojekyll'
        
        # Add/Update the .nojekyll file
        try:
            contents = repo.get_contents(".nojekyll", ref="main")
            repo.update_file(path=".nojekyll", message="Update .nojekyll file", content="", sha=contents.sha, branch="main")
        except Exception:
            repo.create_file(path=".nojekyll", message="Add .nojekyll to enable direct HTML serving", content="", branch="main")
        print("Added/Updated .nojekyll file.")

        # Commit the generated index.html
        try:
            contents = repo.get_contents("index.html", ref="main")
            repo.update_file(path="index.html", message=f"Update site content for {city}", content=new_content, sha=contents.sha, branch="main")
        except Exception:
            repo.create_file(path="index.html", message=f"Initial site deployment for {city}", content=new_content, branch="main")
        print("Committed updated index.html to the new repository.")

        # 7. Enable GitHub Pages using direct requests API call
        
        pages_api_url = f"https://api.github.com/repos/{user.login}/{new_repo_name}/pages"
        
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'Authorization': f'token {token}',
        }
        data = {
            'source': {
                'branch': 'main',
                'path': '/'
            }
        }
        
        # Use POST to create Pages config (if it doesn't exist)
        r = requests.post(pages_api_url, headers=headers, json=data)
        
        if r.status_code == 201:
            print("Successfully configured GitHub Pages (New Site).")
        elif r.status_code == 409:
            # Conflict (409) means pages config already exists, so we update it
            r = requests.put(pages_api_url, headers=headers, json=data)
            if r.status_code == 204:
                print("Successfully updated GitHub Pages configuration.")
        
        # 8. Fetch and Display Final URL
        pages_info_url = f"https://api.github.com/repos/{user.login}/{new_repo_name}/pages"
        r = requests.get(pages_info_url, headers=headers)
        
        try:
            pages_url = json.loads(r.text).get('html_url', 'URL not yet active or failed to retrieve.')
        except:
            pages_url = 'URL failed to retrieve, check repo settings manually.'


        print(f"\n--- SUCCESS ---")
        print(f"New repository created/updated: {repo.html_url}")
        print(f"Live site URL: {pages_url}")
        print(f"---------------")

    except Exception as e:
        print(f"A critical error occurred: {e}")
        raise

if __name__ == "__main__":
    main()

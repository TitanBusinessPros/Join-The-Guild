import os
import re
from github import Github

# --- Configuration ---
SOURCE_HTML_FILE = 'index.html'
SEARCH_TERM = 'Oklahoma City'
REPO_PREFIX = 'The-'
REPO_SUFFIX = '-Software-Guild'
# ---------------------

def read_file(filename):
    """Reads the content of a file."""
    if not os.path.exists(filename):
        print(f"Error: Required file not found: {filename}")
        return None
    with open(filename, 'r', encoding='utf-8') as f:
        return f.read()

def main():
    """Main execution function."""
    
    # 1. Get Environment Variables
    city = os.environ.get('CITY_INPUT')
    token = os.environ.get('GH_TOKEN')

    if not city or not token:
        print("Error: Missing CITY_INPUT or GH_TOKEN environment variables.")
        return

    # 2. Define New Repository Details
    repo_name_base = f"{city.replace(' ', '')}"
    new_repo_name = f"{REPO_PREFIX}{repo_name_base}{REPO_SUFFIX}"
    print(f"Targeting new repository: {new_repo_name}")
    
    # 3. Read and Modify HTML Content
    base_html_content = read_file(SOURCE_HTML_FILE)
    if base_html_content is None:
        return

    # Replace the body content (city name)
    new_content = base_html_content.replace(SEARCH_TERM, city)
    
    # Replace the title tag
    new_site_title = f"{REPO_PREFIX.strip('-')} {city} {REPO_SUFFIX.strip('-')}"
    new_content = re.sub(r'<title>.*?</title>', f'<title>{new_site_title}</title>', new_content, flags=re.IGNORECASE)
    
    # 4. Connect to GitHub and Create Repo
    try:
        g = Github(token)
        user = g.get_user()
        
        # Check if repo exists
        try:
            repo = user.get_repo(new_repo_name)
            print(f"Repository {new_repo_name} already exists. Proceeding to update.")
        except Exception:
            # Create the repository if it doesn't exist
            repo = user.create_repo(
                name=new_repo_name,
                description=f"GitHub Pages site for {city} Software Guild",
                private=False,
                has_issues=False,
                has_projects=False,
                has_wiki=False
            )
            print(f"Successfully created new repository: {new_repo_name}")

        # 5. Commit and Push 'index.html'
        
        # Add the .nojekyll file to ensure GitHub Pages serves HTML directly
        repo.create_file(
            path=".nojekyll",
            message="Add .nojekyll to enable direct HTML serving",
            content="",
            branch="main"
        )
        print("Added .nojekyll file.")

        # Commit the generated index.html
        try:
            contents = repo.get_contents("index.html", ref="main")
            # Update existing file
            repo.update_file(
                path="index.html",
                message=f"Update site content for {city}",
                content=new_content,
                sha=contents.sha,
                branch="main"
            )
        except Exception:
            # Create new file
            repo.create_file(
                path="index.html",
                message=f"Initial site deployment for {city}",
                content=new_content,
                branch="main"
            )
        print("Committed updated index.html to the new repository.")

        # 6. Enable GitHub Pages Deployment
        # NOTE: This setting is often asynchronous and may take a moment to appear on GitHub UI
        repo.enable_pages(
            source={"branch": "main", "path": "/"},
            cname=None
        )
        
        print(f"\n--- SUCCESS ---")
        print(f"New repository created/updated: {repo.html_url}")
        print(f"Live site URL (may take a moment to activate): {repo.html_url.replace('.com', '.io')}")
        print(f"---------------")


    except Exception as e:
        print(f"A critical error occurred: {e}")
        raise

if __name__ == "__main__":
    main()

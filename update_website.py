import os
import re
from github import Github, InputRequired
from time import sleep

# --- Configuration ---
SOURCE_HTML_FILE = 'index.html'
CITIES_FILE = 'replacement_word.txt'
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
    
    # 1. Get Environment Variables (City and Token)
    city_input = os.environ.get('CITY_INPUT')
    token = os.environ.get('GH_TOKEN')

    if not city_input or not token:
        print("Error: Missing CITY_INPUT or GH_TOKEN environment variables. Cannot proceed.")
        return

    # 2. Read Cities and Validate Input
    cities_data = read_file(CITIES_FILE)
    if cities_data is None:
        return
        
    all_cities = [c.strip() for c in cities_data.splitlines() if c.strip()]
    
    # Check if the input city is in the text file
    if city_input not in all_cities:
        print(f"Error: City '{city_input}' not found in {CITIES_FILE}. Valid cities are: {', '.join(all_cities)}")
        return

    # 3. Define New Repository Details
    city = city_input # Use the validated city name
    repo_name_base = f"{city.replace(' ', '')}"
    new_repo_name = f"{REPO_PREFIX}{repo_name_base}{REPO_SUFFIX}"
    print(f"Targeting new repository: {new_repo_name}")
    
    # 4. Read and Modify HTML Content
    base_html_content = read_file(SOURCE_HTML_FILE)
    if base_html_content is None:
        return

    # Replace the body content (city name)
    new_content = base_html_content.replace(SEARCH_TERM, city)
    
    # Replace the title tag
    new_site_title = f"{REPO_PREFIX.strip('-')} {city} {REPO_SUFFIX.strip('-')}"
    new_content = re.sub(r'<title>.*?</title>', f'<title>{new_site_title}</title>', new_content, flags=re.IGNORECASE)
    
    # 5. Connect to GitHub and Create Repo
    try:
        g = Github(token)
        user = g.get_user()
        
        # Check if repo exists
        try:
            repo = user.get_repo(new_repo_name)
            print(f"Repository {new_repo_name} already exists. Proceeding to update.")
            
            # If repo exists, ensure main branch is updated/created
            try:
                repo.get_branch("main")
            except Exception:
                # If main branch doesn't exist (e.g., empty repo), create it
                repo.create_git_ref(ref='refs/heads/main', sha=repo.get_commits()[0].sha)
                print("Created 'main' branch.")

        except Exception as e:
            # Create the repository if it doesn't exist
            print(f"Repository {new_repo_name} does not exist. Creating new repository.")
            repo = user.create_repo(
                name=new_repo_name,
                description=f"GitHub Pages site for {city} Software Guild",
                private=False,
                has_issues=False,
                has_projects=False,
                has_wiki=False,
                auto_init=True # Initialize with a README to create the main branch
            )
            print(f"Successfully created new repository: {new_repo_name}")
            
            # GitHub Pages setup requires a short wait after creation
            sleep(5) 
            
        # 6. Commit 'index.html' and '.nojekyll' to the new repo's main branch

        # Add the .nojekyll file (Crucial for Pages deployment)
        try:
            # Check if .nojekyll exists to update it, otherwise create it
            contents = repo.get_contents(".nojekyll", ref="main")
            repo.update_file(
                path=".nojekyll",
                message="Update .nojekyll file (no content change)",
                content="",
                sha=contents.sha,
                branch="main"
            )
        except Exception:
            # Create new file
            repo.create_file(
                path=".nojekyll",
                message="Add .nojekyll to enable direct HTML serving",
                content="",
                branch="main"
            )
        print("Added/Updated .nojekyll file.")

        # Commit the generated index.html (Create or Update)
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

        # 7. Enable GitHub Pages Deployment from the 'main' branch
        repo.enable_pages(
            source={"branch": "main", "path": "/"},
            cname=None
        )
        
        pages_info = repo.get_pages()
        print(f"\n--- SUCCESS ---")
        print(f"New repository created/updated: {repo.html_url}")
        print(f"Live site URL (may take a minute to activate): {pages_info.html_url}")
        print(f"---------------")


    except InputRequired as e:
        print(f"API Error: A required input for GitHub API was missing. Check token scopes.")
        raise
    except Exception as e:
        print(f"A critical error occurred: {e}")
        raise

if __name__ == "__main__":
    main()

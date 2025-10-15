import os
import re
from github import Github
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

    # Replace the body content (city name)
    new_content = base_html_content.replace(SEARCH_TERM, city)
    
    # Replace the title tag
    new_site_title = f"{REPO_PREFIX.strip('-')} {city} {REPO_SUFFIX.strip('-')}"
    new_content = re.sub(r'<title>.*?</title>', f'<title>{new_site_title}</title>', new_content, flags=re.IGNORECASE)
    
    # 5. Connect to GitHub and Create/Get Repo
    try:
        # Suppress the DeprecationWarning for cleaner output
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            g = Github(token)
        user = g.get_user()
        
        # Check if repo exists
        try:
            repo = user.get_repo(new_repo_name)
            print(f"Repository {new_repo_name} already exists. Proceeding to update.")
            
            # Ensure main branch exists before committing
            try:
                repo.get_branch("main")
            except Exception:
                initial_sha = repo.get_commits()[0].sha
                repo.create_git_ref(ref='refs/heads/main', sha=initial_sha)
                print("Created 'main' branch reference.")
            
        except Exception:
            # Create the repository if it doesn't exist
            print(f"Repository {new_repo_name} does not exist. Creating new repository.")
            
            repo = user.create_repo(
                name=new_repo_name,
                description=f"GitHub Pages site for {city} Software Guild",
                private=False,
                has_issues=False,
                has_projects=False,
                has_wiki=False,
                auto_init=True
            )
            print(f"Successfully created new repository: {new_repo_name}")
            sleep(5) 
            
        # 6. Commit 'index.html' and '.nojekyll' to the new repo's main branch

        # Add/Update the .nojekyll file
        try:
            contents = repo.get_contents(".nojekyll", ref="main")
            repo.update_file(
                path=".nojekyll",
                message="Update .nojekyll file",
                content="",
                sha=contents.sha,
                branch="main"
            )
        except Exception:
            repo.create_file(
                path=".nojekyll",
                message="Add .nojekyll to enable direct HTML serving",
                content="",
                branch="main"
            )
        print("Added/Updated .nojekyll file.")

        # Commit the generated index.html
        try:
            contents = repo.get_contents("index.html", ref="main")
            repo.update_file(
                path="index.html",
                message=f"Update site content for {city}",
                content=new_content,
                sha=contents.sha,
                branch="main"
            )
        except Exception:
            repo.create_file(
                path="index.html",
                message=f"Initial site deployment for {city}",
                content=new_content,
                branch="main"
            )
        print("Committed updated index.html to the new repository.")

        # 7. FINAL FIX: Enable GitHub Pages Deployment using the modern Service method
        
        # The new API endpoint structure requires getting the Pages service object.
        # This replaces both 'enable_pages' and 'get_pages().update()'.
        
        # Ensure the Pages object exists (create it if not)
        try:
            pages = repo.get_pages()
        except:
            # If get_pages fails on a new repo, we manually trigger the creation/deployment
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
            
            # This is a highly stable method for creating/updating the Pages config
            r = g.get_url(f'{repo.url}/pages', headers=headers, verb='POST', data=data)
            
            if r.status_code == 201 or r.status_code == 204:
                print("Successfully configured GitHub Pages via API.")
            else:
                 print(f"Warning: Pages API response was unexpected (Status: {r.status_code}).")
        
        # Now we can safely call get_pages to fetch the final URL
        pages_info = repo.get_pages() 

        print(f"\n--- SUCCESS ---")
        print(f"New repository created/updated: {repo.html_url}")
        print(f"Live site URL (may take a minute to activate): {pages_info.html_url}")
        print(f"---------------")

    except Exception as e:
        print(f"An error occurred during GitHub API operations: {e}")
        raise
if __name__ == "__main__":
    main()

#-------------------------------------------------------------------------------
# Instagram Follower Scraper
# Author: merhametsize
#
# This script is designed to scrape a target user's followers list using
# headers extracted from a raw HTTP request file (request.txt). It handles
# pagination automatically and uses random delays to mimic human behavior
# and mitigate rate limiting.
#-------------------------------------------------------------------------------
import requests
import time
import random
import json
import sys

from datetime import datetime
from typing import Any

# --- CONFIGURATION FILE LOADING -----------------------------------------------

def load_request_data(filepath: str) -> tuple[dict[str, str], str, str]:
    '''
    Parses the raw HTTP request from the file, extracting base URL, target_id, and headers.
    '''

    # We look for this pattern to ensure we are hitting the correct API endpoint
    BASE_API_PATH_PATTERN = '/api/v1/friendships/'
    headers: dict[str, str] = {}

    # Headers to skip because requests handles them or they are problematic/redundant
    HEADERS_TO_SKIP = ['host', 'content-length', 'connection', 'pragma', 'cache-control', 'accept-encoding', 'priority']

    try:
        with open(filepath, 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f'🛑 Error: Configuration file not found at \'{filepath}\'. Please create request.txt.')
        sys.exit(1)

    if not lines:
        print(f'🛑 Error: Configuration file \'{filepath}\' is empty.')
        sys.exit(1)

    # 1. Parse the request line (e.g., GET /path/to/resource HTTP/1.1)
    request_line_parts = lines[0].strip().split(' ')
    if len(request_line_parts) < 2 or request_line_parts[0] != 'GET':
        print(f'🛑 Error: First line of \'{filepath}\' must start with \'GET /...\'')
        sys.exit(1)

    # Extract the path, ignoring any query parameters (like ?count=25&max_id=...)
    full_path: str = request_line_parts[1].split('?')[0]

    # Ensure the path contains the expected API structure
    if BASE_API_PATH_PATTERN not in full_path:
        print(f'🛑 Error: Request path in \'{filepath}\' does not look like Instagram follower API.')
        print(f'Expected pattern: {BASE_API_PATH_PATTERN}')
        print(f'Found path: {full_path}')
        sys.exit(1)

    try:
        # full_path is like /api/v1/friendships/123456789/followers/
        path_after_base = full_path.split(BASE_API_PATH_PATTERN, 1)[1]
        target_id = path_after_base.split('/')[0]
        if not target_id.isdigit():
             raise ValueError('Target ID found is not purely numeric.')
    except Exception:
        print(f'🛑 Error: Could not extract target ID from path in \'{filepath}\'.')
        print(f'Path found: {full_path}')
        sys.exit(1)

    # 2. Parse headers from the rest of the lines
    for line in lines[1:]:
        line = line.strip()
        if not line:
            break # Stop at the first blank line (end of headers)

        if ':' in line:
            name, value = line.split(':', 1)
            name = name.strip()
            value = value.strip()

            # Skip problematic or automatically handled headers
            if name.lower() in HEADERS_TO_SKIP:
                continue

            headers[name] = value

    # 3. Validation and final construction
    required_headers = ['Cookie', 'X-IG-WWW-Claim']
    for req_h in required_headers:
        if req_h not in headers:
            print(f'🛑 Error: Required header \'{req_h}\' not found in \'{filepath}\'.')
            print('Please ensure your request.txt file contains a complete, fresh request.')
            sys.exit(1)

    # The base URL for the API is always https://www.instagram.com followed by the path found
    # MODIFIED: Return target_id
    return headers, f'https://www.instagram.com{full_path}', target_id

# --- API FETCH FUNCTION -------------------------------------------------------

def fetch_followers(base_url: str, target_id: str, max_id: str | None, headers: dict[str, str]) -> dict[str, Any] | None:
    '''
    Fetches a single page of follower data from the Instagram API.
    '''

    # Construct the full URL using the base URL and the max_id parameter
    url = f'{base_url}?count=25&max_id={max_id or ''}&search_surface=follow_list_page'

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        try:
            return response.json()
        except json.JSONDecodeError:
            print('\nError: Response content is not JSON (Likely a security challenge or expired cookie).')
            print(f'--- Raw Content Snippet ---\n{response.text[:500]}\n---------------------------\n')
            return None

    except requests.exceptions.HTTPError as http_err:
        print(f'HTTP error occurred (Rate Limit/Access Denied): {http_err}')
        return None
    except requests.exceptions.RequestException as req_err:
        print(f'Request error occurred: {req_err}')
        return None

# --- CORE SCRAPING CYCLE FUNCTION ---------------------------------------------

def scrape_single_cycle(base_url: str, target_id: str, headers: dict[str, str]) -> set[str]:
    '''
    Runs one full, complete pagination cycle and returns all unique usernames
    found in this single attempt as a set.
    '''

    cycle_followers: set[str] = set()
    next_max_id: str | None = None
    pages_fetched: int = 0

    print('\nStarting a new scrape cycle...')

    while True:
        data = fetch_followers(base_url, target_id, next_max_id, headers)

        if data is None:
            print('🛑 Cycle terminated early due to API error.')
            break

        if data.get('status') == 'ok':
            users: list[dict[str, Any]] = data.get('users', [])
            usernames: list[str] = [user['username'] for user in users]

            cycle_followers.update(usernames)
            pages_fetched += 1

            # Print usernames found in this request
            output_sample = ', '.join(usernames)
            print(f'[*] Page {pages_fetched} - Total unique usernames in cycle: {len(cycle_followers)}; sample: {output_sample[:45]}...')


            if not data.get('has_more'):
                print(f'✅ Cycle complete. Fetched {pages_fetched} pages.')
                break

            next_max_id = data.get('next_max_id')
            sleep_time = random.randint(4, 12)
            time.sleep(sleep_time)
        else:
            print('Error fetching data (API status not \'ok\'):', data)
            break

    return cycle_followers

# --- MASTER CONTROL FUNCTION --------------------------------------------------

def main():
    if len(sys.argv) != 3:
        print('Usage: python3 follow_scraper.py <request_file_path> <target_count>')
        print('\nExample: python3 follow_scraper.py request.txt 894')
        sys.exit(1)

    # Generate timestamp for output
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_filename: str = f'followers_{timestamp}.txt'

    request_filepath: str = sys.argv[1]

    try:
        target_count: int = int(sys.argv[2])
        if target_count <= 0:
            raise ValueError
    except ValueError:
        print('Error: Target count must be a positive whole number.')
        sys.exit(1)

    # 1. Load headers, base URL, and the extracted TARGET_ID from the request file
    HEADERS, BASE_URL, TARGET_ID = load_request_data(request_filepath)

    # MASTER SET: Stores all unique usernames found across ALL cycles
    master_unique_followers: set[str] = set()
    cycle_number: int = 0

    print(f'\n--- Master Scraper Initialized ---')
    print(f'Target User ID (Extracted): {TARGET_ID}') # ADDED: Display the extracted ID
    print(f'Base API URL: {BASE_URL}')
    print(f'Target Follower Count: {target_count}')
    print('----------------------------------')

    while len(master_unique_followers) < target_count:
        cycle_number += 1

        # 2. Scrape a full cycle (using the extracted TARGET_ID)
        current_cycle_set: set[str] = scrape_single_cycle(BASE_URL, TARGET_ID, HEADERS)

        if not current_cycle_set:
            print('\nSkipping master update (no users found in this cycle). Check headers/IP.')
            if cycle_number > 5 and len(master_unique_followers) == 0:
                print('🛑 Five cycles failed without finding any users. Aborting.')
                sys.exit(1)

        # 3. Update the master set
        old_size: int = len(master_unique_followers)
        master_unique_followers.update(current_cycle_set)
        new_users_found: int = len(master_unique_followers) - old_size

        # 4. Report Status
        print(f'\n[CYCLE {cycle_number}] Status:')
        print(f'  - Unique users found in this cycle: {len(current_cycle_set)}')
        print(f'  - New unique users added to master list: {new_users_found}')
        print(f'  - TOTAL UNIQUE FOUND: {len(master_unique_followers)} / {target_count}')

        # 5. Check for completion
        if len(master_unique_followers) >= target_count:
            print('\n🎉 TARGET REACHED! Combined count is equal to or greater than the target. Stopping.')
            break

        # 6. Temporary dump
        final_list: list[str] = sorted(list(master_unique_followers))
        try:
            with open(output_filename, 'w') as f:
                f.write('\n'.join(final_list))
        except Exception as e:
            print(f'Error saving the temporary output file {output_filename}: {e}')

        # 7. Delay between cycles (Crucial for avoiding long-term rate limits)
        cycle_sleep_time = random.randint(30, 60)
        print(f'😴 Waiting {cycle_sleep_time} seconds before starting Cycle {cycle_number + 1}...')
        time.sleep(cycle_sleep_time)


    # --- FINAL OUTPUT ---
    final_list: list[str] = sorted(list(master_unique_followers))

    try:
        with open(output_filename, 'w') as f:
            f.write('\n'.join(final_list))

        print('-' * 50)
        print(f'✅ FINAL OUTPUT SUCCESSFUL')
        print(f'Total Unique Usernames Saved: {len(final_list)}')
        print(f'Output saved to: {output_filename}')
        print('-' * 50)

    except Exception as e:
        print(f'Error saving the final output file {output_filename}: {e}')


if __name__ == '__main__':
    main()

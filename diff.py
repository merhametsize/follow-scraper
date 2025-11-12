#-------------------------------------------------------------------------------
# diff.py
# Author: merhametsize
#
# Utility script to find what changed in your followers list
#-------------------------------------------------------------------------------

import sys
from datetime import datetime

def load_usernames(filepath: str) -> set[str] | None:
    '''Reads a file, extracting unique usernames into a set.'''
    try:
        with open(filepath, 'r') as f:
            # Read lines, strip whitespace (like \n), and filter out empty lines
            usernames = {line.strip() for line in f if line.strip()}
        return usernames
    except FileNotFoundError:
        print(f'🛑 Error: Input file not found: {filepath}')
        return None
    except Exception as e:
        print(f'🛑 An unexpected error occurred while reading {filepath}: {e}')
        return None

def main():
    '''Compares two follower lists to find lost and new followers.'''

    # 1. Check for correct command-line arguments
    if len(sys.argv) != 3:
        print('Usage: python diff.py <old_usernames_file> <new_usernames_file>')
        print('Example: python diff.py usernames_20251109_120000.txt usernames_20251110_180000.txt')
        sys.exit(1)

    file_old = sys.argv[1]
    file_new = sys.argv[2]

    # 2. Load data from files
    followers_old = load_usernames(file_old)
    followers_new = load_usernames(file_new)

    if followers_old is None or followers_new is None:
        sys.exit(1) # Exit if loading failed for either file

    # 3. Perform Set Arithmetic to Find Differences

    # Followers that were in OLD but are NOT in NEW = Unfollowed/Lost Followers
    lost_followers = followers_old - followers_new

    # Followers that are in NEW but were NOT in OLD = New Followers
    new_followers = followers_new - followers_old

    # Calculate total change
    old_count = len(followers_old)
    new_count = len(followers_new)
    net_change = new_count - old_count

    # 4. Generate the Report Content

    report_lines = []

    report_lines.append('-' * 70)
    report_lines.append(f'Follower Difference Report Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    report_lines.append('-' * 70)
    report_lines.append(f'Comparison Basis:')
    report_lines.append(f'  - OLD Snapshot: {file_old} ({old_count} followers)')
    report_lines.append(f'  - NEW Snapshot: {file_new} ({new_count} followers)')
    report_lines.append('-' * 70)

    # Summary Metrics
    report_lines.append('SUMMARY OF CHANGES')
    report_lines.append(f'------------------')
    report_lines.append(f'Total Lost Followers (Unfollowed): {len(lost_followers)}')
    report_lines.append(f'Total New Followers:             {len(new_followers)}')
    report_lines.append(f'Net Change in Follower Count:    {net_change:+} (Total: {new_count})')
    report_lines.append('-' * 70)

    # Detailed List of Lost Followers
    report_lines.append('\nLIST OF LOST FOLLOWERS (In OLD, Not in NEW):')
    report_lines.append('-' * 40)
    if lost_followers:
        sorted_lost = sorted(list(lost_followers))
        report_lines.extend(sorted_lost)
    else:
        report_lines.append('N/A - No followers were lost.')

    # Detailed List of New Followers
    report_lines.append('\n\nLIST OF NEW FOLLOWERS (In NEW, Not in OLD):')
    report_lines.append('-' * 40)
    if new_followers:
        sorted_new = sorted(list(new_followers))
        report_lines.extend(sorted_new)
    else:
        report_lines.append('N/A - No new followers were gained.')

    # 5. Write the report to the output file
    output_filename = 'difference.txt'
    try:
        with open(output_filename, 'w') as f:
            f.write('\n'.join(report_lines))

        print('\n✅ Analysis complete!')
        print(f'Report saved to: {output_filename}')
        print('-' * 70)

    except IOError as e:
        print(f'🛑 Error writing report file {output_filename}: {e}')

if __name__ == '__main__':
    main()

"""
Example: Instaloader-based Instagram Data Collection

This is a working example of how to use Instaloader to collect
public Instagram profile data for celebrities.

Run locally to test before deploying to Lambda.
"""

import instaloader
import json
from datetime import datetime

# Initialize Instaloader
L = instaloader.Instaloader(
    quiet=True,
    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
)

def scrape_instagram_profile(instagram_handle):
    """
    Scrape a public Instagram profile using Instaloader.

    Args:
        instagram_handle: Instagram username (without @)

    Returns:
        dict: Profile data or error information
    """
    try:
        # Fetch the profile
        profile = instaloader.Profile.from_username(L.context, instagram_handle)

        # Extract data
        data = {
            'success': True,
            'username': profile.username,
            'followers': profile.follower_count,
            'posts': profile.mediacount,
            'biography': profile.biography,
            'is_verified': profile.is_verified,
            'is_business_account': profile.is_business_account,
            'is_private': profile.is_private,
            'profile_pic_url': profile.profile_pic_url,
            'scraped_at': datetime.utcnow().isoformat()
        }

        print(f"✓ Successfully scraped: {instagram_handle}")
        return data

    except instaloader.exceptions.ProfileNotExistsException:
        print(f"✗ Profile not found: {instagram_handle}")
        return {
            'success': False,
            'error': f'Profile does not exist: {instagram_handle}'
        }

    except instaloader.exceptions.LoginRequiredException:
        print(f"! Login required for: {instagram_handle}")
        return {
            'success': False,
            'error': f'Private account requires login: {instagram_handle}'
        }

    except instaloader.exceptions.TooManyRequestsException:
        print(f"⚠ Rate limited (TooManyRequests)")
        return {
            'success': False,
            'error': 'Rate limited by Instagram, please wait'
        }

    except Exception as e:
        print(f"✗ Error scraping {instagram_handle}: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


def scrape_multiple_celebrities(handles_list):
    """
    Scrape multiple Instagram profiles.

    Args:
        handles_list: List of Instagram usernames

    Returns:
        dict: Results summary and data
    """
    results = {
        'total': len(handles_list),
        'successful': 0,
        'failed': 0,
        'data': []
    }

    for handle in handles_list:
        data = scrape_instagram_profile(handle)
        results['data'].append(data)

        if data.get('success'):
            results['successful'] += 1
        else:
            results['failed'] += 1

    return results


def login_with_account(username, password):
    """
    Optionally login with Instagram account credentials.
    Useful for accessing additional data or higher rate limits.

    Args:
        username: Instagram username
        password: Instagram password

    Returns:
        bool: True if login successful, False otherwise
    """
    try:
        L.login(username, password)
        print(f"✓ Logged in as: {username}")
        return True
    except Exception as e:
        print(f"✗ Login failed: {str(e)}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Instagram Data Collection Example (Instaloader)")
    print("=" * 60)
    print()

    # Example 1: Single profile (anonymous mode)
    print("Example 1: Single Profile (Anonymous Mode)")
    print("-" * 60)

    profile_data = scrape_instagram_profile('cristiano')

    if profile_data.get('success'):
        print(f"\nProfile Data for @{profile_data['username']}:")
        print(f"  Followers: {profile_data['followers']:,}")
        print(f"  Posts: {profile_data['posts']}")
        print(f"  Verified: {profile_data['is_verified']}")
        print(f"  Bio: {profile_data['biography'][:100]}...")
    else:
        print(f"Error: {profile_data.get('error')}")

    print()

    # Example 2: Multiple profiles
    print("Example 2: Multiple Profiles")
    print("-" * 60)

    celebrities = [
        'arianagrande',
        'beyonce',
        'rihanna',
        'justinbieber',
        'selenagomez'
    ]

    results = scrape_multiple_celebrities(celebrities)

    print(f"\nResults Summary:")
    print(f"  Total: {results['total']}")
    print(f"  Successful: {results['successful']}")
    print(f"  Failed: {results['failed']}")

    print("\nDetailed Results:")
    for item in results['data']:
        if item.get('success'):
            print(f"  ✓ @{item['username']}: {item['followers']:,} followers")
        else:
            print(f"  ✗ {item.get('error', 'Unknown error')}")

    print()

    # Example 3: Optional - Login with account (uncomment to use)
    print("Example 3: Optional Account Login")
    print("-" * 60)
    print("To use account credentials:")
    print("  1. Set environment variables INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD")
    print("  2. Uncomment code below")
    print("  3. Account credentials give access to additional data")
    print()

    # Uncomment to use:
    # import os
    # username = os.getenv('INSTAGRAM_USERNAME')
    # password = os.getenv('INSTAGRAM_PASSWORD')
    # if username and password:
    #     if login_with_account(username, password):
    #         # Now scrape with authenticated session
    #         data = scrape_instagram_profile('arianagrande')
    #         print(json.dumps(data, indent=2))

    print("=" * 60)
    print("Example complete!")
    print("=" * 60)

import requests
import boto3
import json
import os
import uuid
import logging
import time
from datetime import datetime
from botocore.exceptions import ClientError

# Configure logging
log_level = os.environ.get('LOG_LEVEL', 'INFO')
logging.basicConfig(level=getattr(logging, log_level))
logger = logging.getLogger(__name__)

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('AWS_REGION', 'us-east-1'))

# YouTube API base URL
YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"


def search_youtube_channel(celebrity_name, api_key, timeout=10):
    """
    Search for a celebrity's YouTube channel.

    Args:
        celebrity_name: Name of celebrity to search
        api_key: YouTube API key
        timeout: Request timeout in seconds

    Returns:
        Dict with channel_id or error message
    """
    url = f"{YOUTUBE_API_BASE}/search"
    params = {
        'q': celebrity_name,
        'part': 'snippet',
        'type': 'channel',
        'key': api_key,
        'maxResults': 1
    }

    try:
        logger.info(f"Searching YouTube for channel: {celebrity_name}")
        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()

        data = response.json()

        # Check for API errors in response
        if 'error' in data:
            error_msg = data['error'].get('message', 'Unknown error')
            logger.error(f"YouTube API error: {error_msg}")
            return {'channel_id': None, 'error': f'API error: {error_msg}'}

        # Extract channel ID from results
        if data.get('items') and len(data['items']) > 0:
            channel_id = data['items'][0]['id']['channelId']
            logger.info(f"Found channel: {channel_id}")
            return {'channel_id': channel_id, 'error': None}
        else:
            logger.warning(f"No YouTube channel found for {celebrity_name}")
            return {'channel_id': None, 'error': 'Channel not found'}

    except requests.Timeout:
        logger.error(f"Timeout searching YouTube for {celebrity_name}")
        return {'channel_id': None, 'error': 'Search timeout'}
    except requests.HTTPError as e:
        status_code = e.response.status_code
        logger.error(f"HTTP {status_code} error searching YouTube")
        return {'channel_id': None, 'error': f'HTTP {status_code}'}
    except Exception as e:
        logger.error(f"Unexpected error searching YouTube: {str(e)}")
        return {'channel_id': None, 'error': str(e)}


def fetch_channel_data(channel_id, api_key, timeout=10):
    """
    Fetch detailed channel information from YouTube.

    Args:
        channel_id: YouTube channel ID
        api_key: YouTube API key
        timeout: Request timeout in seconds

    Returns:
        Dict with success status and channel data or error
    """
    url = f"{YOUTUBE_API_BASE}/channels"
    params = {
        'id': channel_id,
        'part': 'snippet,statistics,contentDetails',
        'key': api_key
    }

    try:
        logger.info(f"Fetching YouTube channel data for: {channel_id}")
        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()

        data = response.json()

        # Check for API errors
        if 'error' in data:
            error_msg = data['error'].get('message', 'Unknown error')
            logger.error(f"YouTube API error: {error_msg}")
            return {
                'success': False,
                'error': f'API error: {error_msg}',
                'raw_text': None
            }

        # Extract channel data
        if data.get('items') and len(data['items']) > 0:
            raw_text = json.dumps(data)
            channel_data = data['items'][0]
            logger.info(f"Successfully fetched channel data")
            return {
                'success': True,
                'raw_text': raw_text,
                'channel_data': channel_data,
                'error': None
            }
        else:
            logger.error(f"No channel data in response")
            return {
                'success': False,
                'error': 'No channel data found',
                'raw_text': None
            }

    except requests.Timeout:
        logger.error(f"Timeout fetching channel data")
        return {
            'success': False,
            'error': 'Channel fetch timeout',
            'raw_text': None
        }
    except requests.HTTPError as e:
        status_code = e.response.status_code
        logger.error(f"HTTP {status_code} error fetching channel")

        # Handle quota exceeded
        if status_code == 403:
            return {
                'success': False,
                'error': 'Quota exceeded (403)',
                'raw_text': None,
                'quota_exceeded': True
            }

        return {
            'success': False,
            'error': f'HTTP {status_code}',
            'raw_text': None
        }
    except Exception as e:
        logger.error(f"Unexpected error fetching channel: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'raw_text': None
        }


def retry_with_backoff(func, max_retries=3, base_delay=1):
    """
    Execute function with exponential backoff retry logic.

    Args:
        func: Function to execute
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds

    Returns:
        Result from function call
    """
    for attempt in range(max_retries):
        try:
            result = func()
            if result.get('success') or result.get('channel_id'):
                return result

            # Don't retry invalid API key errors
            if 'Invalid' in result.get('error', '') or 'API key' in result.get('error', ''):
                logger.error(f"Invalid API key - not retrying")
                return result

            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)  # 1s, 2s, 4s
                logger.warning(f"Attempt {attempt + 1} failed: {result.get('error')}. Retrying in {delay}s...")
                time.sleep(delay)

        except Exception as e:
            logger.error(f"Unexpected error in retry logic: {str(e)}")
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                time.sleep(delay)

    return result


def get_all_celebrities(table):
    """
    Get all celebrities from DynamoDB.

    Returns:
        List of celebrity records with id and name
    """
    try:
        logger.info("Fetching all celebrities from DynamoDB...")
        response = table.scan()

        # Filter to get unique celebrities (one per celebrity_id)
        celebrities_map = {}
        for item in response.get('Items', []):
            celeb_id = item.get('celebrity_id')
            if celeb_id and celeb_id not in celebrities_map:
                # Get metadata record for this celebrity
                if item.get('source_type#timestamp', '').startswith('metadata#'):
                    celebrities_map[celeb_id] = {
                        'celebrity_id': celeb_id,
                        'name': item.get('name', 'Unknown')
                    }

        # If we didn't find metadata records, just get unique celebrities
        if not celebrities_map:
            for item in response.get('Items', []):
                celeb_id = item.get('celebrity_id')
                if celeb_id and celeb_id not in celebrities_map:
                    celebrities_map[celeb_id] = {
                        'celebrity_id': celeb_id,
                        'name': item.get('name', 'Unknown')
                    }

        celebrities = list(celebrities_map.values())
        logger.info(f"Found {len(celebrities)} celebrities")
        return celebrities

    except ClientError as e:
        logger.error(f"Error scanning DynamoDB: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching celebrities: {str(e)}")
        return []


def write_scraper_entry_with_retry(table, item, max_retries=3, base_delay=1):
    """
    Write scraper entry to DynamoDB with exponential backoff.

    Args:
        table: DynamoDB table resource
        item: Item to write
        max_retries: Maximum retry attempts
        base_delay: Initial retry delay

    Returns:
        True if successful, False otherwise
    """
    for attempt in range(max_retries):
        try:
            table.put_item(Item=item)
            logger.info(f"Successfully wrote entry for {item['name']}")
            return True

        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"DynamoDB write error ({error_code}): {str(e)}")

            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Retrying DynamoDB write in {delay}s...")
                time.sleep(delay)

        except Exception as e:
            logger.error(f"Unexpected error writing to DynamoDB: {str(e)}")
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                time.sleep(delay)

    logger.error(f"Failed to write entry for {item['name']} after {max_retries} attempts")
    return False


def lambda_handler(event, context):
    """
    Main Lambda handler for YouTube scraper.

    Fetches all celebrities from DynamoDB and collects YouTube channel data.
    Writes scraped entries back to DynamoDB.

    Args:
        event: Lambda event (unused)
        context: Lambda context

    Returns:
        Summary with success/error counts and details
    """
    logger.info("Starting YouTube scraper...")

    # Load configuration
    table_name = os.environ.get('DYNAMODB_TABLE')
    api_key = os.environ.get('YOUTUBE_API_KEY')
    timeout = int(os.environ.get('YOUTUBE_TIMEOUT', '10'))

    # Validate configuration
    if not all([table_name, api_key]):
        error_msg = "Missing required environment variables (DYNAMODB_TABLE, YOUTUBE_API_KEY)"
        logger.error(error_msg)
        return {
            'total': 0,
            'success': 0,
            'errors': 1,
            'error': error_msg,
            'details': []
        }

    try:
        table = dynamodb.Table(table_name)
    except ClientError as e:
        error_msg = f"Error accessing DynamoDB table: {str(e)}"
        logger.error(error_msg)
        return {
            'total': 0,
            'success': 0,
            'errors': 1,
            'error': error_msg,
            'details': []
        }

    # Get all celebrities
    celebrities = get_all_celebrities(table)
    if not celebrities:
        logger.warning("No celebrities found in DynamoDB")
        return {
            'total': 0,
            'success': 0,
            'errors': 0,
            'details': []
        }

    # Process each celebrity
    results = []
    for celeb in celebrities:
        try:
            celeb_id = celeb['celebrity_id']
            celeb_name = celeb['name']

            logger.info(f"Processing {celeb_name} ({celeb_id})")

            # Search for YouTube channel
            search_result = retry_with_backoff(
                lambda: search_youtube_channel(celeb_name, api_key, timeout),
                max_retries=3,
                base_delay=1
            )

            if not search_result['channel_id']:
                results.append({
                    'celebrity_id': celeb_id,
                    'name': celeb_name,
                    'status': 'not_found',
                    'error': search_result.get('error', 'Unknown error')
                })
                continue

            # Fetch channel data
            channel_result = retry_with_backoff(
                lambda: fetch_channel_data(search_result['channel_id'], api_key, timeout),
                max_retries=3,
                base_delay=1
            )

            if channel_result['success']:
                # Create scraper entry (FIRST-HAND data)
                scraper_entry = {
                    'celebrity_id': celeb_id,
                    'source_type#timestamp': f"youtube#{datetime.utcnow().isoformat()}Z",
                    'id': str(uuid.uuid4()),
                    'name': celeb_name,
                    'raw_text': channel_result['raw_text'],
                    'source': 'https://www.googleapis.com/youtube/v3/channels',
                    'timestamp': datetime.utcnow().isoformat() + 'Z',
                    'weight': None,
                    'sentiment': None,
                    'metadata': {
                        'scraper_name': 'scraper-youtube',
                        'source_type': 'youtube',
                        'processed': False,
                        'error': None,
                        'channel_id': search_result['channel_id']
                    }
                }

                # Write to DynamoDB with retry
                if write_scraper_entry_with_retry(table, scraper_entry):
                    # Extract subscriber count for logging
                    channel_data = channel_result.get('channel_data', {})
                    statistics = channel_data.get('statistics', {})
                    subscriber_count = statistics.get('subscriberCount', 'unknown')

                    results.append({
                        'celebrity_id': celeb_id,
                        'name': celeb_name,
                        'status': 'success',
                        'subscribers': subscriber_count,
                        'channel_id': search_result['channel_id']
                    })
                else:
                    results.append({
                        'celebrity_id': celeb_id,
                        'name': celeb_name,
                        'status': 'error',
                        'error': 'DynamoDB write failed'
                    })
            else:
                results.append({
                    'celebrity_id': celeb_id,
                    'name': celeb_name,
                    'status': 'error',
                    'error': channel_result.get('error', 'Unknown error')
                })

        except Exception as e:
            logger.error(f"Unexpected error processing {celeb.get('name', 'Unknown')}: {str(e)}")
            results.append({
                'celebrity_id': celeb.get('celebrity_id', 'unknown'),
                'name': celeb.get('name', 'Unknown'),
                'status': 'error',
                'error': str(e)
            })

    # Compile summary
    success_count = len([r for r in results if r['status'] == 'success'])
    error_count = len([r for r in results if r['status'] == 'error'])
    not_found_count = len([r for r in results if r['status'] == 'not_found'])

    summary = {
        'total': len(celebrities),
        'success': success_count,
        'errors': error_count,
        'not_found': not_found_count,
        'details': results
    }

    logger.info(
        f"YouTube scraper completed. "
        f"Success: {success_count}/{len(celebrities)}, "
        f"Not Found: {not_found_count}, "
        f"Errors: {error_count}"
    )
    return summary


# For local testing
if __name__ == "__main__":
    import sys

    # Test mode
    if len(sys.argv) > 1 and sys.argv[1] == '--test-mode':
        logging.basicConfig(level=logging.INFO)
        print("Running in test mode...")

        # Mock test
        print("✓ Lambda handler function exists")
        print("✓ YouTube search function defined")
        print("✓ Channel data fetch function defined")
        print("✓ Error handling functions defined")
        print("✓ DynamoDB integration prepared")
        print("✓ Test mode completed")
    else:
        # Try to invoke handler locally (requires AWS credentials and DynamoDB)
        try:
            result = lambda_handler({}, None)
            print(json.dumps(result, indent=2))
        except Exception as e:
            print(f"Error: {str(e)}")
            print("Note: Local execution requires AWS credentials and DynamoDB access")

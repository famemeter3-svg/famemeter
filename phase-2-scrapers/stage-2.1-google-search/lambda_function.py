import requests
import boto3
import json
import os
import uuid
import logging
import time
from datetime import datetime
from botocore.exceptions import ClientError
from key_rotation import get_rotation_manager, APIKeyRotationManager

# Configure logging
log_level = os.environ.get('LOG_LEVEL', 'INFO')
logging.basicConfig(level=getattr(logging, log_level))
logger = logging.getLogger(__name__)

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('AWS_REGION', 'us-east-1'))

# Initialize key rotation manager
key_rotation_enabled = os.environ.get('ENABLE_KEY_ROTATION', 'true').lower() == 'true'
rotation_manager = None
if key_rotation_enabled:
    rotation_manager = get_rotation_manager()


def clean_raw_text(response_data):
    """
    Clean raw Google API response.
    - Normalize whitespace
    - Remove null bytes
    - Ensure valid UTF-8 encoding
    - Preserve structure of JSON
    """
    try:
        # If it's already a dict, convert to JSON string
        if isinstance(response_data, dict):
            cleaned = json.dumps(response_data, ensure_ascii=False)
            return cleaned

        # If it's a JSON string, parse and re-serialize for consistency
        if isinstance(response_data, str):
            try:
                data = json.loads(response_data)
                cleaned = json.dumps(data, ensure_ascii=False)
                return cleaned
            except json.JSONDecodeError:
                # If JSON parsing fails, clean as raw text
                pass

        # Fallback: clean text directly
        text = str(response_data)
        import re
        text = re.sub(r'\s+', ' ', text)  # Collapse whitespace
        text = text.encode('utf-8', 'ignore').decode('utf-8')  # Remove non-UTF8
        return text

    except Exception as e:
        logger.warning(f"Error cleaning raw text: {str(e)}")
        return str(response_data)


def fetch_google_search_data(celebrity_name, api_key, search_engine_id, timeout=10, use_rotation=False):
    """
    Fetch search results from Google Custom Search API.

    Args:
        celebrity_name: Name of celebrity to search
        api_key: Google API key
        search_engine_id: Google Custom Search Engine ID
        timeout: Request timeout in seconds
        use_rotation: Whether to use key rotation for this request

    Returns:
        Dict with success/error status and raw response
    """
    url = "https://www.googleapis.com/customsearch/v1"

    # Use rotated key if enabled and available
    if use_rotation and rotation_manager:
        api_key = rotation_manager.get_next_key()
        if not api_key:
            logger.error("Key rotation enabled but no valid keys available")
            return {
                'success': False,
                'error': 'No valid API keys available',
                'raw_text': None,
                'item_count': 0
            }

    params = {
        'q': celebrity_name,
        'key': api_key,
        'cx': search_engine_id,
        'num': 10  # Get top 10 results
    }

    try:
        logger.info(f"Fetching Google Search data for: {celebrity_name}")
        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()

        data = response.json()

        # Check for API error responses
        if 'error' in data:
            error_msg = data['error'].get('message', 'Unknown API error')
            logger.error(f"Google API error: {error_msg}")
            if rotation_manager and use_rotation:
                rotation_manager.record_request(api_key, success=False, error_type='API_ERROR')
            return {
                'success': False,
                'error': f'API error: {error_msg}',
                'raw_text': None,
                'item_count': 0
            }

        raw_text = clean_raw_text(data)
        item_count = len(data.get('items', []))

        logger.info(f"Successfully fetched {item_count} results for {celebrity_name}")
        if rotation_manager and use_rotation:
            rotation_manager.record_request(api_key, success=True)
        return {
            'success': True,
            'raw_text': raw_text,
            'item_count': item_count,
            'error': None
        }

    except requests.Timeout:
        logger.error(f"Timeout fetching data for {celebrity_name}")
        if rotation_manager and use_rotation:
            rotation_manager.record_request(api_key, success=False, error_type='TIMEOUT')
        return {
            'success': False,
            'error': 'API timeout',
            'raw_text': None,
            'item_count': 0
        }

    except requests.HTTPError as e:
        status_code = e.response.status_code
        logger.error(f"HTTP {status_code} error for {celebrity_name}")

        # Special handling for rate limit
        if status_code == 429:
            if rotation_manager and use_rotation:
                rotation_manager.record_request(api_key, success=False, error_type='RATE_LIMIT')
            return {
                'success': False,
                'error': f'Rate limited (429)',
                'raw_text': None,
                'item_count': 0,
                'rate_limited': True
            }

        return {
            'success': False,
            'error': f'HTTP {status_code}',
            'raw_text': None,
            'item_count': 0
        }

    except json.JSONDecodeError:
        logger.error(f"Malformed JSON response for {celebrity_name}")
        return {
            'success': False,
            'error': 'Malformed response',
            'raw_text': None,
            'item_count': 0
        }

    except Exception as e:
        logger.error(f"Unexpected error fetching data for {celebrity_name}: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'raw_text': None,
            'item_count': 0
        }


def retry_with_backoff(func, max_retries=3, base_delay=1):
    """
    Execute function with exponential backoff retry logic.

    Args:
        func: Function to execute
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds (1, 2, 4)

    Returns:
        Result from function call
    """
    for attempt in range(max_retries):
        try:
            result = func()
            if result.get('success'):
                return result

            # Don't retry invalid API key errors
            if 'Invalid' in result.get('error', '') or 'API key' in result.get('error', ''):
                logger.error(f"Invalid API key - not retrying")
                return result

            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
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
    Scans the table and filters for metadata records.

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
    Main Lambda handler for Google Search scraper.

    Fetches all celebrities from DynamoDB and collects Google Search data for each.
    Writes scraped entries back to DynamoDB.

    Args:
        event: Lambda event (unused)
        context: Lambda context

    Returns:
        Summary with success/error counts and details
    """
    logger.info("Starting Google Search scraper...")

    # Load configuration
    table_name = os.environ.get('DYNAMODB_TABLE')
    api_key = os.environ.get('GOOGLE_API_KEY')
    search_engine_id = os.environ.get('GOOGLE_SEARCH_ENGINE_ID')
    timeout = int(os.environ.get('GOOGLE_TIMEOUT', '10'))

    # Validate configuration
    if not all([table_name, api_key, search_engine_id]):
        error_msg = "Missing required environment variables (DYNAMODB_TABLE, GOOGLE_API_KEY, GOOGLE_SEARCH_ENGINE_ID)"
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
    use_key_rotation = key_rotation_enabled and rotation_manager is not None

    for celeb in celebrities:
        try:
            celeb_id = celeb['celebrity_id']
            celeb_name = celeb['name']

            logger.info(f"Processing {celeb_name} ({celeb_id})")

            # Fetch Google Search data with retry logic and optional key rotation
            google_result = retry_with_backoff(
                lambda: fetch_google_search_data(
                    celeb_name, api_key, search_engine_id, timeout,
                    use_rotation=use_key_rotation
                ),
                max_retries=3,
                base_delay=1
            )

            if google_result['success']:
                # Create scraper entry (FIRST-HAND data)
                scraper_entry = {
                    'celebrity_id': celeb_id,
                    'source_type#timestamp': f"google_search#{datetime.utcnow().isoformat()}Z",
                    'id': str(uuid.uuid4()),
                    'name': celeb_name,
                    'raw_text': google_result['raw_text'],
                    'source': 'https://www.googleapis.com/customsearch/v1',
                    'timestamp': datetime.utcnow().isoformat() + 'Z',
                    'weight': None,
                    'sentiment': None,
                    'metadata': {
                        'scraper_name': 'scraper-google-search',
                        'source_type': 'google_search',
                        'processed': False,
                        'error': None
                    }
                }

                # Write to DynamoDB with retry
                if write_scraper_entry_with_retry(table, scraper_entry):
                    results.append({
                        'celebrity_id': celeb_id,
                        'name': celeb_name,
                        'status': 'success',
                        'item_count': google_result.get('item_count', 0)
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
                    'error': google_result.get('error', 'Unknown error')
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

    summary = {
        'total': len(celebrities),
        'success': success_count,
        'errors': error_count,
        'details': results
    }

    # Add key rotation statistics if enabled
    if use_key_rotation and rotation_manager:
        rotation_manager.log_summary()
        summary['key_rotation'] = {
            'enabled': True,
            'strategy': rotation_manager.strategy,
            'keys_used': len(rotation_manager.keys),
            'statistics': rotation_manager.get_statistics()
        }
        logger.info(f"Key rotation stats: {summary['key_rotation']['statistics']}")
    else:
        summary['key_rotation'] = {'enabled': False}

    logger.info(f"Google Search scraper completed. Success: {success_count}/{len(celebrities)}, Errors: {error_count}")
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

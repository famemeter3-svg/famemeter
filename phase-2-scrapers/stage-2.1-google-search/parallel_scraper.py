#!/usr/bin/env python3
"""
Parallel Google Search Scraper with 20 Workers

Runs locally connected to your AWS DynamoDB, fills the database with
first Google Search entries for all 100 celebrities.

Usage:
    python3 parallel_scraper.py --workers 20 --celebrities 100
"""

import json
import os
import sys
import uuid
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple
import boto3
from botocore.exceptions import ClientError
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize DynamoDB
dynamodb = boto3.resource(
    'dynamodb',
    region_name=os.environ.get('AWS_REGION', 'us-east-1')
)

# Google Custom Search API
GOOGLE_API_BASE = "https://www.googleapis.com/customsearch/v1"


class ParallelScraper:
    """Parallel Google Search scraper with worker pool."""

    def __init__(self, num_workers: int = 20):
        self.num_workers = num_workers
        self.table_name = os.environ.get('DYNAMODB_TABLE', 'celebrity-database')
        self.api_keys = self._load_api_keys()
        self.search_engine_id = os.environ.get('GOOGLE_SEARCH_ENGINE_ID')
        self.table = dynamodb.Table(self.table_name)

        # Statistics
        self.stats = {
            'total': 0,
            'success': 0,
            'errors': 0,
            'not_found': 0,
            'start_time': None,
            'end_time': None
        }

    def _load_api_keys(self) -> List[str]:
        """Load API keys from environment variables."""
        keys = []
        for i in range(1, 4):
            key = os.environ.get(f'GOOGLE_API_KEY_{i}')
            if key:
                keys.append(key)

        if not keys:
            raise ValueError("No Google API keys found in environment (GOOGLE_API_KEY_1, GOOGLE_API_KEY_2, GOOGLE_API_KEY_3)")

        logger.info(f"Loaded {len(keys)} API keys")
        return keys

    def _get_next_key(self, celebrity_index: int) -> str:
        """Get next API key using round-robin rotation."""
        return self.api_keys[celebrity_index % len(self.api_keys)]

    def _fetch_google_search_data(self, celebrity_name: str, api_key: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Fetch Google Search data for a celebrity.

        Returns: (success, raw_text, error_message)
        """
        url = GOOGLE_API_BASE
        params = {
            'q': celebrity_name,
            'cx': self.search_engine_id,
            'key': api_key,
            'start': 1
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            # Check for API errors
            if 'error' in data:
                error_msg = data['error'].get('message', 'Unknown error')
                logger.warning(f"API error for {celebrity_name}: {error_msg}")
                return False, None, f"API error: {error_msg}"

            # Success
            raw_text = json.dumps(data)
            return True, raw_text, None

        except requests.Timeout:
            error = f"Timeout searching {celebrity_name}"
            logger.error(error)
            return False, None, error
        except requests.HTTPError as e:
            error = f"HTTP {e.response.status_code} error for {celebrity_name}"
            logger.error(error)
            return False, None, error
        except json.JSONDecodeError as e:
            error = f"Malformed JSON response for {celebrity_name}: {str(e)}"
            logger.error(error)
            return False, None, error
        except Exception as e:
            error = f"Unexpected error for {celebrity_name}: {str(e)}"
            logger.error(error)
            return False, None, error

    def _write_to_dynamodb(self, celebrity_id: str, celebrity_name: str, raw_text: str, api_key_num: int) -> bool:
        """Write scraper entry to DynamoDB with retry."""
        try:
            entry = {
                'celebrity_id': celebrity_id,
                'source_type#timestamp': f"google_search#{datetime.utcnow().isoformat()}Z",
                'id': str(uuid.uuid4()),
                'name': celebrity_name,
                'raw_text': raw_text,
                'source': GOOGLE_API_BASE,
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'weight': None,
                'sentiment': None,
                'metadata': {
                    'scraper_name': 'scraper-google-search',
                    'source_type': 'google_search',
                    'processed': False,
                    'error': None,
                    'key_rotation': {
                        'enabled': True,
                        'strategy': 'round_robin',
                        'key_used': f'key_{api_key_num}'
                    }
                }
            }

            # Retry logic
            for attempt in range(3):
                try:
                    self.table.put_item(Item=entry)
                    logger.debug(f"Successfully wrote {celebrity_name} to DynamoDB")
                    return True
                except ClientError as e:
                    error_code = e.response['Error']['Code']
                    if error_code == 'ProvisionedThroughputExceededException':
                        if attempt < 2:
                            import time
                            delay = 2 ** attempt
                            logger.warning(f"Throttled, retrying {celebrity_name} in {delay}s...")
                            time.sleep(delay)
                        else:
                            logger.error(f"Failed to write {celebrity_name} after 3 attempts (throttle)")
                            return False
                    else:
                        logger.error(f"DynamoDB error writing {celebrity_name}: {error_code}")
                        return False

        except Exception as e:
            logger.error(f"Error preparing entry for {celebrity_name}: {str(e)}")
            return False

    def _process_celebrity(self, celebrity_data: Dict, index: int) -> Dict:
        """Process a single celebrity (called by worker)."""
        celebrity_id = celebrity_data['celebrity_id']
        celebrity_name = celebrity_data['name']
        api_key_num = (index % len(self.api_keys)) + 1
        api_key = self._get_next_key(index)

        logger.info(f"[{index+1}] Processing {celebrity_name} (celeb_id: {celebrity_id}) with key_{api_key_num}")

        # Fetch Google Search data
        success, raw_text, error = self._fetch_google_search_data(celebrity_name, api_key)

        if not success:
            self.stats['errors'] += 1
            logger.error(f"✗ {celebrity_name}: {error}")
            return {
                'celebrity_id': celebrity_id,
                'name': celebrity_name,
                'status': 'error',
                'error': error,
                'api_key': f'key_{api_key_num}'
            }

        # Write to DynamoDB
        if self._write_to_dynamodb(celebrity_id, celebrity_name, raw_text, api_key_num):
            self.stats['success'] += 1
            logger.info(f"✓ {celebrity_name}: Successfully written to DynamoDB")
            return {
                'celebrity_id': celebrity_id,
                'name': celebrity_name,
                'status': 'success',
                'api_key': f'key_{api_key_num}'
            }
        else:
            self.stats['errors'] += 1
            logger.error(f"✗ {celebrity_name}: Failed to write to DynamoDB")
            return {
                'celebrity_id': celebrity_id,
                'name': celebrity_name,
                'status': 'error',
                'error': 'DynamoDB write failed',
                'api_key': f'key_{api_key_num}'
            }

    def _get_celebrities_from_dynamodb(self) -> List[Dict]:
        """Get all celebrities from metadata records in DynamoDB."""
        logger.info("Fetching celebrities from DynamoDB...")

        try:
            celebrities = []
            response = self.table.scan(
                FilterExpression='attribute_exists(birth_date)'  # Metadata records have birth_date
            )

            for item in response.get('Items', []):
                if 'source_type#timestamp' in item and item['source_type#timestamp'].startswith('metadata#'):
                    celebrities.append({
                        'celebrity_id': item['celebrity_id'],
                        'name': item['name']
                    })

            logger.info(f"Found {len(celebrities)} celebrities in DynamoDB")
            return celebrities

        except Exception as e:
            logger.error(f"Error fetching celebrities: {str(e)}")
            return []

    def run(self, limit: Optional[int] = None) -> Dict:
        """Run parallel scraper with worker pool.

        Args:
            limit: Maximum number of celebrities to process (None = all)

        Returns:
            Summary statistics
        """
        self.stats['start_time'] = datetime.utcnow()

        # Get celebrities from database
        celebrities = self._get_celebrities_from_dynamodb()

        if not celebrities:
            logger.error("No celebrities found in database")
            return {
                'error': 'No celebrities found',
                'total': 0
            }

        # Apply limit if specified
        if limit:
            celebrities = celebrities[:limit]

        self.stats['total'] = len(celebrities)
        logger.info(f"\nStarting parallel scraper with {self.num_workers} workers")
        logger.info(f"Processing {len(celebrities)} celebrities\n")

        results = []

        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            # Submit all tasks
            future_to_celeb = {
                executor.submit(self._process_celebrity, celeb, idx): (celeb, idx)
                for idx, celeb in enumerate(celebrities)
            }

            # Process completed tasks as they finish
            for future in as_completed(future_to_celeb):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    celeb, idx = future_to_celeb[future]
                    logger.error(f"Worker failed for {celeb['name']}: {str(e)}")
                    self.stats['errors'] += 1
                    results.append({
                        'celebrity_id': celeb['celebrity_id'],
                        'name': celeb['name'],
                        'status': 'error',
                        'error': str(e)
                    })

        self.stats['end_time'] = datetime.utcnow()
        duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()

        # Print summary
        logger.info("\n" + "="*80)
        logger.info("PARALLEL SCRAPER COMPLETE")
        logger.info("="*80)
        logger.info(f"Total: {self.stats['total']}")
        logger.info(f"Success: {self.stats['success']}")
        logger.info(f"Errors: {self.stats['errors']}")
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info(f"Rate: {self.stats['success']/duration:.2f} celebrities/second")
        logger.info("="*80 + "\n")

        return {
            'total': self.stats['total'],
            'success': self.stats['success'],
            'errors': self.stats['errors'],
            'duration_seconds': duration,
            'rate_per_second': self.stats['success'] / duration if duration > 0 else 0,
            'results': results
        }


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Parallel Google Search Scraper')
    parser.add_argument('--workers', type=int, default=20, help='Number of parallel workers (default: 20)')
    parser.add_argument('--celebrities', type=int, default=None, help='Limit number of celebrities to process')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Check environment variables
    required_vars = ['GOOGLE_API_KEY_1', 'GOOGLE_SEARCH_ENGINE_ID', 'AWS_REGION']
    missing = [var for var in required_vars if not os.environ.get(var)]

    if missing:
        logger.error(f"Missing environment variables: {', '.join(missing)}")
        logger.error("\nPlease set up your .env file with:")
        logger.error("  GOOGLE_API_KEY_1=your_key_1")
        logger.error("  GOOGLE_API_KEY_2=your_key_2")
        logger.error("  GOOGLE_API_KEY_3=your_key_3")
        logger.error("  GOOGLE_SEARCH_ENGINE_ID=your_search_engine_id")
        logger.error("  DYNAMODB_TABLE=celebrity-database")
        logger.error("  AWS_REGION=us-east-1")
        sys.exit(1)

    # Run scraper
    scraper = ParallelScraper(num_workers=args.workers)
    result = scraper.run(limit=args.celebrities)

    # Print summary
    print("\n" + json.dumps(result, indent=2, default=str))


if __name__ == '__main__':
    main()

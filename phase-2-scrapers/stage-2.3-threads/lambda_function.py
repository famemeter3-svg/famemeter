"""
Stage 2.3: Threads Scraper - Account-Based Profile Data Collection

Collects Threads profile data (followers, posts, bio) using real account credentials
with proxy rotation to avoid detection. Integrates with Phase 1 DynamoDB database.

Error Handling:
- Rate Limit (429): Exponential backoff + proxy rotation
- Detection (403): Rotate proxy + retry
- Timeout: Retry with backoff
- Connection Error: Rotate proxy + retry
- Parse Error: Log and skip
- Missing Handle: Skip gracefully
- No Accounts/Proxies: Graceful fallback
"""

import os
import json
import re
import uuid
import time
import random
import logging
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
from enum import Enum

import boto3
import requests
from botocore.exceptions import ClientError
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# AWS clients
secrets_client = boto3.client('secretsmanager')
dynamodb = boto3.resource('dynamodb')
cloudwatch = boto3.client('cloudwatch')

# Constants
THREADS_MAX_RETRIES = 3
THREADS_TIMEOUT = int(os.environ.get('INSTAGRAM_TIMEOUT', '20'))
THREAD_BACKOFF_BASE = 5  # seconds
CIRCUIT_BREAKER_THRESHOLD = 5
CIRCUIT_BREAKER_TIMEOUT = 300  # seconds
BATCH_DELAY = 2  # seconds between requests


class ScraperStatus(Enum):
    """Scraper status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"
    NOT_FOUND = "not_found"
    INVALID_HANDLE = "invalid_handle"


class CircuitBreaker:
    """Circuit breaker pattern for rate limiting protection."""

    def __init__(self, failure_threshold: int = CIRCUIT_BREAKER_THRESHOLD,
                 timeout: int = CIRCUIT_BREAKER_TIMEOUT):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time = None
        self.is_open = False

    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.is_open:
            if time.time() - self.last_failure_time > self.timeout:
                self.is_open = False
                self.failures = 0
            else:
                raise Exception("Circuit breaker is open")

        try:
            result = func(*args, **kwargs)
            self.failures = 0
            return result
        except Exception as e:
            self.failures += 1
            self.last_failure_time = time.time()
            if self.failures >= self.failure_threshold:
                self.is_open = True
                logger.warning(f"Circuit breaker opened after {self.failures} failures")
            raise e

    def is_healthy(self) -> bool:
        """Check if circuit breaker is healthy."""
        if not self.is_open:
            return True
        if time.time() - self.last_failure_time > self.timeout:
            self.is_open = False
            self.failures = 0
            return True
        return False


class MetricsCollector:
    """Collects and publishes CloudWatch metrics."""

    def __init__(self):
        self.metrics = {
            'successful': 0,
            'failed': 0,
            'rate_limited': 0,
            'retries': 0,
            'duration_ms': 0
        }
        self.start_time = None

    def start(self):
        """Start timing metrics collection."""
        self.start_time = time.time()

    def record_success(self):
        """Record successful scrape."""
        self.metrics['successful'] += 1

    def record_failure(self, error_type: str = "unknown"):
        """Record failed scrape."""
        self.metrics['failed'] += 1
        logger.error(f"Scrape failed: {error_type}")

    def record_rate_limited(self):
        """Record rate limit event."""
        self.metrics['rate_limited'] += 1

    def record_retry(self):
        """Record retry attempt."""
        self.metrics['retries'] += 1

    def publish_metrics(self, namespace: str = 'ThreadsScraper'):
        """Publish metrics to CloudWatch."""
        try:
            if self.start_time:
                self.metrics['duration_ms'] = int((time.time() - self.start_time) * 1000)

            cloudwatch.put_metric_data(
                Namespace=namespace,
                MetricData=[
                    {
                        'MetricName': 'SuccessfulScrapes',
                        'Value': self.metrics['successful'],
                        'Unit': 'Count'
                    },
                    {
                        'MetricName': 'FailedScrapes',
                        'Value': self.metrics['failed'],
                        'Unit': 'Count'
                    },
                    {
                        'MetricName': 'RateLimitedAttempts',
                        'Value': self.metrics['rate_limited'],
                        'Unit': 'Count'
                    },
                    {
                        'MetricName': 'RetryCount',
                        'Value': self.metrics['retries'],
                        'Unit': 'Count'
                    },
                    {
                        'MetricName': 'ExecutionDuration',
                        'Value': self.metrics['duration_ms'],
                        'Unit': 'Milliseconds'
                    }
                ]
            )
            logger.info("Metrics published to CloudWatch")
        except Exception as e:
            logger.error(f"Failed to publish metrics: {str(e)}")


class ThreadsScraper:
    """Scrapes Threads profile data using account credentials and proxy rotation."""

    def __init__(self):
        """Initialize ThreadsScraper with accounts and proxies."""
        self.accounts = self._load_accounts()
        self.proxies = self._load_proxies()
        self.account_index = 0
        self.proxy_index = 0
        self.session_cache = {}
        self.circuit_breaker = CircuitBreaker()
        self.metrics = MetricsCollector()
        logger.info(f"ThreadsScraper initialized: {len(self.accounts)} accounts, {len(self.proxies)} proxies")

    def _load_accounts(self) -> List[Dict[str, str]]:
        """Load Instagram accounts from Secrets Manager."""
        try:
            secret_arn = os.environ.get('INSTAGRAM_ACCOUNTS_SECRET_ARN')
            if not secret_arn:
                logger.error("INSTAGRAM_ACCOUNTS_SECRET_ARN not configured")
                return []

            response = secrets_client.get_secret_value(SecretId=secret_arn)
            secret_data = json.loads(response['SecretString'])
            accounts = secret_data.get('accounts', [])
            logger.info(f"Loaded {len(accounts)} accounts from Secrets Manager")
            return accounts
        except ClientError as e:
            logger.error(f"Failed to load accounts from Secrets Manager: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error loading accounts: {str(e)}")
            return []

    def _load_proxies(self) -> List[Dict[str, str]]:
        """Load proxy list from Secrets Manager."""
        try:
            secret_arn = os.environ.get('PROXY_LIST_SECRET_ARN')
            if not secret_arn:
                logger.warning("PROXY_LIST_SECRET_ARN not configured, will try direct connection")
                return []

            response = secrets_client.get_secret_value(SecretId=secret_arn)
            secret_data = json.loads(response['SecretString'])
            proxies = secret_data.get('proxies', [])
            logger.info(f"Loaded {len(proxies)} proxies from Secrets Manager")
            return proxies
        except ClientError as e:
            logger.warning(f"Failed to load proxies from Secrets Manager: {str(e)}")
            return []
        except Exception as e:
            logger.warning(f"Unexpected error loading proxies: {str(e)}")
            return []

    def _get_next_account(self) -> Optional[Dict[str, str]]:
        """Get next account in rotation."""
        if not self.accounts:
            return None
        account = self.accounts[self.account_index % len(self.accounts)]
        self.account_index += 1
        return account

    def _get_next_proxy(self) -> Optional[Dict[str, str]]:
        """Get next proxy in rotation with delay."""
        if not self.proxies:
            return None
        proxy = self.proxies[self.proxy_index % len(self.proxies)]
        self.proxy_index += 1
        time.sleep(random.uniform(1, BATCH_DELAY))
        return proxy

    def _get_random_user_agent(self) -> str:
        """Return random user agent string."""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
        ]
        return random.choice(user_agents)

    def _create_session(self, proxy: Optional[Dict[str, str]] = None) -> requests.Session:
        """Create requests session with proxy and retries."""
        session = requests.Session()

        # Configure retries
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Set headers
        session.headers.update({
            'User-Agent': self._get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })

        # Configure proxy if provided
        if proxy:
            session.proxies = {
                'http': proxy.get('url'),
                'https': proxy.get('url')
            }
            logger.debug(f"Session configured with proxy: {proxy.get('proxy_id')}")

        return session

    def scrape_threads_profile(self, threads_handle: str) -> Dict[str, Any]:
        """
        Scrape Threads profile with account rotation and proxy rotation.

        Args:
            threads_handle: Threads username to scrape

        Returns:
            Dict with success status, data, and metadata
        """
        if not threads_handle or not isinstance(threads_handle, str):
            return {
                'status': ScraperStatus.INVALID_HANDLE.value,
                'success': False,
                'error': 'Invalid threads handle',
                'raw_text': None
            }

        last_error = None
        for attempt in range(THREADS_MAX_RETRIES):
            try:
                self.metrics.record_retry() if attempt > 0 else None

                account = self._get_next_account()
                proxy = self._get_next_proxy()

                if not account:
                    return {
                        'status': ScraperStatus.FAILED.value,
                        'success': False,
                        'error': 'No accounts available',
                        'raw_text': None
                    }

                session = self._create_session(proxy)

                # Construct Threads profile URL
                url = f"https://www.threads.net/@{threads_handle}/"
                logger.info(f"Scraping {url} (attempt {attempt + 1}/{THREADS_MAX_RETRIES})")

                response = session.get(url, timeout=THREADS_TIMEOUT)

                if response.status_code == 200:
                    # Parse profile data
                    profile_data = self._parse_threads_profile(response.text)
                    if profile_data:
                        self.metrics.record_success()
                        return {
                            'status': ScraperStatus.SUCCESS.value,
                            'success': True,
                            'raw_text': response.text,
                            'data': profile_data,
                            'account_used': account.get('account_id', 'unknown'),
                            'proxy_used': proxy.get('proxy_id', 'direct') if proxy else 'direct'
                        }

                elif response.status_code == 429:
                    # Rate limited
                    self.metrics.record_rate_limited()
                    logger.warning(f"Rate limited (429) on attempt {attempt + 1}, retrying...")
                    backoff = THREAD_BACKOFF_BASE * (2 ** attempt)
                    time.sleep(backoff + random.uniform(0, 5))
                    continue

                elif response.status_code == 403:
                    # Forbidden / Detected
                    logger.warning(f"Detected (403) on attempt {attempt + 1}, rotating proxy...")
                    time.sleep(random.uniform(10, 15))
                    continue

                elif response.status_code == 404:
                    # Not found
                    self.metrics.record_failure("not_found")
                    return {
                        'status': ScraperStatus.NOT_FOUND.value,
                        'success': False,
                        'error': f'Profile not found (404)',
                        'raw_text': None
                    }

                else:
                    last_error = f"HTTP {response.status_code}"
                    logger.warning(f"Unexpected status {response.status_code} on attempt {attempt + 1}")
                    if attempt < THREADS_MAX_RETRIES - 1:
                        time.sleep(random.uniform(5, 10))
                    continue

            except requests.Timeout:
                last_error = "Request timeout"
                logger.warning(f"Timeout on attempt {attempt + 1}/{THREADS_MAX_RETRIES}")
                self.metrics.record_failure("timeout")
                if attempt < THREADS_MAX_RETRIES - 1:
                    time.sleep(random.uniform(5, 10))
                continue

            except requests.ConnectionError as e:
                last_error = f"Connection error: {str(e)}"
                logger.warning(f"Connection error on attempt {attempt + 1}: {str(e)}")
                self.metrics.record_failure("connection_error")
                if attempt < THREADS_MAX_RETRIES - 1:
                    time.sleep(random.uniform(5, 10))
                continue

            except Exception as e:
                last_error = f"Unexpected error: {str(e)}"
                logger.error(f"Unexpected error on attempt {attempt + 1}: {str(e)}")
                self.metrics.record_failure(str(type(e).__name__))
                if attempt < THREADS_MAX_RETRIES - 1:
                    time.sleep(random.uniform(5, 10))
                continue

        # All retries exhausted
        self.metrics.record_failure("max_retries_exceeded")
        return {
            'status': ScraperStatus.FAILED.value,
            'success': False,
            'error': last_error or 'Max retries exceeded',
            'raw_text': None
        }

    def _parse_threads_profile(self, html: str) -> Optional[Dict[str, Any]]:
        """
        Parse Threads profile data from HTML response.

        Args:
            html: HTML response from Threads profile page

        Returns:
            Dict with extracted profile data or None if parsing fails
        """
        try:
            if not html:
                return None

            data = {}

            # Extract follower count
            follower_match = re.search(r'"edge_followed_by":\{"count":(\d+)\}', html)
            if follower_match:
                data['followers'] = int(follower_match.group(1))
            else:
                # Try alternative pattern
                follower_match = re.search(r'followers["\']?\s*:\s*[\'"]*(\d+)', html, re.IGNORECASE)
                data['followers'] = int(follower_match.group(1)) if follower_match else None

            # Extract post count
            post_match = re.search(r'"edge_owner_to_timeline_media":\{"count":(\d+)\}', html)
            if post_match:
                data['posts'] = int(post_match.group(1))
            else:
                # Try alternative pattern
                post_match = re.search(r'posts["\']?\s*:\s*[\'"]*(\d+)', html, re.IGNORECASE)
                data['posts'] = int(post_match.group(1)) if post_match else None

            # Extract bio
            bio_match = re.search(r'"biography":"([^"]*)"', html)
            if bio_match:
                data['biography'] = bio_match.group(1)
            else:
                data['biography'] = None

            # Check for private account indicator
            is_private = bool(re.search(r'"is_private":\s*true', html))
            data['is_private'] = is_private

            logger.info(f"Parsed Threads profile: {data}")
            return data

        except Exception as e:
            logger.error(f"Error parsing Threads profile: {str(e)}")
            return None

    def process_celebrity(self, celebrity: Dict[str, str]) -> Dict[str, Any]:
        """
        Process a single celebrity and scrape their Threads profile.

        Args:
            celebrity: Celebrity record with celebrity_id and metadata

        Returns:
            Dict with processing result
        """
        celebrity_id = celebrity.get('celebrity_id')
        celebrity_name = celebrity.get('name')

        # Extract Threads handle
        threads_handle = self._extract_threads_handle(celebrity)

        if not threads_handle:
            logger.info(f"Skipping {celebrity_id}: No Threads handle found")
            return {
                'celebrity_id': celebrity_id,
                'name': celebrity_name,
                'status': ScraperStatus.INVALID_HANDLE.value,
                'reason': 'No Threads handle'
            }

        # Scrape profile
        result = self.scrape_threads_profile(threads_handle)

        if result['success']:
            return {
                'celebrity_id': celebrity_id,
                'name': celebrity_name,
                'threads_handle': threads_handle,
                'status': ScraperStatus.SUCCESS.value,
                'result': result
            }
        else:
            return {
                'celebrity_id': celebrity_id,
                'name': celebrity_name,
                'threads_handle': threads_handle,
                'status': result['status'],
                'error': result.get('error')
            }

    def _extract_threads_handle(self, celebrity: Dict[str, Any]) -> Optional[str]:
        """Extract Threads handle from celebrity record."""
        # Try different fields where Threads handle might be stored
        handle = celebrity.get('threads_handle')
        if handle:
            return handle

        # Check metadata
        metadata = celebrity.get('metadata', {})
        if isinstance(metadata, dict):
            handle = metadata.get('threads_handle')
            if handle:
                return handle

        # Check if same as Instagram handle (common for celebrities)
        instagram_handle = celebrity.get('instagram_handle') or celebrity.get('handle')
        if instagram_handle:
            return instagram_handle

        # Check name field
        name = celebrity.get('name', '')
        if name:
            # Convert name to handle-like format
            return name.lower().replace(' ', '')

        return None


def get_all_celebrities(table) -> List[Dict[str, Any]]:
    """Get all celebrities from DynamoDB."""
    try:
        response = table.scan()
        # Filter to get only metadata entries (source_type#timestamp starts with 'metadata#')
        celebrities = []
        seen_ids = set()

        for item in response.get('Items', []):
            celebrity_id = item.get('celebrity_id')
            # Get unique celebrities (first entry for each ID)
            if celebrity_id and celebrity_id not in seen_ids:
                celebrities.append(item)
                seen_ids.add(celebrity_id)

        logger.info(f"Found {len(celebrities)} unique celebrities in database")
        return celebrities
    except Exception as e:
        logger.error(f"Error fetching celebrities from DynamoDB: {str(e)}")
        return []


def save_to_dynamodb(table, celebrity_id: str, scrape_result: Dict[str, Any],
                     request_id: str) -> bool:
    """
    Save scraping result to DynamoDB.

    Args:
        table: DynamoDB table resource
        celebrity_id: Celebrity ID
        scrape_result: Scraping result from ThreadsScraper
        request_id: Request tracking ID

    Returns:
        True if successful, False otherwise
    """
    try:
        timestamp = datetime.utcnow().isoformat() + 'Z'

        item = {
            'celebrity_id': celebrity_id,
            'source_type#timestamp': f"threads#{timestamp}",
            'id': str(uuid.uuid4()),
            'name': scrape_result.get('name'),
            'raw_text': scrape_result.get('result', {}).get('raw_text'),
            'source': 'https://www.threads.net',
            'timestamp': timestamp,
            'weight': None,
            'sentiment': None,
            'metadata': {
                'scraper_name': 'scraper-threads',
                'source_type': 'threads',
                'processed': False,
                'error': None,
                'request_id': request_id,
                'threads_handle': scrape_result.get('threads_handle'),
                'account_used': scrape_result.get('result', {}).get('account_used'),
                'proxy_used': scrape_result.get('result', {}).get('proxy_used'),
                'scraped_data': scrape_result.get('result', {}).get('data')
            },
            'request_id': request_id
        }

        table.put_item(Item=item)
        logger.info(f"Saved Threads data for {celebrity_id} to DynamoDB")
        return True

    except Exception as e:
        logger.error(f"Error saving to DynamoDB: {str(e)}")
        return False


def lambda_handler(event, context) -> Dict[str, Any]:
    """
    Lambda handler for Threads scraper.

    Event structure:
    {
        "celebrities": [  # Optional: specific celebrities to scrape
            {"celebrity_id": "celeb_001", "name": "Celebrity Name"}
        ],
        "limit": 10  # Optional: limit number of celebrities
    }
    """
    request_id = context.aws_request_id if context else str(uuid.uuid4())
    logger.info(f"Starting Threads scraper execution (request_id={request_id})")

    metrics = MetricsCollector()
    metrics.start()

    try:
        # Get DynamoDB table
        table_name = os.environ.get('DYNAMODB_TABLE', 'celebrity-database')
        table = dynamodb.Table(table_name)

        # Initialize scraper
        scraper = ThreadsScraper()

        # Check if we have necessary resources
        if not scraper.accounts:
            logger.error("No Instagram accounts configured")
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'No Instagram accounts configured',
                    'success': 0,
                    'failed': 0,
                    'skipped': 0
                })
            }

        # Get celebrities to scrape
        celebrities = event.get('celebrities', [])
        if not celebrities:
            # Get all celebrities from database
            limit = event.get('limit', None)
            all_celebrities = get_all_celebrities(table)
            if limit:
                celebrities = all_celebrities[:limit]
            else:
                celebrities = all_celebrities

        logger.info(f"Processing {len(celebrities)} celebrities")

        # Process each celebrity
        results = []
        success_count = 0
        error_count = 0
        skipped_count = 0

        for i, celebrity in enumerate(celebrities):
            try:
                logger.info(f"Processing {i + 1}/{len(celebrities)}: {celebrity.get('name')}")

                # Process celebrity
                process_result = scraper.process_celebrity(celebrity)

                if process_result['status'] == ScraperStatus.SUCCESS.value:
                    # Save to DynamoDB
                    if save_to_dynamodb(table, celebrity.get('celebrity_id'), process_result, request_id):
                        success_count += 1
                        results.append({
                            'celebrity_id': celebrity.get('celebrity_id'),
                            'name': celebrity.get('name'),
                            'status': 'success',
                            'threads_handle': process_result.get('threads_handle')
                        })
                    else:
                        error_count += 1
                        results.append({
                            'celebrity_id': celebrity.get('celebrity_id'),
                            'name': celebrity.get('name'),
                            'status': 'error',
                            'error': 'Failed to save to DynamoDB'
                        })
                elif process_result['status'] == ScraperStatus.INVALID_HANDLE.value:
                    skipped_count += 1
                    results.append({
                        'celebrity_id': celebrity.get('celebrity_id'),
                        'name': celebrity.get('name'),
                        'status': 'skipped',
                        'reason': 'No Threads handle'
                    })
                else:
                    error_count += 1
                    results.append({
                        'celebrity_id': celebrity.get('celebrity_id'),
                        'name': celebrity.get('name'),
                        'status': 'error',
                        'error': process_result.get('error')
                    })

                # Add batch delay between requests
                if i < len(celebrities) - 1:
                    time.sleep(random.uniform(1, 3))

            except Exception as e:
                logger.error(f"Error processing celebrity: {str(e)}")
                error_count += 1
                results.append({
                    'celebrity_id': celebrity.get('celebrity_id'),
                    'status': 'error',
                    'error': str(e)
                })

        # Publish metrics
        metrics.metrics['successful'] = success_count
        metrics.metrics['failed'] = error_count
        metrics.publish_metrics()

        logger.info(f"Completed: {success_count} successful, {error_count} errors, {skipped_count} skipped")

        return {
            'statusCode': 200,
            'body': json.dumps({
                'total': len(celebrities),
                'success': success_count,
                'errors': error_count,
                'skipped': skipped_count,
                'details': results[:10]  # Return first 10 for brevity
            })
        }

    except Exception as e:
        logger.error(f"Fatal error in lambda_handler: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'success': 0,
                'failed': 1
            })
        }

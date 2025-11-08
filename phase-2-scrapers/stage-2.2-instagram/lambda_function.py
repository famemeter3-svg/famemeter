"""
AWS Lambda Handler: Instagram Data Collection with Instaloader

Robust implementation with:
- Error handling + exponential backoff retries
- DynamoDB batch writes
- CloudWatch structured logging
- Metrics collection
- Circuit breaker for rate limiting
"""

import boto3
import instaloader
import json
import os
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from botocore.exceptions import ClientError
from enum import Enum
import time

# AWS Clients
dynamodb = boto3.resource('dynamodb')
secrets_client = boto3.client('secretsmanager')
cloudwatch = boto3.client('cloudwatch')
logs_client = boto3.client('logs')

# Configuration from environment
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE', 'celebrity-database')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
INSTAGRAM_ACCOUNTS_SECRET_ARN = os.environ.get('INSTAGRAM_ACCOUNTS_SECRET_ARN')
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
INSTAGRAM_TIMEOUT = int(os.environ.get('INSTAGRAM_TIMEOUT', '30'))
INSTAGRAM_MAX_RETRIES = int(os.environ.get('INSTAGRAM_MAX_RETRIES', '3'))

# Logging setup
logger = logging.getLogger()
logger.setLevel(getattr(logging, LOG_LEVEL))

# JSON formatter for structured logging
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        if hasattr(record, 'request_id'):
            log_obj['request_id'] = record.request_id
        return json.dumps(log_obj)

handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.handlers = [handler]


class ScraperStatus(Enum):
    """Enumeration for scraper operation status."""
    SUCCESS = 'success'
    PROFILE_NOT_FOUND = 'profile_not_found'
    RATE_LIMITED = 'rate_limited'
    PRIVATE_ACCOUNT = 'private_account'
    LOGIN_REQUIRED = 'login_required'
    NETWORK_ERROR = 'network_error'
    UNKNOWN_ERROR = 'unknown_error'
    RETRY_EXHAUSTED = 'retry_exhausted'


class CircuitBreaker:
    """Circuit breaker for rate limiting."""

    def __init__(self, failure_threshold: int = 5, timeout: int = 300):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.is_open = False

    def record_success(self):
        """Record successful request."""
        self.failure_count = 0
        self.is_open = False

    def record_failure(self):
        """Record failed request."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        if self.failure_count >= self.failure_threshold:
            self.is_open = True
            logger.warning(f"Circuit breaker OPEN - {self.failure_count} failures")

    def can_execute(self) -> bool:
        """Check if execution is allowed."""
        if not self.is_open:
            return True

        # Check if timeout has expired
        if self.last_failure_time:
            elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
            if elapsed > self.timeout:
                self.is_open = False
                self.failure_count = 0
                logger.info("Circuit breaker CLOSED - resuming operations")
                return True

        return False


class MetricsCollector:
    """Collect and publish CloudWatch metrics."""

    def __init__(self, request_id: str):
        self.request_id = request_id
        self.metrics = {
            'successful_scrapes': 0,
            'failed_scrapes': 0,
            'rate_limited': 0,
            'not_found': 0,
            'errors_by_type': {},
            'retry_count': 0,
            'start_time': datetime.utcnow()
        }

    def record_success(self):
        """Record successful scrape."""
        self.metrics['successful_scrapes'] += 1

    def record_failure(self, error_type: str):
        """Record failed scrape."""
        self.metrics['failed_scrapes'] += 1
        self.metrics['errors_by_type'][error_type] = self.metrics['errors_by_type'].get(error_type, 0) + 1

    def record_rate_limited(self):
        """Record rate limit event."""
        self.metrics['rate_limited'] += 1

    def record_retry(self):
        """Record retry attempt."""
        self.metrics['retry_count'] += 1

    def publish(self):
        """Publish metrics to CloudWatch."""
        try:
            end_time = datetime.utcnow()
            duration = (end_time - self.metrics['start_time']).total_seconds()

            cloudwatch.put_metric_data(
                Namespace='InstagramScraper',
                MetricData=[
                    {
                        'MetricName': 'SuccessfulScrapes',
                        'Value': self.metrics['successful_scrapes'],
                        'Unit': 'Count',
                        'Timestamp': end_time
                    },
                    {
                        'MetricName': 'FailedScrapes',
                        'Value': self.metrics['failed_scrapes'],
                        'Unit': 'Count',
                        'Timestamp': end_time
                    },
                    {
                        'MetricName': 'ExecutionDuration',
                        'Value': duration,
                        'Unit': 'Seconds',
                        'Timestamp': end_time
                    },
                    {
                        'MetricName': 'RateLimitedCount',
                        'Value': self.metrics['rate_limited'],
                        'Unit': 'Count',
                        'Timestamp': end_time
                    },
                    {
                        'MetricName': 'RetryCount',
                        'Value': self.metrics['retry_count'],
                        'Unit': 'Count',
                        'Timestamp': end_time
                    }
                ]
            )
            logger.info(f"Metrics published: {json.dumps(self.metrics, default=str)}")
        except Exception as e:
            logger.error(f"Failed to publish metrics: {str(e)}")


class InstagramScraper:
    """Main Instagram scraper using Instaloader."""

    def __init__(self, request_id: str):
        self.request_id = request_id
        self.L = instaloader.Instaloader(
            quiet=True,
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            download_videos=False,
            download_video_thumbnails=False,
            save_metadata=False,
            compress_json=False,
        )
        self.accounts = self.load_accounts()
        self.account_index = 0
        self.circuit_breaker = CircuitBreaker()
        self.metrics = MetricsCollector(request_id)
        self.processed_profiles = set()  # Track to avoid duplicates

    def add_request_id(self, record):
        """Add request ID to log records."""
        record.request_id = self.request_id
        return True

    def load_accounts(self) -> List[Dict]:
        """Load Instagram accounts from Secrets Manager (optional)."""
        try:
            if not INSTAGRAM_ACCOUNTS_SECRET_ARN:
                logger.info("No INSTAGRAM_ACCOUNTS_SECRET_ARN provided, will run in anonymous mode")
                return []

            secret = secrets_client.get_secret_value(SecretId=INSTAGRAM_ACCOUNTS_SECRET_ARN)
            accounts = json.loads(secret['SecretString']).get('accounts', [])
            logger.info(f"Loaded {len(accounts)} Instagram accounts from Secrets Manager")
            return accounts

        except ClientError as e:
            logger.warning(f"Failed to load accounts from Secrets Manager: {str(e)}, continuing anonymously")
            return []
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid account JSON format: {str(e)}, continuing anonymously")
            return []

    def login_next_account(self) -> Optional[str]:
        """Login with next account from rotation, fallback to anonymous."""
        if not self.accounts:
            logger.debug("No accounts available, running in anonymous mode")
            return None

        account = self.accounts[self.account_index % len(self.accounts)]
        self.account_index += 1

        try:
            self.L.login(account['username'], account['password'])
            logger.info(f"Logged in as: {account['username']}")
            return account.get('account_id')
        except Exception as e:
            logger.warning(f"Login failed for {account['username']}: {str(e)}, continuing anonymously")
            return None

    def scrape_instagram_profile(self, instagram_handle: str) -> Tuple[bool, Dict]:
        """
        Scrape Instagram profile with exponential backoff retry.

        Returns:
            Tuple[bool, Dict]: (success, data)
        """
        # Check circuit breaker
        if not self.circuit_breaker.can_execute():
            logger.warning(f"Circuit breaker OPEN, skipping {instagram_handle}")
            return False, {
                'status': ScraperStatus.RATE_LIMITED.value,
                'error': 'Circuit breaker is open due to excessive rate limiting'
            }

        # Check for duplicates
        if instagram_handle in self.processed_profiles:
            logger.info(f"Profile already processed in this run: {instagram_handle}")
            return False, {
                'status': 'duplicate',
                'error': f'Profile already processed: {instagram_handle}'
            }

        for attempt in range(INSTAGRAM_MAX_RETRIES):
            try:
                # Fetch profile
                profile = instaloader.Profile.from_username(self.L.context, instagram_handle)

                # Mark as processed
                self.processed_profiles.add(instagram_handle)

                data = {
                    'status': ScraperStatus.SUCCESS.value,
                    'username': profile.username,
                    'followers': profile.follower_count,
                    'posts': profile.mediacount,
                    'biography': profile.biography,
                    'is_verified': profile.is_verified,
                    'is_business_account': profile.is_business_account,
                    'is_private': profile.is_private,
                    'profile_pic_url': profile.profile_pic_url if hasattr(profile, 'profile_pic_url') else None,
                }

                self.circuit_breaker.record_success()
                self.metrics.record_success()
                logger.info(f"Successfully scraped: {instagram_handle} ({profile.follower_count} followers)")
                return True, data

            except instaloader.exceptions.ProfileNotExistsException:
                self.metrics.record_failure('profile_not_found')
                logger.warning(f"Profile not found: {instagram_handle}")
                return False, {
                    'status': ScraperStatus.PROFILE_NOT_FOUND.value,
                    'error': f'Profile does not exist: {instagram_handle}'
                }

            except instaloader.exceptions.PrivateProfileNotFollowedException:
                self.metrics.record_failure('private_account')
                logger.warning(f"Private account (not followed): {instagram_handle}")
                return False, {
                    'status': ScraperStatus.PRIVATE_ACCOUNT.value,
                    'error': f'Private account requires follow: {instagram_handle}'
                }

            except instaloader.exceptions.LoginRequiredException:
                self.metrics.record_failure('login_required')
                logger.warning(f"Login required for {instagram_handle}, attempt {attempt + 1}/{INSTAGRAM_MAX_RETRIES}")

                if attempt < INSTAGRAM_MAX_RETRIES - 1:
                    self.login_next_account()
                    self.metrics.record_retry()
                    continue

                return False, {
                    'status': ScraperStatus.LOGIN_REQUIRED.value,
                    'error': f'Login required and all accounts failed: {instagram_handle}'
                }

            except instaloader.exceptions.TooManyRequestsException:
                self.metrics.record_rate_limited()
                logger.warning(f"Rate limited for {instagram_handle}, attempt {attempt + 1}/{INSTAGRAM_MAX_RETRIES}")
                self.circuit_breaker.record_failure()

                if attempt < INSTAGRAM_MAX_RETRIES - 1:
                    wait_time = 10 * (2 ** attempt)  # Exponential backoff: 10s, 20s, 40s
                    logger.info(f"Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    self.metrics.record_retry()
                    continue

                return False, {
                    'status': ScraperStatus.RATE_LIMITED.value,
                    'error': f'Rate limited after {INSTAGRAM_MAX_RETRIES} retries: {instagram_handle}'
                }

            except Exception as e:
                error_type = type(e).__name__
                self.metrics.record_failure(error_type)
                logger.error(f"Exception on attempt {attempt + 1}/{INSTAGRAM_MAX_RETRIES}: {error_type}: {str(e)}")

                if attempt < INSTAGRAM_MAX_RETRIES - 1:
                    wait_time = 5 * (attempt + 1)
                    logger.info(f"Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    self.metrics.record_retry()
                    continue

        return False, {
            'status': ScraperStatus.RETRY_EXHAUSTED.value,
            'error': f'Max retries ({INSTAGRAM_MAX_RETRIES}) exceeded for {instagram_handle}'
        }

    def get_celebrities_from_dynamodb(self, limit: Optional[int] = None) -> List[Dict]:
        """Get list of celebrities from DynamoDB."""
        try:
            table = dynamodb.Table(DYNAMODB_TABLE)

            # Scan for celebrities (limit to avoid timeout)
            response = table.scan(Limit=limit or 100)
            celebrities = response.get('Items', [])

            logger.info(f"Retrieved {len(celebrities)} celebrities from DynamoDB")
            return celebrities
        except Exception as e:
            logger.error(f"Failed to retrieve celebrities: {str(e)}")
            return []

    def save_to_dynamodb(self, celebrity_id: str, celebrity_name: str, instagram_data: Dict) -> bool:
        """Save scraped Instagram data to DynamoDB."""
        try:
            table = dynamodb.Table(DYNAMODB_TABLE)

            timestamp = datetime.utcnow().isoformat()
            item = {
                'celebrity_id': celebrity_id,
                'source_type#timestamp': f"instagram#{timestamp}",
                'name': celebrity_name,
                'source': 'instagram',
                'timestamp': timestamp,
                'raw_text': json.dumps(instagram_data),
                'id': str(uuid.uuid4()),
                'weight': None,
                'sentiment': None,
                'request_id': self.request_id  # Track which request created this
            }

            table.put_item(Item=item)
            logger.info(f"Saved Instagram data for {celebrity_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to save to DynamoDB: {str(e)}")
            return False

    def process_celebrity(self, celebrity: Dict) -> Dict:
        """Process single celebrity."""
        celebrity_id = celebrity.get('celebrity_id')
        celebrity_name = celebrity.get('name', 'Unknown')
        instagram_handle = celebrity.get('instagram_handle') or celebrity.get('instagram')

        if not instagram_handle:
            logger.warning(f"Skipping {celebrity_name} (no Instagram handle)")
            return {
                'celebrity_id': celebrity_id,
                'name': celebrity_name,
                'status': 'skipped',
                'reason': 'no_instagram_handle'
            }

        # Scrape profile
        success, data = self.scrape_instagram_profile(instagram_handle)

        if success:
            # Save to DynamoDB
            saved = self.save_to_dynamodb(celebrity_id, celebrity_name, data)
            return {
                'celebrity_id': celebrity_id,
                'name': celebrity_name,
                'instagram_handle': instagram_handle,
                'status': 'success' if saved else 'save_failed',
                'data': data
            }
        else:
            return {
                'celebrity_id': celebrity_id,
                'name': celebrity_name,
                'instagram_handle': instagram_handle,
                'status': 'failed',
                'reason': data.get('status'),
                'error': data.get('error')
            }


def lambda_handler(event, context):
    """
    AWS Lambda handler for Instagram scraping.

    Event format:
    {
        "celebrities": [
            {"celebrity_id": "id", "name": "Name", "instagram_handle": "handle"}
        ],
        "limit": 100  # Optional: limit number of celebrities to process
    }
    """
    request_id = context.aws_request_id if context else str(uuid.uuid4())
    logger.info(f"Starting Instagram scraping job (request_id: {request_id})")

    try:
        # Initialize scraper
        scraper = scraper_instance = InstagramScraper(request_id)
        logger.handlers[0].addFilter(scraper.add_request_id)

        # Get celebrities to process
        if 'celebrities' in event:
            celebrities = event['celebrities']
            logger.info(f"Processing {len(celebrities)} celebrities from event")
        else:
            limit = event.get('limit')
            celebrities = scraper.get_celebrities_from_dynamodb(limit)
            logger.info(f"Processing {len(celebrities)} celebrities from DynamoDB")

        if not celebrities:
            logger.warning("No celebrities to process")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'No celebrities to process',
                    'request_id': request_id
                })
            }

        # Process each celebrity
        results = {
            'request_id': request_id,
            'timestamp': datetime.utcnow().isoformat(),
            'total_celebrities': len(celebrities),
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'details': []
        }

        for celebrity in celebrities:
            result = scraper.process_celebrity(celebrity)
            results['details'].append(result)

            if result['status'] == 'success':
                results['successful'] += 1
            elif result['status'] == 'skipped':
                results['skipped'] += 1
            else:
                results['failed'] += 1

        # Publish metrics
        scraper.metrics.publish()

        # Log summary
        logger.info(f"Scraping job complete: {results['successful']} successful, {results['failed']} failed, {results['skipped']} skipped")

        return {
            'statusCode': 200,
            'body': json.dumps(results, default=str)
        }

    except Exception as e:
        logger.error(f"Fatal error in lambda_handler: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'request_id': request_id
            })
        }

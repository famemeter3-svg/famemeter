# Phase 2: Data Source Scrapers - Four-Stage Collection System

## Executive Summary

Phase 2 implements the data collection layer of the system using a **four-stage pipeline** for diverse data sources. Each stage is independently deployable and uses different collection methodologies optimized for its data source. This phase is critical for populating the database with rich, first-hand data from multiple origins.

**Key Principle**: Each stage is independently deployable and testable. Failure of one stage should not block others. All data is stored in its raw, unprocessed form for post-processing in Phase 3.

---

## 📌 IMPORTANT: Database Integration Reference

**Before implementing any scraper**, read **[DATABASE_INTEGRATION.md](./DATABASE_INTEGRATION.md)** for:
- ✅ DynamoDB table structure (from Phase 1)
- ✅ Celebrity metadata schema
- ✅ How to read/write scraper entries
- ✅ Required IAM permissions & environment variables
- ✅ Query patterns for each stage
- ✅ Troubleshooting & monitoring

This provides essential context that ALL stages depend on.

---

## Overview

Phase 2 accomplishes:
1. **Stage 2.1**: Google Search API data collection with raw text cleaning
2. **Stage 2.2**: Instagram account-based scraping with credential management and proxy rotation
3. **Stage 2.3**: Threads account-based scraping with anti-detection measures
4. **Stage 2.4**: YouTube API integration for channel and video data

Each stage follows the same pattern:
```
EventBridge Trigger
  ↓
Get All Celebrities from DynamoDB
  ↓
For Each Celebrity:
  - Fetch data from source API/account
  - Validate response
  - Create scraper entry (first-hand data)
  - Write to DynamoDB
  ↓
Return summary (success count, errors, details)
```

## Data Collection Architecture

### First-Hand Data Requirement

All scrapers at Stage 2 must capture **first-hand data** - the raw, unprocessed response from the data source. This data is stored completely in the `raw_text` field and will be processed in Phase 3.

**First-Hand Fields** (Set during scrape):
```json
{
  "id": "uuid-string",
  "name": "Celebrity Name",
  "raw_text": "{complete unprocessed API response or HTML}",
  "source": "https://source.url/endpoint",
  "timestamp": "2025-11-07T17:20:00Z"
}
```

**DynamoDB Write Pattern**:
```
Key: celebrity_id + source_type#timestamp
Example: celeb_001 + google_search#2025-11-07T17:20:00Z
```

---

## Stage 2.1: Google Search API - Simple Text Cleaning

### Purpose
Collect search results and basic information about celebrities using Google Search API with straightforward raw text cleaning.

### Data Source
- **Source**: Google Custom Search API or Google Search with SERP parsing
- **API Tier**: Free tier (100 searches/day) or paid ($0.05 per search)
- **Data**: Search results, snippets, basic information, news references
- **Rate Limiting**: 100 requests/day (free), higher with paid tier
- **Status**: ✅ Production Ready

### Lambda Configuration

**Function Name**: `scraper-google-search`
- **Runtime**: Python 3.11
- **Memory**: 512 MB
- **Timeout**: 5 minutes (300 seconds)
- **Ephemeral Storage**: 512 MB
- **Trigger**: EventBridge (weekly)

**Environment Variables**:
```bash
GOOGLE_API_KEY=your_api_key_here
GOOGLE_SEARCH_ENGINE_ID=your_search_engine_id_here
DYNAMODB_TABLE=celebrity-database
AWS_REGION=us-east-1
LOG_LEVEL=INFO
GOOGLE_TIMEOUT=10
```

### Data Collection Flow

```
1. GET Celebrity from DynamoDB
   ├─ Extract: name, celebrity_id
   └─ Validate: name not empty

2. CALL Google Search API
   ├─ Search query: "{celebrity_name}"
   ├─ Handle rate limiting (max 10 requests/second)
   ├─ Implement exponential backoff
   ├─ Timeout after 10 seconds
   └─ Catch all exceptions

3. PARSE Response
   ├─ Validate JSON response format
   ├─ Extract search results array
   ├─ Clean raw text (remove excessive whitespace, standardize encoding)
   ├─ Store complete raw response
   └─ Check for errors in response

4. CREATE Scraper Entry (FIRST-HAND)
   ├─ Generate unique ID (UUID)
   ├─ Set ISO 8601 timestamp
   ├─ Populate:
   │  ├─ id (unique UUID)
   │  ├─ name (from input or API response)
   │  ├─ raw_text (complete JSON response with cleaned text)
   │  ├─ source (https://www.googleapis.com/customsearch/v1)
   │  └─ timestamp (ISO 8601)
   ├─ Initialize computed fields to null:
   │  ├─ weight = null
   │  └─ sentiment = null
   └─ Add metadata

5. WRITE to DynamoDB
   ├─ Key: celebrity_id + google_search#timestamp
   ├─ Exponential backoff on failure
   ├─ Verify write succeeded
   └─ Log result

6. RETURN Status
   ├─ Success: {status: 'success'}
   └─ Error: {status: 'error', error: message}
```

### Implementation Details

**Raw Text Cleaning**:
```python
def clean_raw_text(response_data):
    """
    Clean raw Google API response.
    - Normalize whitespace
    - Remove null bytes
    - Ensure valid UTF-8 encoding
    - Preserve structure of JSON
    """
    # Remove extra whitespace
    import re
    import json

    # If JSON, ensure valid formatting
    try:
        data = json.loads(response_data) if isinstance(response_data, str) else response_data
        # Normalize nested strings
        cleaned = json.dumps(data, ensure_ascii=False)
        return cleaned
    except:
        # Fallback: clean text directly
        text = str(response_data)
        text = re.sub(r'\s+', ' ', text)  # Collapse whitespace
        text = text.encode('utf-8', 'ignore').decode('utf-8')  # Remove non-UTF8
        return text
```

**API Call Example**:
```python
import requests
from datetime import datetime
import uuid

def fetch_google_search_data(celebrity_name, api_key, search_engine_id):
    """
    Fetch search results from Google Custom Search API.
    """
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        'q': celebrity_name,
        'key': api_key,
        'cx': search_engine_id,
        'num': 10  # Get top 10 results
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        return {
            'success': True,
            'raw_text': json.dumps(data),  # Store complete response
            'item_count': len(data.get('items', [])),
            'error': None
        }

    except requests.Timeout:
        return {'success': False, 'error': 'API timeout', 'raw_text': None}
    except requests.HTTPError as e:
        return {'success': False, 'error': f'HTTP {e.response.status_code}', 'raw_text': None}
    except Exception as e:
        return {'success': False, 'error': str(e), 'raw_text': None}

def lambda_handler(event, context):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])

    api_key = os.environ['GOOGLE_API_KEY']
    search_engine_id = os.environ['GOOGLE_SEARCH_ENGINE_ID']

    # Get all celebrities
    celebrities = get_all_celebrities(table)

    results = []
    for celeb in celebrities:
        try:
            # Fetch data from Google
            google_result = fetch_google_search_data(
                celeb['name'],
                api_key,
                search_engine_id
            )

            if google_result['success']:
                # Create scraper entry (FIRST-HAND)
                scraper_entry = {
                    "id": str(uuid.uuid4()),
                    "name": celeb['name'],
                    "raw_text": google_result['raw_text'],
                    "source": "https://www.googleapis.com/customsearch/v1",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "weight": None,
                    "sentiment": None
                }

                # Write to DynamoDB
                table.put_item(Item={
                    'celebrity_id': celeb['celebrity_id'],
                    'source_type#timestamp': f"google_search#{scraper_entry['timestamp']}",
                    **scraper_entry
                })

                results.append({
                    'celebrity_id': celeb['celebrity_id'],
                    'name': celeb['name'],
                    'status': 'success',
                    'item_count': google_result.get('item_count', 0)
                })
            else:
                results.append({
                    'celebrity_id': celeb['celebrity_id'],
                    'name': celeb['name'],
                    'status': 'error',
                    'error': google_result['error']
                })

        except Exception as e:
            results.append({
                'celebrity_id': celeb['celebrity_id'],
                'name': celeb['name'],
                'status': 'error',
                'error': str(e)
            })

    return {
        'total': len(celebrities),
        'success': len([r for r in results if r['status'] == 'success']),
        'errors': len([r for r in results if r['status'] == 'error']),
        'details': results
    }
```

### Error Handling

**Error**: API Timeout
```
Scenario: Google API doesn't respond within 10 seconds
Handling: Log timeout error
Recovery: Retry up to 3 times with exponential backoff (1s, 2s, 4s)
Fallback: Skip celebrity, continue to next
```

**Error**: Invalid API Key
```
Scenario: API key invalid or expired
Handling: Log error immediately, do not retry
Recovery: Verify key in AWS Secrets Manager
Fallback: Exit scraper, report error in summary
```

**Error**: Rate Limit Exceeded (429)
```
Scenario: Too many requests to Google API
Handling: Check Retry-After header
Recovery: Implement exponential backoff, retry operation
Fallback: Skip remaining celebrities, report status
```

**Error**: Malformed Response
```
Scenario: Response is not valid JSON
Handling: Log response sample, validate before parsing
Recovery: Store raw text anyway, continue
Fallback: Skip celebrity
```

**Error**: DynamoDB Write Failure
```
Scenario: Put operation fails (throttling, permissions)
Handling: Log error with item details
Recovery: Retry with exponential backoff
Fallback: Log and continue (data lost for this entry)
```

### Testing Protocol

**Phase 2.1A: Single Scraper Setup**

**Step 1: Obtain API Key**
```bash
# 1. Visit https://console.cloud.google.com
# 2. Create project "celebrity-database"
# 3. Enable Custom Search API
# 4. Create API key (Credentials > Create API Key)
# 5. Create custom search engine at https://cse.google.com
# 6. Copy Search Engine ID
```

**Step 2: Configure Environment**
```bash
cd phase-2-scrapers/scraper-google-search/
cp .env.template .env
# Edit .env and add:
# GOOGLE_API_KEY=your_actual_key
# GOOGLE_SEARCH_ENGINE_ID=your_engine_id
# DYNAMODB_TABLE=celebrity-database
# AWS_REGION=us-east-1
```

**Step 3: Test with Single Celebrity (Offline)**
```bash
python3 lambda_function.py --test-mode --celebrity "Leonardo DiCaprio"
# Expected: ✓ Function runs without crashes
# Expected: ✓ Error handling works
# Expected: ✓ Logging is clear
```

**Step 4: Test with Single Celebrity (Online)**
```bash
aws lambda invoke \
  --function-name scraper-google-search-dev \
  --payload '{"celebrities":[{"celebrity_id":"celeb_001","name":"Leonardo DiCaprio"}]}' \
  response.json

cat response.json | jq '.'
# Expected:
# {
#   "total": 1,
#   "success": 1,
#   "errors": 0,
#   "details": [{
#     "celebrity_id": "celeb_001",
#     "status": "success",
#     "item_count": 10
#   }]
# }
```

**Step 5: Verify Data in DynamoDB**
```bash
aws dynamodb query --table-name celebrity-database \
  --key-condition-expression "celebrity_id = :id" \
  --expression-attribute-values "{\":id\":{\"S\":\"celeb_001\"}}" \
  --query 'Items[] | [?begins_with(source_type#timestamp, `google_search`)]'

# Expected: At least one google_search entry with:
# - id, name, raw_text, source, timestamp populated
# - weight and sentiment are null
# - raw_text contains valid JSON from Google API
```

**Step 6: STOP IF ANY ERRORS**
- [ ] Log all CloudWatch errors
- [ ] Check API key validity and quota
- [ ] Verify IAM role has DynamoDB permissions
- [ ] **DO NOT proceed to 5 celebrities** until this passes
- [ ] Fix errors and re-run steps 4-5

**Phase 2.1B: Batch Testing (5 Celebrities)**

```bash
aws lambda invoke \
  --function-name scraper-google-search-dev \
  --payload '{"limit": 5}' \
  response.json

# Monitor logs
aws logs tail /aws/lambda/scraper-google-search-dev --follow

# Verify results
cat response.json | jq '.[] | select(.status == "error")'

# If success rate >= 80%, proceed to full deployment
```

**Phase 2.1C: Full Deployment (100 Celebrities)**

```bash
aws lambda update-function-code \
  --function-name scraper-google-search \
  --zip-file fileb://function.zip

aws lambda invoke \
  --function-name scraper-google-search \
  --payload '{}' \
  response.json

# Final verification
aws dynamodb scan --table-name celebrity-database \
  --filter-expression "begins_with(#key, :source)" \
  --expression-attribute-names "{\"#key\":\"source_type#timestamp\"}" \
  --expression-attribute-values "{\":source\":{\"S\":\"google_search#\"}}" \
  --select COUNT

# Expected: 100 entries (or close to it)
```

**Cost Estimate**: ~$0-2/month (depends on free vs paid API tier)

---

## Stage 2.2: Instagram - Account-Based Scraping with Proxy Rotation

### Purpose
Collect Instagram account data by using dedicated accounts with real credentials to mimic user behavior and gather information while avoiding detection through proxy rotation.

### Data Source
- **Source**: Instagram Web (via account login with proxy)
- **Authentication**: Real account credentials (username/password)
- **Data**: Follower count, post count, bio information, engagement metrics
- **Rate Limiting**: Variable by Instagram's anti-bot detection
- **Scaling**: Supports multiple accounts provided
- **Status**: ⚠️ Requires Careful Implementation (Anti-Detection)

### Key Features
- Real account authentication for accurate data collection
- **Proxy rotation** to avoid IP-based detection
- **User-Agent rotation** for request diversity
- Graceful handling of rate limiting and detection blocks
- **Scalable**: Can add more accounts to increase throughput
- **Low-key operation**: Minimal footprint, respectful of platform

### Lambda Configuration

**Function Name**: `scraper-instagram`
- **Runtime**: Python 3.11
- **Memory**: 1024 MB (higher due to session management)
- **Timeout**: 10 minutes (600 seconds)
- **Ephemeral Storage**: 512 MB
- **Trigger**: EventBridge (weekly)

**Environment Variables**:
```bash
INSTAGRAM_ACCOUNTS_SECRET_ARN=arn:aws:secretsmanager:region:account:secret:instagram-accounts
PROXY_LIST_SECRET_ARN=arn:aws:secretsmanager:region:account:secret:proxy-list
DYNAMODB_TABLE=celebrity-database
AWS_REGION=us-east-1
LOG_LEVEL=INFO
INSTAGRAM_TIMEOUT=20
INSTAGRAM_MAX_RETRIES=3
USE_PROXY=true
ROTATION_DELAY_MIN=2
ROTATION_DELAY_MAX=5
```

### Instagram Credentials Management

**Secrets Manager Structure** - `instagram-accounts`:
```json
{
  "accounts": [
    {
      "account_id": "account_001",
      "username": "dedicated_account_1",
      "password": "encrypted_password_1",
      "status": "active",
      "created": "2025-11-01"
    },
    {
      "account_id": "account_002",
      "username": "dedicated_account_2",
      "password": "encrypted_password_2",
      "status": "active",
      "created": "2025-11-01"
    }
  ]
}
```

**Proxy List Structure** - `proxy-list`:
```json
{
  "proxies": [
    {
      "proxy_id": "proxy_001",
      "url": "http://proxy1.example.com:8080",
      "username": "proxy_user",
      "password": "proxy_pass",
      "status": "active",
      "rotation_count": 0
    },
    {
      "proxy_id": "proxy_002",
      "url": "http://proxy2.example.com:8080",
      "status": "active",
      "rotation_count": 0
    }
  ]
}
```

### Anti-Detection Strategies

**1. Proxy Rotation**:
```python
import random
import time
from datetime import datetime, timedelta

class ProxyManager:
    def __init__(self, proxies):
        self.proxies = proxies
        self.rotation_index = 0
        self.rotation_delay = random.uniform(2, 5)  # 2-5 seconds between rotations

    def get_next_proxy(self):
        """Get next proxy, rotating through available proxies."""
        proxy = self.proxies[self.rotation_index % len(self.proxies)]
        self.rotation_index += 1

        # Add delay between rotations
        time.sleep(self.rotation_delay)

        return {
            'http': proxy['url'],
            'https': proxy['url']
        }

    def format_proxy_url(self, proxy):
        """Format proxy with authentication if needed."""
        if proxy.get('username'):
            return f"http://{proxy['username']}:{proxy['password']}@{proxy['url']}"
        return f"http://{proxy['url']}"
```

**2. User-Agent Rotation**:
```python
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1',
]

def get_random_user_agent():
    return random.choice(USER_AGENTS)
```

**3. Request Timing**:
```python
def add_human_like_delay():
    """Add realistic delay between requests."""
    delay = random.uniform(1, 4)  # 1-4 seconds between requests
    time.sleep(delay)
```

**4. Session Management**:
```python
def create_instagram_session(account, proxy):
    """Create session with account credentials and proxy."""
    session = requests.Session()

    # Set up proxy
    session.proxies = proxy

    # Set headers
    session.headers.update({
        'User-Agent': get_random_user_agent(),
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate',
        'DNT': '1',
    })

    # Attempt login
    login_url = 'https://www.instagram.com/accounts/login/ajax/'

    # Note: Instagram login requires CSRF token and is heavily protected
    # This is a simplified example - actual implementation needs:
    # - CSRF token extraction
    # - Challenge handling
    # - 2FA support (if enabled)
    # - Session validation

    return session
```

### Data Collection Flow

```
1. INITIALIZE Account & Proxy
   ├─ Get next Instagram account from Secrets Manager
   ├─ Rotate proxy from available list
   ├─ Create session with credentials
   ├─ Add random delays and User-Agent
   └─ Validate session is ready

2. GET Celebrity from DynamoDB
   ├─ Extract: name, celebrity_id
   ├─ Try to find Instagram handle
   └─ Validate: handle not empty

3. FETCH Instagram Data
   ├─ Navigate to account profile
   ├─ Extract: follower count, post count, bio
   ├─ Implement request retry with proxy rotation
   ├─ Handle rate limiting (429, 403 responses)
   ├─ Timeout after 20 seconds
   └─ Catch detection blocks (repeat with different proxy)

4. PARSE Response
   ├─ Extract data from profile page
   ├─ Validate required fields present
   ├─ Store complete raw response/HTML
   └─ Check for anti-bot indicators

5. CREATE Scraper Entry (FIRST-HAND)
   ├─ Generate unique ID (UUID)
   ├─ Set ISO 8601 timestamp
   ├─ Populate:
   │  ├─ id (unique UUID)
   │  ├─ name (celebrity name)
   │  ├─ raw_text (complete profile HTML or JSON)
   │  ├─ source (https://www.instagram.com)
   │  └─ timestamp
   ├─ Initialize: weight = null, sentiment = null
   └─ Add metadata (account used, proxy used)

6. WRITE to DynamoDB
   ├─ Key: celebrity_id + instagram#timestamp
   ├─ Exponential backoff on failure
   └─ Log result

7. RETURN Status
   ├─ Success: {status: 'success', account_used: account_id}
   └─ Error: {status: 'error', error: message}
```

### Implementation Example

```python
import boto3
import requests
from botocore.exceptions import ClientError
import json
import uuid
from datetime import datetime
import random
import time

secrets_client = boto3.client('secretsmanager')
dynamodb = boto3.resource('dynamodb')

class InstagramScraper:
    def __init__(self):
        self.accounts = self.load_accounts()
        self.proxies = self.load_proxies()
        self.account_index = 0
        self.proxy_index = 0

    def load_accounts(self):
        """Load Instagram accounts from Secrets Manager."""
        try:
            secret = secrets_client.get_secret_value(
                SecretId=os.environ['INSTAGRAM_ACCOUNTS_SECRET_ARN']
            )
            return json.loads(secret['SecretString'])['accounts']
        except ClientError as e:
            print(f"ERROR loading Instagram accounts: {str(e)}")
            return []

    def load_proxies(self):
        """Load proxy list from Secrets Manager."""
        try:
            secret = secrets_client.get_secret_value(
                SecretId=os.environ['PROXY_LIST_SECRET_ARN']
            )
            return json.loads(secret['SecretString'])['proxies']
        except ClientError as e:
            print(f"ERROR loading proxy list: {str(e)}")
            return []

    def get_next_account(self):
        """Rotate to next Instagram account."""
        account = self.accounts[self.account_index % len(self.accounts)]
        self.account_index += 1
        return account

    def get_next_proxy(self):
        """Rotate to next proxy."""
        proxy = self.proxies[self.proxy_index % len(self.proxies)]
        self.proxy_index += 1
        time.sleep(random.uniform(2, 5))  # Human-like delay
        return proxy

    def scrape_instagram_profile(self, instagram_handle, max_retries=3):
        """
        Scrape Instagram profile data with proxy rotation and retry logic.
        """
        for attempt in range(max_retries):
            try:
                account = self.get_next_account()
                proxy = self.get_next_proxy()

                session = requests.Session()
                session.proxies = {'http': proxy['url'], 'https': proxy['url']}
                session.headers.update({
                    'User-Agent': self.get_random_user_agent(),
                })

                # Fetch profile URL
                url = f"https://www.instagram.com/{instagram_handle}/"
                response = session.get(url, timeout=20)

                if response.status_code == 200:
                    # Extract data from response (simplified)
                    data = self.parse_profile(response.text)
                    return {
                        'success': True,
                        'raw_text': response.text,
                        'data': data,
                        'account_used': account['account_id'],
                        'proxy_used': proxy['proxy_id']
                    }

                elif response.status_code == 429:  # Rate limited
                    print(f"Rate limited (429), attempt {attempt+1}/{max_retries}")
                    time.sleep(random.uniform(5, 10))
                    continue

                elif response.status_code == 403:  # Forbidden (detection)
                    print(f"Detected (403), rotating proxy and account...")
                    time.sleep(random.uniform(10, 15))
                    continue

                else:
                    return {
                        'success': False,
                        'error': f'HTTP {response.status_code}',
                        'raw_text': None
                    }

            except requests.Timeout:
                print(f"Timeout on attempt {attempt+1}/{max_retries}")
                if attempt < max_retries - 1:
                    time.sleep(random.uniform(5, 10))
                continue

            except Exception as e:
                print(f"Exception on attempt {attempt+1}: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(random.uniform(5, 10))
                continue

        return {
            'success': False,
            'error': 'Max retries exceeded',
            'raw_text': None
        }

    def parse_profile(self, html):
        """Extract profile data from Instagram HTML."""
        # Simplified - would use BeautifulSoup or regex in production
        try:
            import re

            # Extract follower count
            follower_match = re.search(r'"edge_followed_by":{"count":(\d+)}', html)
            followers = int(follower_match.group(1)) if follower_match else None

            # Extract post count
            post_match = re.search(r'"edge_owner_to_timeline_media":{"count":(\d+)}', html)
            posts = int(post_match.group(1)) if post_match else None

            return {
                'followers': followers,
                'posts': posts,
                'html_length': len(html)
            }
        except:
            return {'followers': None, 'posts': None}

    def get_random_user_agent(self):
        """Get random User-Agent for request diversity."""
        agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X)',
        ]
        return random.choice(agents)

def lambda_handler(event, context):
    table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])
    scraper = InstagramScraper()

    # Check we have accounts and proxies
    if not scraper.accounts or not scraper.proxies:
        return {
            'error': 'Missing Instagram accounts or proxies',
            'success': 0,
            'errors': 0
        }

    # Get all celebrities
    celebrities = get_all_celebrities(table)

    results = []
    for celeb in celebrities:
        try:
            # Get Instagram handle (would be stored in DynamoDB)
            instagram_handle = extract_instagram_handle(celeb)

            if not instagram_handle:
                results.append({
                    'celebrity_id': celeb['celebrity_id'],
                    'status': 'skipped',
                    'reason': 'No Instagram handle'
                })
                continue

            # Scrape profile with proxy rotation
            scrape_result = scraper.scrape_instagram_profile(instagram_handle)

            if scrape_result['success']:
                # Create scraper entry
                scraper_entry = {
                    'id': str(uuid.uuid4()),
                    'name': celeb['name'],
                    'raw_text': scrape_result['raw_text'],
                    'source': 'https://www.instagram.com',
                    'timestamp': datetime.utcnow().isoformat() + 'Z',
                    'weight': None,
                    'sentiment': None,
                    'metadata': {
                        'account_used': scrape_result.get('account_used'),
                        'proxy_used': scrape_result.get('proxy_used'),
                        'data': scrape_result.get('data')
                    }
                }

                # Write to DynamoDB
                table.put_item(Item={
                    'celebrity_id': celeb['celebrity_id'],
                    'source_type#timestamp': f"instagram#{scraper_entry['timestamp']}",
                    **scraper_entry
                })

                results.append({
                    'celebrity_id': celeb['celebrity_id'],
                    'status': 'success',
                    'account_used': scrape_result.get('account_used')
                })
            else:
                results.append({
                    'celebrity_id': celeb['celebrity_id'],
                    'status': 'error',
                    'error': scrape_result['error']
                })

        except Exception as e:
            results.append({
                'celebrity_id': celeb['celebrity_id'],
                'status': 'error',
                'error': str(e)
            })

    return {
        'total': len(celebrities),
        'success': len([r for r in results if r['status'] == 'success']),
        'errors': len([r for r in results if r['status'] == 'error']),
        'skipped': len([r for r in results if r['status'] == 'skipped']),
        'details': results
    }
```

### Error Handling

**Error**: Detection Block (403 Forbidden)
```
Scenario: Instagram detects suspicious behavior
Handling: Rotate proxy, rotate account, increase delay
Recovery: Retry with fresh proxy and account
Fallback: Skip celebrity, continue with next
Note: This is normal and expected - keep operations "low key"
```

**Error**: Rate Limit (429 Too Many Requests)
```
Scenario: Too many requests from IP/account
Handling: Exponential backoff + proxy rotation
Recovery: Wait 5-15 seconds, retry with new proxy
Fallback: Skip remaining celebrities
```

**Error**: Account Locked
```
Scenario: Instagram locks account due to suspicious activity
Handling: Mark account as inactive in Secrets Manager
Recovery: Switch to different account, notify admin
Fallback: Continue with remaining accounts
```

**Error**: No Instagram Handle
```
Scenario: Celebrity not found or no Instagram profile
Handling: Log warning
Action: Skip celebrity, continue to next
Result: Entry not created
```

**Error**: Timeout or Connection Error
```
Scenario: Network issue or Instagram temporarily unavailable
Handling: Exponential backoff
Recovery: Retry up to 3 times with new proxy
Fallback: Skip celebrity
```

### Scaling with Multiple Accounts

To scale Instagram scraping, add accounts to Secrets Manager:

```bash
# In Secrets Manager, update instagram-accounts secret:
{
  "accounts": [
    {"account_id": "account_001", "username": "account1", "password": "..."},
    {"account_id": "account_002", "username": "account2", "password": "..."},
    {"account_id": "account_003", "username": "account3", "password": "..."},
    {"account_id": "account_004", "username": "account4", "password": "..."},
    {"account_id": "account_005", "username": "account5", "password": "..."}
  ]
}
```

Each Lambda invocation will cycle through accounts automatically, distributing load and reducing detection risk.

### Testing Protocol

**Phase 2.2A: Proxy & Account Setup**

**Step 1: Prepare Instagram Accounts**
```bash
# Create 2-3 dedicated Instagram accounts for scraping
# Account creation checklist:
# - [ ] Account created with valid email
# - [ ] Phone number added (some security)
# - [ ] Username set (avoid obvious bot names)
# - [ ] Profile minimally filled
# - [ ] Account aged 24+ hours before use
# - [ ] 2FA disabled (for automated login)
```

**Step 2: Configure Proxies**
```bash
# Options:
# - Use cloud proxy service (BrightData, Oxylabs, ScraperAPI)
# - Or self-hosted proxy servers
# Recommendation: Start with 3-5 rotating proxies

# Update Secrets Manager:
aws secretsmanager put-secret-value \
  --secret-id proxy-list \
  --secret-string '{
    "proxies": [
      {"proxy_id": "proxy_001", "url": "http://proxy1:8080"},
      {"proxy_id": "proxy_002", "url": "http://proxy2:8080"}
    ]
  }'
```

**Step 3: Store Credentials**
```bash
# Update Secrets Manager:
aws secretsmanager put-secret-value \
  --secret-id instagram-accounts \
  --secret-string '{
    "accounts": [
      {
        "account_id": "account_001",
        "username": "dedicated_scraper_1",
        "password": "ENCRYPTED_PASSWORD",
        "status": "active"
      }
    ]
  }'
```

**Step 4: Test Single Celebrity (Offline)**
```bash
python3 lambda_function.py --test-mode --celebrity "Kylie Jenner"
# Expected: ✓ Function runs without crashes
# Expected: ✓ Proxy rotation works
# Expected: ✓ Account handling works
```

**Step 5: Test with Single Celebrity (Online)**
```bash
aws lambda invoke \
  --function-name scraper-instagram-dev \
  --payload '{"celebrities":[{"celebrity_id":"celeb_001","name":"Taylor Swift"}]}' \
  response.json

cat response.json | jq '.'
# Expected:
# {
#   "success": 1,
#   "errors": 0,
#   "details": [{
#     "status": "success",
#     "account_used": "account_001"
#   }]
# }
```

**Step 6: Verify Data in DynamoDB**
```bash
aws dynamodb query --table-name celebrity-database \
  --key-condition-expression "celebrity_id = :id" \
  --expression-attribute-values "{\":id\":{\"S\":\"celeb_001\"}}" \
  --query 'Items[] | [?begins_with(source_type#timestamp, `instagram`)]'

# Expected: Instagram entry with:
# - raw_text contains HTML/JSON from Instagram
# - source: https://www.instagram.com
# - metadata includes account_used and proxy_used
```

**Step 7: STOP IF ANY ERRORS**
- [ ] Verify account can login successfully
- [ ] Verify proxy is working
- [ ] Check CloudWatch for detection blocks (403 errors)
- [ ] **DO NOT proceed** if getting locked or detected
- [ ] Adjust delays and proxy rotation
- [ ] Re-test with different account

**Phase 2.2B: Batch Testing (5 Celebrities)**

```bash
aws lambda invoke \
  --function-name scraper-instagram-dev \
  --payload '{"limit": 5}' \
  response.json

# Monitor for detection blocks
aws logs tail /aws/lambda/scraper-instagram-dev --follow

# Check if operating "low key"
cat response.json | jq '.details[] | select(.status == "error")'

# If success rate >= 60%, proceed (some failures expected)
```

**Phase 2.2C: Full Deployment (100 Celebrities)**

```bash
aws lambda update-function-code \
  --function-name scraper-instagram \
  --zip-file fileb://function.zip

aws lambda invoke \
  --function-name scraper-instagram \
  --payload '{}' \
  response.json

# Final verification
aws dynamodb scan --table-name celebrity-database \
  --filter-expression "begins_with(#key, :source)" \
  --expression-attribute-names "{\"#key\":\"source_type#timestamp\"}" \
  --expression-attribute-values "{\":source\":{\"S\":\"instagram#\"}}" \
  --select COUNT

# Expected: 60-80 entries (not all celebrities have Instagram)
```

**Important Notes**:
- Instagram actively prevents scraping - accept 10-20% failure rate
- Keep operations minimal and respectful
- Rotate accounts and proxies frequently
- Monitor for account suspensions
- If accounts get locked, create new ones

**Cost Estimate**: ~$10-20/month (proxy service cost)

---

## Stage 2.3: Threads - Account-Based Scraping (Same as Instagram)

### Purpose
Collect Threads account data using similar methodology to Instagram - real account credentials with proxy rotation to collect profile information while avoiding detection.

### Data Source
- **Source**: Threads (Meta's Twitter alternative)
- **Authentication**: Real account credentials (username/password)
- **Data**: Follower count, post count, bio information
- **Rate Limiting**: Similar to Instagram (anti-bot protection)
- **Scaling**: Supports multiple accounts
- **Status**: ⚠️ Similar to Instagram

### Key Differences from Instagram
- Uses same Instagram account credentials (Threads uses Meta accounts)
- API structure is simpler (newer platform)
- Fewer anti-bot measures (but growing)
- More lenient rate limits initially

### Lambda Configuration

**Function Name**: `scraper-threads`
- **Runtime**: Python 3.11
- **Memory**: 1024 MB
- **Timeout**: 10 minutes
- **Trigger**: EventBridge (weekly)

**Environment Variables**: (Same as Instagram)
```bash
INSTAGRAM_ACCOUNTS_SECRET_ARN=arn:aws:secretsmanager:region:account:secret:instagram-accounts
PROXY_LIST_SECRET_ARN=arn:aws:secretsmanager:region:account:secret:proxy-list
DYNAMODB_TABLE=celebrity-database
AWS_REGION=us-east-1
```

### Implementation

**Data Collection Flow** (Identical to Instagram):

```
1. INITIALIZE Account & Proxy
   ├─ Get next account from Secrets Manager
   ├─ Rotate proxy from available list
   ├─ Create session with credentials
   └─ Add random delays and User-Agent

2. FETCH Threads Data
   ├─ Navigate to profile
   ├─ Extract: follower count, post count
   ├─ Retry with proxy rotation on failure
   └─ Timeout after 20 seconds

3. CREATE Scraper Entry (FIRST-HAND)
   ├─ id, name, raw_text, source, timestamp
   └─ weight = null, sentiment = null

4. WRITE to DynamoDB
   └─ Key: celebrity_id + threads#timestamp

5. RETURN Status
   └─ Success/Error with account used
```

### Code Example

```python
import requests
import random
import time
from datetime import datetime
import uuid

class ThreadsScraper:
    def __init__(self, accounts, proxies):
        self.accounts = accounts
        self.proxies = proxies
        self.account_index = 0
        self.proxy_index = 0

    def scrape_threads_profile(self, threads_handle, max_retries=3):
        """
        Scrape Threads profile with proxy rotation.
        Threads URL pattern: threads.net/@{handle}
        """
        for attempt in range(max_retries):
            try:
                account = self.accounts[self.account_index % len(self.accounts)]
                proxy = self.proxies[self.proxy_index % len(self.proxies)]
                self.proxy_index += 1

                session = requests.Session()
                session.proxies = {'http': proxy['url'], 'https': proxy['url']}
                session.headers.update({
                    'User-Agent': self.get_random_user_agent(),
                })

                # Threads profile endpoint
                url = f"https://www.threads.net/@{threads_handle}/"
                response = session.get(url, timeout=20)

                if response.status_code == 200:
                    data = self.parse_threads_profile(response.text)
                    return {
                        'success': True,
                        'raw_text': response.text,
                        'data': data,
                        'account_used': account['account_id']
                    }

                elif response.status_code == 429:
                    print(f"Rate limited (429), retrying...")
                    time.sleep(random.uniform(5, 10))
                    continue

                else:
                    return {
                        'success': False,
                        'error': f'HTTP {response.status_code}',
                        'raw_text': None
                    }

            except Exception as e:
                print(f"Exception: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(random.uniform(5, 10))
                continue

        return {
            'success': False,
            'error': 'Max retries exceeded',
            'raw_text': None
        }

    def parse_threads_profile(self, html):
        """Extract profile data from Threads HTML."""
        import re
        try:
            follower_match = re.search(r'"edge_followed_by":{"count":(\d+)}', html)
            followers = int(follower_match.group(1)) if follower_match else None

            post_match = re.search(r'"edge_owner_to_timeline_media":{"count":(\d+)}', html)
            posts = int(post_match.group(1)) if post_match else None

            return {'followers': followers, 'posts': posts}
        except:
            return {'followers': None, 'posts': None}

    def get_random_user_agent(self):
        agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        ]
        return random.choice(agents)

def lambda_handler(event, context):
    # Same pattern as Instagram scraper
    # Get accounts and proxies
    # Iterate through celebrities
    # Scrape Threads data with proxy rotation
    # Write to DynamoDB with threads#timestamp
    pass
```

### Testing Protocol

**Phase 2.3A: Basic Setup**

```bash
# Verify accounts are set up (same accounts as Instagram)
# Verify proxies are working

# Test single celebrity
aws lambda invoke \
  --function-name scraper-threads-dev \
  --payload '{"celebrities":[{"celebrity_id":"celeb_002","name":"Taylor Swift"}]}' \
  response.json

# Expected: Success with threads data
```

**Phase 2.3B: Verify Data Structure**

```bash
aws dynamodb query --table-name celebrity-database \
  --key-condition-expression "celebrity_id = :id" \
  --expression-attribute-values "{\":id\":{\"S\":\"celeb_002\"}}" \
  --query 'Items[] | [?begins_with(source_type#timestamp, `threads`)]'

# Expected: threads entry with raw_text containing profile HTML
```

**Phase 2.3C: Full Deployment**

```bash
aws lambda update-function-code \
  --function-name scraper-threads \
  --zip-file fileb://function.zip

aws lambda invoke \
  --function-name scraper-threads \
  --payload '{}' \
  response.json

# Verify results
aws dynamodb scan --table-name celebrity-database \
  --filter-expression "begins_with(#key, :source)" \
  --expression-attribute-names "{\"#key\":\"source_type#timestamp\"}" \
  --expression-attribute-values "{\":source\":{\"S\":\"threads#\"}}" \
  --select COUNT
```

**Cost Estimate**: ~$10-20/month (shared proxy costs with Instagram)

---

## Stage 2.4: YouTube API - Official API Integration

### Purpose
Collect YouTube channel and video data using the official YouTube Data API for reliable, authorized data collection.

### Data Source
- **Source**: YouTube Data API v3
- **API Tier**: Free tier (10,000 quota units/day)
- **Data**: Channel subscribers, video count, view count, upload stats
- **Rate Limiting**: Quota-based (generous free tier)
- **Status**: ✅ Production Ready

### Lambda Configuration

**Function Name**: `scraper-youtube`
- **Runtime**: Python 3.11
- **Memory**: 512 MB
- **Timeout**: 5 minutes
- **Trigger**: EventBridge (weekly)

**Environment Variables**:
```bash
YOUTUBE_API_KEY=your_api_key_here
DYNAMODB_TABLE=celebrity-database
AWS_REGION=us-east-1
LOG_LEVEL=INFO
YOUTUBE_TIMEOUT=10
```

### Data Collection Flow

```
1. GET Celebrity from DynamoDB
   ├─ Extract: name, celebrity_id
   ├─ Get YouTube channel handle (if stored)
   └─ Validate: handle not empty

2. SEARCH YouTube API
   ├─ Use /search endpoint with celebrity name
   ├─ Filter for channels
   ├─ Get channel ID from results
   └─ Timeout after 10 seconds

3. FETCH Channel Data
   ├─ Use /channels endpoint
   ├─ Get: subscriber count, view count, video count
   ├─ Get: upload playlist ID
   ├─ Get: latest upload date
   └─ Handle rate limiting

4. PARSE Response
   ├─ Validate JSON response format
   ├─ Extract required fields
   ├─ Store complete raw response
   └─ Check for API errors

5. CREATE Scraper Entry (FIRST-HAND)
   ├─ id, name, raw_text, source, timestamp
   ├─ raw_text contains complete API response
   └─ weight = null, sentiment = null

6. WRITE to DynamoDB
   └─ Key: celebrity_id + youtube#timestamp

7. RETURN Status
   ├─ Success: {status: 'success', video_count: X}
   └─ Error: {status: 'error', error: message}
```

### Implementation Example

```python
import requests
import json
import uuid
from datetime import datetime

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"

def search_youtube_channel(celebrity_name, api_key):
    """
    Search for celebrity YouTube channel.
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
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()

        if data.get('items') and len(data['items']) > 0:
            channel_id = data['items'][0]['id']['channelId']
            return {'channel_id': channel_id, 'error': None}
        else:
            return {'channel_id': None, 'error': 'Channel not found'}

    except requests.Timeout:
        return {'channel_id': None, 'error': 'API timeout'}
    except Exception as e:
        return {'channel_id': None, 'error': str(e)}

def fetch_channel_data(channel_id, api_key):
    """
    Fetch detailed channel information.
    """
    url = f"{YOUTUBE_API_BASE}/channels"
    params = {
        'id': channel_id,
        'part': 'snippet,statistics,contentDetails',
        'key': api_key
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        return {
            'success': True,
            'raw_text': json.dumps(data),
            'channel_data': data.get('items', [{}])[0]
        }

    except requests.HTTPError as e:
        return {
            'success': False,
            'error': f'HTTP {e.response.status_code}',
            'raw_text': None
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'raw_text': None
        }

def lambda_handler(event, context):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])

    api_key = os.environ['YOUTUBE_API_KEY']

    # Get all celebrities
    celebrities = get_all_celebrities(table)

    results = []
    for celeb in celebrities:
        try:
            # Search for YouTube channel
            search_result = search_youtube_channel(celeb['name'], api_key)

            if not search_result['channel_id']:
                results.append({
                    'celebrity_id': celeb['celebrity_id'],
                    'status': 'not_found',
                    'error': search_result['error']
                })
                continue

            # Fetch channel data
            channel_result = fetch_channel_data(search_result['channel_id'], api_key)

            if channel_result['success']:
                # Create scraper entry (FIRST-HAND)
                scraper_entry = {
                    'id': str(uuid.uuid4()),
                    'name': celeb['name'],
                    'raw_text': channel_result['raw_text'],
                    'source': 'https://www.googleapis.com/youtube/v3/channels',
                    'timestamp': datetime.utcnow().isoformat() + 'Z',
                    'weight': None,
                    'sentiment': None
                }

                # Write to DynamoDB
                table.put_item(Item={
                    'celebrity_id': celeb['celebrity_id'],
                    'source_type#timestamp': f"youtube#{scraper_entry['timestamp']}",
                    **scraper_entry
                })

                # Extract subscriber count for logging
                channel_data = channel_result['channel_data']
                subscriber_count = channel_data.get('statistics', {}).get('subscriberCount', 'hidden')

                results.append({
                    'celebrity_id': celeb['celebrity_id'],
                    'status': 'success',
                    'subscribers': subscriber_count,
                    'channel_id': search_result['channel_id']
                })
            else:
                results.append({
                    'celebrity_id': celeb['celebrity_id'],
                    'status': 'error',
                    'error': channel_result['error']
                })

        except Exception as e:
            results.append({
                'celebrity_id': celeb['celebrity_id'],
                'status': 'error',
                'error': str(e)
            })

    return {
        'total': len(celebrities),
        'success': len([r for r in results if r['status'] == 'success']),
        'errors': len([r for r in results if r['status'] == 'error']),
        'not_found': len([r for r in results if r['status'] == 'not_found']),
        'details': results
    }
```

### Error Handling

**Error**: Channel Not Found (404)
```
Scenario: Celebrity doesn't have YouTube channel
Handling: Log warning, skip celebrity
Action: Continue to next
Result: Entry not created (not an error)
```

**Error**: API Quota Exceeded
```
Scenario: 10,000 daily quota units exceeded
Handling: Check quota usage, log error
Recovery: Wait until quota resets (24 hours)
Fallback: Continue with remaining quota
```

**Error**: Invalid API Key
```
Scenario: API key invalid or expired
Handling: Log error, do not retry
Recovery: Verify key in AWS Secrets Manager
Fallback: Exit scraper
```

### Testing Protocol

**Phase 2.4A: API Key Setup**

```bash
# 1. Visit https://console.cloud.google.com
# 2. Create project "celebrity-database"
# 3. Enable YouTube Data API v3
# 4. Create API key (Credentials > Create API Key)
# 5. Copy API key
```

**Phase 2.4B: Test Single Celebrity**

```bash
aws lambda invoke \
  --function-name scraper-youtube-dev \
  --payload '{"celebrities":[{"celebrity_id":"celeb_003","name":"Kylie Jenner"}]}' \
  response.json

cat response.json | jq '.'
# Expected: Success with subscriber count
```

**Phase 2.4C: Verify Data**

```bash
aws dynamodb query --table-name celebrity-database \
  --key-condition-expression "celebrity_id = :id" \
  --expression-attribute-values "{\":id\":{\"S\":\"celeb_003\"}}" \
  --query 'Items[] | [?begins_with(source_type#timestamp, `youtube`)]'

# Expected: YouTube entry with raw_text containing API response
```

**Phase 2.4D: Full Deployment**

```bash
aws lambda update-function-code \
  --function-name scraper-youtube \
  --zip-file fileb://function.zip

aws lambda invoke \
  --function-name scraper-youtube \
  --payload '{}' \
  response.json

# Final verification
aws dynamodb scan --table-name celebrity-database \
  --filter-expression "begins_with(#key, :source)" \
  --expression-attribute-names "{\"#key\":\"source_type#timestamp\"}" \
  --expression-attribute-values "{\":source\":{\"S\":\"youtube#\"}}" \
  --select COUNT

# Expected: 80-100 entries (most celebrities have YouTube)
```

**Cost Estimate**: Free (within quota limits)

---

## Multi-Stage Lambda Layer & Dependencies

### Common Requirements (All Stages)

**Layer Name**: `celebrity-scrapers-dependencies`
**Python Packages**:
```
requests==2.31.0
boto3==1.28.0
python-dateutil==2.8.2
feedparser==6.0.10
beautifulsoup4==4.12.2
```

**Layer Creation**:
```bash
mkdir -p python
pip install -r requirements.txt -t python/
zip -r layer.zip python/
aws lambda publish-layer-version \
  --layer-name celebrity-scrapers-dependencies \
  --zip-file fileb://layer.zip \
  --compatible-runtimes python3.11
```

### Common IAM Permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:Scan",
        "dynamodb:Query",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem"
      ],
      "Resource": "arn:aws:dynamodb:*:*:table/celebrity-database"
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": [
        "arn:aws:secretsmanager:*:*:secret:instagram-accounts*",
        "arn:aws:secretsmanager:*:*:secret:proxy-list*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

---

## Integration & Multi-Stage Testing

### Phase 2 Integration Testing

After all 4 stages are deployed:

```bash
# Trigger all scrapers simultaneously
for scraper in scraper-google-search scraper-instagram scraper-threads scraper-youtube; do
  aws lambda invoke \
    --function-name $scraper \
    --payload '{"limit": 5}' \
    response-$scraper.json &
done

# Wait for all
wait

# Check results
for scraper in scraper-google-search scraper-instagram scraper-threads scraper-youtube; do
  echo "=== $scraper ==="
  cat response-$scraper.json | jq '.success, .errors'
done
```

### Data Completeness Verification

```bash
# For each celebrity, verify all 4 sources have data
for celeb_id in celeb_001 celeb_002 celeb_003; do
  echo "=== $celeb_id ==="

  aws dynamodb query --table-name celebrity-database \
    --key-condition-expression "celebrity_id = :id" \
    --expression-attribute-values "{\":id\":{\"S\":\"$celeb_id\"}}" \
    --query 'Items[] | [?!begins_with(source_type#timestamp, `master`) | source_type#timestamp | split(`#`)[0]]' | sort | uniq
done

# Expected output for each celebrity:
# google_search
# instagram (or skip if no profile)
# threads (or skip if no profile)
# youtube (or skip if no channel)
```

---

## Fallback & Recovery Strategies

### Stage Temporary Failure
**Scenario**: Stage unavailable for 1 hour
```
Detection: Timeout errors, 503 responses
Response: Exponential backoff up to 5 minutes
Recovery: Skip affected celebrities, continue
Result: Some celebrities missing data for this stage
Next Week: Re-attempt on next scheduled run
```

### Partial Batch Failure
**Scenario**: 80% succeeded, 20% failed
```
Detection: Response summary shows errors
Response: Log details of failed celebrities
Recovery: Proceed if success rate > 70%
Action: Failed celebrities re-attempted next week
```

### Rate Limit Across Stages
**Scenario**: Multiple stages hitting API limits
```
Detection: 429 responses from multiple sources
Response: Stagger stage execution (don't run all at once)
Recovery: Space out by 5-10 minutes
Action: Use EventBridge to trigger staggered
```

---

## File Structure

```
phase-2-scrapers/
├── README.md                           # This file
├── lambda-layers/
│   ├── requirements.txt
│   └── publish-layer.sh
├── scraper-google-search/
│   ├── lambda_function.py
│   ├── requirements.txt
│   ├── test_scraper.py
│   └── .env.template
├── scraper-instagram/
│   ├── lambda_function.py
│   ├── requirements.txt
│   ├── test_scraper.py
│   ├── proxy_manager.py
│   └── .env.template
├── scraper-threads/
│   ├── lambda_function.py
│   ├── requirements.txt
│   ├── test_scraper.py
│   └── .env.template
├── scraper-youtube/
│   ├── lambda_function.py
│   ├── requirements.txt
│   ├── test_scraper.py
│   └── .env.template
├── shared-utilities/
│   ├── dynamodb_helper.py
│   ├── logger_config.py
│   └── retry_handler.py
└── deployment/
    ├── deploy.sh
    └── test-all-stages.sh
```

---

## Timeline & Milestones

**Week 3**: Stage 2.1 - Google Search API
- [ ] Code implementation
- [ ] Testing with 1, 5, then 100 celebrities
- [ ] Validation and debugging

**Week 4**: Stage 2.2 - Instagram Scraper
- [ ] Account & proxy setup
- [ ] Code implementation
- [ ] Testing cycle (watch for detection blocks)
- [ ] Validation

**Week 5**: Stage 2.3 - Threads Scraper
- [ ] Code implementation
- [ ] Testing cycle
- [ ] Validation

**Week 6**: Stage 2.4 - YouTube API
- [ ] Code implementation
- [ ] Testing cycle
- [ ] Validation
- [ ] All 4 stages running in parallel

---

## Current Implementation Status

### ✅ Completed
- [x] Phase 2 restructured into 4 stages
- [x] Stage definitions and architecture documented
- [x] Error handling framework for each stage
- [x] Testing protocol documented
- [x] Code examples provided for each stage

### 🟡 In Progress
- [ ] Deploy Stage 2.1 (Google Search)
- [ ] Test with 1, 5, then 100 celebrities
- [ ] Deploy Stage 2.2 (Instagram)
- [ ] Deploy Stage 2.3 (Threads)
- [ ] Deploy Stage 2.4 (YouTube)

### ⏳ Not Started
- [ ] Phase 3 (Post-Processing)

---

## Coding Principles & Best Practices

### Error Handling
✅ **Implemented**:
- Try-catch blocks for all external API calls
- Specific error handling per error type
- Exponential backoff with jitter for retries
- Circuit breaker pattern (for detection blocks in 2.2/2.3)
- Graceful degradation (continue if 1 celebrity fails)

### Data Validation
✅ **Implemented**:
- Validate response structure before parsing
- Check for required fields in responses
- Validate data types
- Verify timestamp formats (ISO 8601)
- Check for API error messages in responses

### Robustness
✅ **Implemented**:
- Idempotent operations (safe to run multiple times)
- Partial success handling
- Comprehensive logging for debugging
- Health checks before operations
- Timeout protection (no hanging requests)

### Security
✅ **Implemented**:
- API keys in AWS Secrets Manager (not hardcoded)
- HTTPS for all external requests
- User-Agent headers (identify as bot for Stage 2.1/2.4, mimic user for 2.2/2.3)
- No sensitive data in logs
- Secure parameter passing (environment variables)
- Account credentials encrypted in Secrets Manager

### Performance
✅ **Implemented**:
- Connection reuse (single session per scraper)
- Batch operations where possible
- Rate limiting compliance
- Proxy rotation to avoid detection
- Caching (optional, per stage)

---

## References

- Project Plan: `../../project-updated.md`
- Google Search API: https://developers.google.com/custom-search/v1/overview
- Instagram Web: https://www.instagram.com/
- Threads: https://www.threads.net/
- YouTube API: https://developers.google.com/youtube/v3
- AWS Secrets Manager: https://docs.aws.amazon.com/secretsmanager/

---

## Cost Summary

| Stage | Service | Monthly Cost |
|-------|---------|--------------|
| 2.1 | Google Search API | $0-2 |
| 2.2 | Instagram (Proxy) | $10-20 |
| 2.3 | Threads (Proxy) | $5-10 |
| 2.4 | YouTube API | Free |
| **Total Phase 2** | | **~$15-32/month** |

---

**Phase 2 Status**: Ready for Implementation
**Created**: November 7, 2025
**Last Updated**: November 7, 2025
**Version**: 2.0 (Four-Stage Architecture)

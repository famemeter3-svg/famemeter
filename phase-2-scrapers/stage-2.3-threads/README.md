# Stage 2.3: Threads - Account-Based Scraping

## Overview

Stage 2.3 collects Threads account data using similar methodology to Instagram - real account credentials with proxy rotation to collect profile information while avoiding detection. Threads is Meta's Twitter alternative with newer, simpler API structures but growing anti-bot measures.

## Purpose
Collect Threads account data (followers, posts, bio) using real account credentials with proxy rotation while maintaining low-key operations.

## Data Source
- **Source**: Threads (Meta's Twitter alternative)
- **Authentication**: Real account credentials (username/password)
- **Data**: Follower count, post count, bio information
- **Rate Limiting**: Similar to Instagram (anti-bot protection)
- **Scaling**: Supports multiple accounts
- **Status**: ⚠️ Similar to Instagram

## Key Differences from Instagram
- Uses same Instagram/Meta account credentials
- API structure is simpler (newer platform)
- Fewer anti-bot measures (but growing)
- More lenient rate limits initially
- Lower detection pressure

## Lambda Configuration

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
LOG_LEVEL=INFO
INSTAGRAM_TIMEOUT=20
```

## Data Collection Flow

```
1. INITIALIZE Account & Proxy
   ├─ Get next account from Secrets Manager
   ├─ Rotate proxy from available list
   ├─ Create session with credentials
   └─ Add random delays and User-Agent

2. GET Celebrity from DynamoDB
   ├─ Extract: name, celebrity_id
   ├─ Try to find Threads handle
   └─ Validate: handle not empty

3. FETCH Threads Data
   ├─ Navigate to profile
   ├─ Extract: follower count, post count, bio
   ├─ Retry with proxy rotation on failure
   └─ Timeout after 20 seconds

4. PARSE Response
   ├─ Extract data from profile page
   ├─ Validate required fields
   ├─ Store complete raw response/HTML
   └─ Check for anti-bot indicators

5. CREATE Scraper Entry (FIRST-HAND)
   ├─ id, name, raw_text, source, timestamp
   ├─ Initialize: weight = null, sentiment = null
   └─ Add metadata (account used, proxy used)

6. WRITE to DynamoDB
   └─ Key: celebrity_id + threads#timestamp

7. RETURN Status
   └─ Success/Error with account used
```

## Implementation

### Main Lambda Handler

```python
import requests
import random
import time
from datetime import datetime
import uuid
import json
import os
import boto3
from botocore.exceptions import ClientError

secrets_client = boto3.client('secretsmanager')
dynamodb = boto3.resource('dynamodb')

class ThreadsScraper:
    def __init__(self):
        self.accounts = self.load_accounts()
        self.proxies = self.load_proxies()
        self.account_index = 0
        self.proxy_index = 0

    def load_accounts(self):
        """Load accounts from Secrets Manager."""
        try:
            secret = secrets_client.get_secret_value(
                SecretId=os.environ['INSTAGRAM_ACCOUNTS_SECRET_ARN']
            )
            return json.loads(secret['SecretString'])['accounts']
        except ClientError as e:
            print(f"ERROR loading accounts: {str(e)}")
            return []

    def load_proxies(self):
        """Load proxy list from Secrets Manager."""
        try:
            secret = secrets_client.get_secret_value(
                SecretId=os.environ['PROXY_LIST_SECRET_ARN']
            )
            return json.loads(secret['SecretString'])['proxies']
        except ClientError as e:
            print(f"ERROR loading proxies: {str(e)}")
            return []

    def scrape_threads_profile(self, threads_handle, max_retries=3):
        """Scrape Threads profile with proxy rotation."""
        for attempt in range(max_retries):
            try:
                account = self.get_next_account()
                proxy = self.get_next_proxy()

                session = requests.Session()
                session.proxies = {'http': proxy['url'], 'https': proxy['url']}
                session.headers.update({
                    'User-Agent': self.get_random_user_agent(),
                })

                # Threads profile endpoint: threads.net/@{handle}
                url = f"https://www.threads.net/@{threads_handle}/"
                response = session.get(url, timeout=20)

                if response.status_code == 200:
                    data = self.parse_threads_profile(response.text)
                    return {
                        'success': True,
                        'raw_text': response.text,
                        'data': data,
                        'account_used': account['account_id'],
                        'proxy_used': proxy['proxy_id']
                    }

                elif response.status_code == 429:
                    print(f"Rate limited (429), attempt {attempt+1}/{max_retries}")
                    time.sleep(random.uniform(5, 10))
                    continue

                elif response.status_code == 403:
                    print(f"Detected (403), rotating...")
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

    def get_next_account(self):
        account = self.accounts[self.account_index % len(self.accounts)]
        self.account_index += 1
        return account

    def get_next_proxy(self):
        proxy = self.proxies[self.proxy_index % len(self.proxies)]
        self.proxy_index += 1
        time.sleep(random.uniform(2, 5))
        return proxy

    def get_random_user_agent(self):
        agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        ]
        return random.choice(agents)

def lambda_handler(event, context):
    table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])
    scraper = ThreadsScraper()

    if not scraper.accounts or not scraper.proxies:
        return {
            'error': 'Missing accounts or proxies',
            'success': 0,
            'errors': 0
        }

    celebrities = get_all_celebrities(table)

    results = []
    for celeb in celebrities:
        try:
            threads_handle = extract_threads_handle(celeb)

            if not threads_handle:
                results.append({
                    'celebrity_id': celeb['celebrity_id'],
                    'status': 'skipped',
                    'reason': 'No Threads handle'
                })
                continue

            scrape_result = scraper.scrape_threads_profile(threads_handle)

            if scrape_result['success']:
                scraper_entry = {
                    'id': str(uuid.uuid4()),
                    'name': celeb['name'],
                    'raw_text': scrape_result['raw_text'],
                    'source': 'https://www.threads.net',
                    'timestamp': datetime.utcnow().isoformat() + 'Z',
                    'weight': None,
                    'sentiment': None,
                    'metadata': {
                        'account_used': scrape_result.get('account_used'),
                        'proxy_used': scrape_result.get('proxy_used'),
                        'data': scrape_result.get('data')
                    }
                }

                table.put_item(Item={
                    'celebrity_id': celeb['celebrity_id'],
                    'source_type#timestamp': f"threads#{scraper_entry['timestamp']}",
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

## Error Handling

| Error | Scenario | Handling | Recovery | Fallback |
|-------|----------|----------|----------|----------|
| **Rate Limit (429)** | Too many requests | Exponential backoff | Wait 5-10s, retry | Skip |
| **Detection (403)** | Suspicious behavior | Rotate proxy | Retry with new proxy | Skip |
| **Timeout** | Connection timeout | Retry with backoff | Try 3 times | Skip |
| **No Handle** | Celebrity missing | Log skip | None | Continue |

## Testing Protocol

### Phase 2.3A: Basic Setup

```bash
# Verify accounts are set up (same as Instagram)
# Verify proxies are working

# Test single celebrity
aws lambda invoke \
  --function-name scraper-threads-dev \
  --payload '{"celebrities":[{"celebrity_id":"celeb_002","name":"Taylor Swift"}]}' \
  response.json

# Expected: Success with threads data
```

### Phase 2.3B: Verify Data Structure

```bash
aws dynamodb query --table-name celebrity-database \
  --key-condition-expression "celebrity_id = :id" \
  --expression-attribute-values "{\":id\":{\"S\":\"celeb_002\"}}" \
  --query 'Items[] | [?begins_with(source_type#timestamp, `threads`)]'

# Expected: threads entry with raw_text containing profile HTML
```

### Phase 2.3C: Batch Testing

```bash
aws lambda invoke \
  --function-name scraper-threads-dev \
  --payload '{"limit": 5}' \
  response.json

# If success rate >= 70%, proceed to deployment
```

### Phase 2.3D: Full Deployment

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

# Expected: 50-80 entries
```

## File Structure

```
stage-2.3-threads/
├── README.md                 # This file
├── lambda_function.py        # Main scraper code
├── requirements.txt          # Dependencies
├── test_scraper.py          # Testing script
└── .env.template            # Environment template
```

## Dependencies

```
requests==2.31.0
boto3==1.28.0
beautifulsoup4==4.12.2
```

## Cost Estimate

- **Proxy Service**: $5-10/month (shared with Instagram)

**Total: $5-10/month**

## Timeline

**Week 5**:
- [ ] Code implementation
- [ ] Testing cycle
- [ ] Validation

## Status

- ✅ Architecture documented
- ⏳ Implementation pending
- ⏳ Testing pending

---

**Created**: November 7, 2025
**Version**: 1.0
**Status**: Ready for Implementation

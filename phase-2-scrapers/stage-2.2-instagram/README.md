# Stage 2.2: Instagram - Account-Based Scraping with Proxy Rotation

## Overview

Stage 2.2 collects Instagram account data by using dedicated accounts with real credentials to mimic user behavior and gather information while avoiding detection through proxy rotation. This stage requires careful implementation and respectful operation.

## Purpose
Collect Instagram account data (followers, posts, bio) using real account credentials with proxy rotation to avoid detection while maintaining low-key operations.

## Data Source
- **Source**: Instagram Web (via account login with proxy)
- **Authentication**: Real account credentials (username/password)
- **Data**: Follower count, post count, bio information, engagement metrics
- **Rate Limiting**: Variable by Instagram's anti-bot detection
- **Scaling**: Supports multiple accounts provided
- **Status**: ⚠️ Requires Careful Implementation (Anti-Detection)

## Key Features
- Real account authentication for accurate data collection
- **Proxy rotation** to avoid IP-based detection
- **User-Agent rotation** for request diversity
- Graceful handling of rate limiting and detection blocks
- **Scalable**: Can add more accounts to increase throughput
- **Low-key operation**: Minimal footprint, respectful of platform

## Lambda Configuration

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

## Credentials Management

### Instagram Accounts (Secrets Manager)

**Secret Name**: `instagram-accounts`

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

### Proxy List (Secrets Manager)

**Secret Name**: `proxy-list`

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

## Anti-Detection Strategies

### 1. Proxy Rotation

```python
import random
import time

class ProxyManager:
    def __init__(self, proxies):
        self.proxies = proxies
        self.rotation_index = 0
        self.rotation_delay = random.uniform(2, 5)

    def get_next_proxy(self):
        """Get next proxy, rotating through available proxies."""
        proxy = self.proxies[self.rotation_index % len(self.proxies)]
        self.rotation_index += 1
        time.sleep(self.rotation_delay)
        return {
            'http': proxy['url'],
            'https': proxy['url']
        }
```

### 2. User-Agent Rotation

```python
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X)',
]

def get_random_user_agent():
    return random.choice(USER_AGENTS)
```

### 3. Request Timing

```python
def add_human_like_delay():
    """Add realistic delay between requests."""
    delay = random.uniform(1, 4)  # 1-4 seconds
    time.sleep(delay)
```

## Data Collection Flow

```
1. INITIALIZE Account & Proxy
   ├─ Get next Instagram account from Secrets Manager
   ├─ Rotate proxy from available list
   ├─ Create session with credentials
   └─ Add random delays and User-Agent

2. GET Celebrity from DynamoDB
   ├─ Extract: name, celebrity_id
   ├─ Try to find Instagram handle
   └─ Validate: handle not empty

3. FETCH Instagram Data
   ├─ Navigate to account profile
   ├─ Extract: follower count, post count, bio
   ├─ Implement request retry with proxy rotation
   ├─ Handle rate limiting (429, 403 responses)
   └─ Catch detection blocks (repeat with different proxy)

4. PARSE Response
   ├─ Extract data from profile page
   ├─ Validate required fields present
   ├─ Store complete raw response/HTML
   └─ Check for anti-bot indicators

5. CREATE Scraper Entry (FIRST-HAND)
   ├─ Generate unique ID (UUID)
   ├─ Set ISO 8601 timestamp
   ├─ Populate: id, name, raw_text, source, timestamp
   ├─ Initialize: weight = null, sentiment = null
   └─ Add metadata (account used, proxy used)

6. WRITE to DynamoDB
   └─ Key: celebrity_id + instagram#timestamp

7. RETURN Status
   └─ Success/Error with account used
```

## Implementation Example

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

    def scrape_instagram_profile(self, instagram_handle, max_retries=3):
        """Scrape Instagram profile with proxy rotation and retry logic."""
        for attempt in range(max_retries):
            try:
                account = self.get_next_account()
                proxy = self.get_next_proxy()

                session = requests.Session()
                session.proxies = {'http': proxy['url'], 'https': proxy['url']}
                session.headers.update({
                    'User-Agent': self.get_random_user_agent(),
                })

                url = f"https://www.instagram.com/{instagram_handle}/"
                response = session.get(url, timeout=20)

                if response.status_code == 200:
                    data = self.parse_profile(response.text)
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
                    print(f"Detected (403), rotating proxy...")
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
            'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X)',
        ]
        return random.choice(agents)

    def parse_profile(self, html):
        """Extract profile data from Instagram HTML."""
        import re
        try:
            follower_match = re.search(r'"edge_followed_by":{"count":(\d+)}', html)
            followers = int(follower_match.group(1)) if follower_match else None

            post_match = re.search(r'"edge_owner_to_timeline_media":{"count":(\d+)}', html)
            posts = int(post_match.group(1)) if post_match else None

            return {
                'followers': followers,
                'posts': posts,
                'html_length': len(html)
            }
        except:
            return {'followers': None, 'posts': None}
```

## Error Handling

| Error | Scenario | Handling | Recovery | Fallback |
|-------|----------|----------|----------|----------|
| **Detection (403)** | Suspicious behavior | Rotate proxy & account | Retry with fresh proxy | Skip celebrity |
| **Rate Limit (429)** | Too many requests | Exponential backoff | Wait 5-15s, retry | Skip remaining |
| **Account Locked** | Suspicious activity | Mark as inactive | Switch to different | Continue |
| **No Handle** | Celebrity has no Instagram | Log warning | None | Skip celebrity |
| **Timeout** | Network issue | Exponential backoff | Retry 3x with proxy | Skip celebrity |

## Scaling with Multiple Accounts

To increase throughput, add accounts to Secrets Manager:

```bash
# Update secret with multiple accounts
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

Each Lambda will cycle through accounts, distributing load and reducing detection risk.

## Testing Protocol

### Phase 2.2A: Account & Proxy Setup

**Step 1: Prepare Instagram Accounts**
```bash
# Create 2-3 dedicated Instagram accounts
# Checklist:
# - [ ] Account created with valid email
# - [ ] Phone number added
# - [ ] Username set (avoid obvious bot names)
# - [ ] Profile minimally filled
# - [ ] Account aged 24+ hours
# - [ ] 2FA disabled
```

**Step 2: Configure Proxies**
```bash
# Use cloud proxy service (BrightData, Oxylabs, ScraperAPI)
# Start with 3-5 rotating proxies

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
aws secretsmanager put-secret-value \
  --secret-id instagram-accounts \
  --secret-string '{
    "accounts": [
      {
        "account_id": "account_001",
        "username": "dedicated_scraper_1",
        "password": "PASSWORD",
        "status": "active"
      }
    ]
  }'
```

### Phase 2.2B: Test Single Celebrity (Online)

```bash
aws lambda invoke \
  --function-name scraper-instagram-dev \
  --payload '{"celebrities":[{"celebrity_id":"celeb_001","name":"Taylor Swift"}]}' \
  response.json

cat response.json | jq '.'
# Expected: success with account_used
```

### Phase 2.2C: Verify Data in DynamoDB

```bash
aws dynamodb query --table-name celebrity-database \
  --key-condition-expression "celebrity_id = :id" \
  --expression-attribute-values "{\":id\":{\"S\":\"celeb_001\"}}" \
  --query 'Items[] | [?begins_with(source_type#timestamp, `instagram`)]'

# Expected: Instagram entry with:
# - raw_text contains HTML from Instagram
# - metadata includes account_used and proxy_used
```

### Phase 2.2D: Batch Testing (5 Celebrities)

```bash
aws lambda invoke \
  --function-name scraper-instagram-dev \
  --payload '{"limit": 5}' \
  response.json

# Check for detection blocks
aws logs tail /aws/lambda/scraper-instagram-dev --follow

# If success rate >= 60%, proceed (some failures expected)
```

### Phase 2.2E: Full Deployment (100 Celebrities)

```bash
aws lambda update-function-code \
  --function-name scraper-instagram \
  --zip-file fileb://function.zip

aws lambda invoke \
  --function-name scraper-instagram \
  --payload '{}' \
  response.json

# Verify count
aws dynamodb scan --table-name celebrity-database \
  --filter-expression "begins_with(#key, :source)" \
  --expression-attribute-names "{\"#key\":\"source_type#timestamp\"}" \
  --expression-attribute-values "{\":source\":{\"S\":\"instagram#\"}}" \
  --select COUNT

# Expected: 60-80 entries (not all celebrities have Instagram)
```

## Important Notes

- Instagram actively prevents scraping - expect 10-20% failure rate
- Keep operations minimal and respectful
- Rotate accounts and proxies frequently
- Monitor for account suspensions
- If accounts locked, create new ones
- Always maintain "low key" operation

## File Structure

```
stage-2.2-instagram/
├── README.md                 # This file
├── lambda_function.py        # Main scraper code
├── proxy_manager.py         # Proxy rotation utility
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

- **Proxy Service**: $10-20/month (depending on provider)

**Total: $10-20/month**

## Timeline

**Week 4**:
- [ ] Account & proxy setup
- [ ] Code implementation
- [ ] Testing cycle (watch for detection)
- [ ] Validation

## Status

- ✅ Architecture documented
- ⏳ Implementation pending
- ⏳ Testing pending

---

**Created**: November 7, 2025
**Version**: 1.0
**Status**: Ready for Implementation

# V_Central Codebase Comprehensive Architecture Analysis

**Analyzed Date**: November 9, 2025  
**Repository**: /Users/howard/Desktop/VS code file/V_central  
**Status**: Phase 1 Complete, Phase 2 In Progress (4-stage pipeline), Phases 3-8 Pending

---

## EXECUTIVE SUMMARY

The V_Central project is a sophisticated **serverless, event-driven celebrity multi-source database system** built on AWS. It automatically collects data from 4+ sources, computes confidence scores and sentiment analysis, and serves the data via REST API with a React dashboard. The system is designed for ultra-low cost (~$4-6/month) and automated weekly execution.

**Key Statistics**:
- 8 independent development phases
- 100 celebrities × 100+ data points each
- 4-stage scraper pipeline (Google, Instagram, Threads, YouTube)
- Comprehensive testing infrastructure (unit, integration, local, load testing)
- Complete infrastructure-as-code with AWS SAM templates
- Production-ready deployment patterns with validation scripts

---

## 1. MAIN COMPONENTS & RESPONSIBILITIES (Phase 2 - Scrapers)

### Overview of Phase 2 Architecture

Phase 2 is organized as a **four-stage pipeline**, each independently deployable and testable:

```
EventBridge (Weekly Trigger)
        ↓
    ┌───┴────┬─────────┬─────────┐
    ↓        ↓         ↓         ↓
Stage 2.1  Stage 2.2  Stage 2.3  Stage 2.4
Google     Instagram   Threads    YouTube
Search     (Scraper)   (Scraper)   API
 API       (Selenium)  (Selenium)
    │        │         │         │
    └────────┴────┬────┴─────────┘
                  ↓
            DynamoDB
        (First-hand data)
                  ↓
        DynamoDB Streams
                  ↓
        Phase 3: Post-Processor
   (Computes weight & sentiment)
```

### Stage 2.1: Google Search API
**Purpose**: Collect search results and basic information about celebrities

**Characteristics**:
- **Status**: ✅ Production Ready
- **Cost**: $0-2/month
- **Implementation**: Simple API calls with raw text cleaning
- **Success Rate**: ~95-100% (all celebrities have search results)
- **Data Collected**: Search snippets, URLs, metadata
- **Key File**: `phase-2-scrapers/stage-2.1-google-search/lambda_function.py`
- **Error Handling**: Rate limiting, timeout, invalid API key
- **Testing**: Unit tests, integration tests, DynamoDB validation

**Technical Details**:
- Lambda: 512 MB, 5-minute timeout
- Rate limit compliance: Max 10 req/second
- Exponential backoff on failures (1s, 2s, 4s)
- First-hand data stored in `raw_text` field

---

### Stage 2.2: Instagram (LEGACY - DEPRECATED)
**Previous Approach**: Account-based scraping with proxy rotation

**Why Deprecated**:
- Required expensive proxy infrastructure ($50-200/month)
- High complexity with manual proxy/account rotation
- Higher account ban risk
- Lower reliability (~60% success rate)

**Status**: ⚠️ Archived - See MIGRATION_SUMMARY.md for details

---

### Stage 2.3: Instagram (MODERN - PRODUCTION)
**Purpose**: Collect Instagram public profile data using Instaloader

**Characteristics**:
- **Status**: ✅ Production Ready
- **Cost**: $0/month (completely free)
- **Implementation**: Instaloader library (lightweight, actively maintained)
- **Success Rate**: 80%+ (public data access)
- **Data Collected**: Followers, posts, biography, verification status
- **Key File**: `phase-2-scrapers/stage-2.2-instagram/lambda_function.py`
- **Architecture**: Instaloader-based (no aggressive detection needed)

**Key Features**:
- Built-in rate limiting (~200 requests/hour)
- Optional account credentials (works in anonymous mode)
- Graceful error handling for rate limits
- Circuit breaker pattern for rate limiting management
- CloudWatch metrics publishing
- Account rotation support (if credentials provided)

**Important Implementation Details**:
- Uses `instaloader` library (v4.14.2)
- Automatic retry with exponential backoff
- Exception handling for:
  - `ProfileNotExistsException` (log and skip)
  - `TooManyRequestsException` (wait 60s, retry)
  - `LoginRequiredException` (rotate account or use anonymous)
  - `PrivateProfileNotFollowedException` (skip)
- Structured JSON logging with request ID tracking
- CloudWatch metrics: successful_scrapes, failed_scrapes, rate_limited, retry_count

**Testing Infrastructure**:
- Unit tests (30+ test cases with mocks)
- Integration tests (real Instaloader with mocked AWS)
- Local testing with DynamoDB Local (docker-compose)
- Pre-deployment validation script
- Load testing framework
- AWS SAM local invocation support

---

### Stage 2.3: Threads (PRODUCTION)
**Purpose**: Collect Threads (Meta's Twitter alternative) profile data

**Characteristics**:
- **Status**: ✅ Production Ready
- **Cost**: $5-10/month (shared proxy costs with Instagram)
- **Implementation**: Similar to Instagram but for Threads platform
- **Data Collected**: Follower count, post count, bio, engagement

**Key Differences from Instagram**:
- Uses Threads API structure (simpler than Instagram)
- Fewer anti-bot measures (newer platform)
- Same account credentials as Instagram (Meta ecosystem)
- More lenient rate limits initially

**Lambda Configuration**:
- Runtime: Python 3.11
- Memory: 1024 MB
- Timeout: 10 minutes
- Trigger: EventBridge (weekly)

---

### Stage 2.4: YouTube API (PRODUCTION)
**Purpose**: Collect YouTube channel and video data using official API

**Characteristics**:
- **Status**: ✅ Production Ready
- **Cost**: Free (within 10,000 quota units/day)
- **Implementation**: Official YouTube Data API v3
- **Success Rate**: 80-100% (most celebrities have YouTube channels)
- **Data Collected**: Subscribers, video count, views, upload stats

**Key Features**:
- Official API (most reliable)
- Quota-based rate limiting (generous free tier)
- No authentication burden
- Comprehensive channel data available

---

## 2. RECENT CHANGES: Stage 2.2 Migration Analysis

### What Changed

The Instagram scraper underwent a major architectural migration on **November 8, 2025**:

### Migration Details

**Old Approach (v1.0 - DEPRECATED)**:
```
Account Credentials + Manual Session Management + Expensive Proxy Rotation
├── Requires 2-5 proxy accounts ($50-200/month)
├── Complex: requests + custom session logic
├── Manual User-Agent rotation
├── Manual request timing delays
├── Higher failure rate: ~60% success
└── Higher ban risk for accounts
```

**New Approach (v3.0 - CURRENT)**:
```
Instaloader Library + Optional Credentials + No Proxy Required
├── Costs: $0/month (open source library)
├── Simple: 4-line profile fetch
├── Built-in rate limiting (automatic ~200 req/hr)
├── Graceful error handling (Instaloader handles)
├── Higher reliability: 80%+ success
└── Low ban risk (defensive approach)
```

### Key Changes Files

| File | Change | Impact |
|------|--------|--------|
| `README.md` | Complete rewrite (835→863 lines) | Now documents Instaloader approach |
| `MIGRATION_SUMMARY.md` | New documentation | Explains old vs new, rationale |
| `lambda_function.py` | Completely rewritten (500+ lines) | Robust Instaloader implementation |
| `requirements.txt` | Simplified | `instaloader==4.14.2` + `boto3` |
| `requirements-dev.txt` | Added | Testing dependencies (pytest, moto, etc.) |
| `example_instaloader.py` | New | Working example code (175 lines) |
| `sam_template.yaml` | Updated | CloudFormation template for deployment |
| `scripts/validate_deployment.py` | New | Pre-deployment validation |
| `scripts/load_test.py` | New | Load testing framework |
| `tests/` | Comprehensive | Unit, integration, local testing |
| `proxy_manager.py` | Deleted | No longer needed |

### Cost Impact

```
Before Migration:
- Instaloader approach: $0/month
- Proxy service: $50-200/month
- TOTAL: $50-200/month

After Migration:
- Instaloader approach: $0/month
- Proxy service: $0/month (not needed)
- TOTAL: $0/month

Savings: 100% reduction in proxy infrastructure costs
```

### Success Rate Impact

```
Before: ~60% (accounts get flagged, proxies block, aggressive detection triggers)
After:  80%+ (defensive approach maintains sustainable access)
Improvement: +33% better success rate
```

### Differences from Stage 2.4 (YouTube)

| Aspect | Stage 2.3 (Instagram) | Stage 2.4 (YouTube) |
|--------|----------------------|-------------------|
| **API Type** | Web scraping | Official API |
| **Auth Required** | Optional (works anonymously) | API key only |
| **Rate Limiting** | Built-in ~200 req/hr | Quota-based (10k units/day) |
| **Library** | instaloader | requests + urllib |
| **Complexity** | Low | Very low |
| **Cost** | $0/month | Free |
| **Success Rate** | 80%+ | 95%+ |
| **Data Richness** | Medium | High |

---

## 3. TESTING INFRASTRUCTURE

### Unit Testing Framework

**Structure**: `phase-2-scrapers/stage-2.2-instagram/tests/test_scraper.py`

```
30+ test cases covering:
├── InstagramScraper initialization and configuration
├── Profile scraping with retries
├── Error handling (all exception types)
├── Account rotation logic
├── DynamoDB operations
├── CircuitBreaker logic (rate limiting management)
├── MetricsCollector (CloudWatch metrics)
└── Rate limit handling
```

**Tools**: pytest, pytest-cov, pytest-mock

**Coverage Targets**: 80%+ code coverage

**Command**:
```bash
pytest tests/test_scraper.py -v --cov=lambda_function --cov-report=html
```

---

### Integration Testing Framework

**Structure**: `phase-2-scrapers/stage-2.2-instagram/tests/test_integration.py`

```
Full scraping flow with mocked AWS services:
├── Complete scraping flow with DynamoDB
├── Batch celebrity processing
├── Error handling in production scenarios
├── Credentials loading
└── Lambda handler invocation
```

**Tools**: pytest, moto (AWS service mocking), responses (HTTP mocking)

**Command**:
```bash
pytest tests/test_integration.py -v -m integration
```

---

### Local Testing with DynamoDB Local

**Setup**: `phase-2-scrapers/stage-2.2-instagram/tests/local/docker-compose.yaml`

```yaml
version: '3.8'
services:
  dynamodb:
    image: amazon/dynamodb-local:latest
    ports:
      - "8000:8000"
    volumes:
      - ./data:/home/dynamodblocal/data
```

**Process**:
1. Start DynamoDB Local: `docker-compose up -d`
2. Run test: `python tests/local/test_locally.py`
3. View admin UI: `http://localhost:8001`
4. Stop: `docker-compose down`

**What It Tests**:
- Celebrity seeding
- Single celebrity scraping
- Batch processing (4 celebrities)
- Error handling
- Data validation
- DynamoDB schema compliance

---

### Pre-Deployment Validation Script

**File**: `scripts/validate_deployment.py`

**Checks**:
- AWS Credentials present
- DynamoDB table exists
- CloudWatch Logs group exists
- Lambda function permissions
- Secrets Manager access
- Network connectivity

**Usage**:
```bash
python scripts/validate_deployment.py --fix
# Auto-creates missing resources
```

---

### Load Testing Framework

**File**: `scripts/load_test.py`

**Capabilities**:
- Concurrent Lambda invocations
- Progressive load testing
- Performance metrics collection
- Dry-run mode for planning

**Usage**:
```bash
# Simple load test (50 celebrities, 5 parallel invocations)
python scripts/load_test.py

# Custom configuration
python scripts/load_test.py --celebrities 100 --parallel 10

# Progressive load
python scripts/load_test.py --progressive

# Dry run
python scripts/load_test.py --dry-run

# Output:
# ============================================================
# Load Test Summary
# ============================================================
# Total Invocations: 10
# Successful Invocations: 10/10
# Total Duration: 45.32s
# Success Rate: 95.5%
# Throughput: 2.10 celebrities/second
```

---

### AWS SAM Local Testing

**Template**: `sam_template.yaml`

**Features**:
- Complete CloudFormation template
- Lambda function definition
- IAM role with DynamoDB/Secrets permissions
- CloudWatch log group
- CloudWatch dashboard
- CloudWatch alarms (failure rate, rate limiting)

**Commands**:
```bash
# Build the function
sam build

# Deploy locally
sam deploy --guided

# Invoke locally
sam local invoke ScraperFunction --event test-event.json

# Invoke with debugging
sam local invoke ScraperFunction -d 5858 --event test-event.json
```

---

### Other Testing Files

- `test_integration.py` - Integration tests (real Instaloader + mocked AWS)
- `test_scraper.py` - Unit tests (30+ test cases)
- `conftest.py` - pytest fixtures and configuration
- `test_locally.py` - Local DynamoDB testing

---

## 4. DEPLOYMENT INFRASTRUCTURE

### AWS SAM Template Structure

**File**: `phase-2-scrapers/stage-2.2-instagram/sam_template.yaml`

```
AWSTemplateFormatVersion: 2010-09-09
Transform: AWS::Serverless-2016-10-31

Globals:
  Function:
    Timeout: 600          # 10 minutes
    MemorySize: 1024      # 1 GB
    Runtime: python3.13
    Architectures: [x86_64]
    Environment Variables:
      - DYNAMODB_TABLE
      - LOG_LEVEL: INFO
      - INSTAGRAM_TIMEOUT: 30
      - INSTAGRAM_MAX_RETRIES: 3

Resources:
  ScraperLambdaRole:
    - DynamoDB permissions (Scan, Query, PutItem, UpdateItem)
    - Secrets Manager permissions (GetSecretValue)
    - CloudWatch permissions (PutMetricData, Logs)

  ScraperFunction:
    - Handler: lambda_function.lambda_handler
    - EventBridge trigger: Schedule cron(0 2 ? * MON *)
    - Lambda Layer: DependenciesLayer

  DependenciesLayer:
    - CompatibleRuntimes: [python3.13]

  ScraperLogGroup:
    - Retention: 30 days

  ScraperDashboard:
    - Metrics: SuccessfulScrapes, FailedScrapes, RateLimitedCount, ExecutionDuration
    - Widgets: Metrics graph, Error summary

  HighFailureRateAlarm:
    - Threshold: > 30% failure rate
    - Period: 1 hour

  RateLimitAlarm:
    - Threshold: >= 5 rate limit events
    - Period: 1 hour

Outputs:
  - ScraperFunctionArn
  - ScraperFunctionName
  - DynamoDBTableName
  - LogGroupName
  - DashboardUrl
```

---

### Validation Scripts

**File**: `scripts/validate_deployment.py`

```python
def validate():
    checks = {
        'aws_credentials': check_aws_credentials(),
        'dynamodb_table': check_dynamodb_table_exists(),
        'cloudwatch_logs': check_cloudwatch_logs_group(),
        'lambda_permissions': check_lambda_permissions(),
        'secrets_manager': check_secrets_access(),
        'network': check_network_connectivity()
    }
    
    for check, result in checks.items():
        print(f"{'✓' if result else '✗'} {check}")
    
    if not all(checks.values()):
        print("\nMissing resources. Run with --fix to auto-create:")
        # Auto-fix logic
```

---

### Load Testing Script

**File**: `scripts/load_test.py`

```python
Features:
- Concurrent Lambda invocations
- Performance metrics (latency, throughput, success rate)
- Progressive load (gradually increase requests)
- Dry-run mode
- Detailed logging
- CloudWatch metric analysis
```

---

## 5. KEY PATTERNS & CONVENTIONS

### First-Hand Data Pattern (Critical)

All scrapers store complete, unprocessed API responses:

```python
# First-hand data structure
entry = {
    "id": str(uuid.uuid4()),                    # Unique ID
    "name": "Celebrity Name",                   # From API response
    "raw_text": json.dumps(complete_response), # ENTIRE API response
    "source": "https://api.source.com",        # Source URL
    "timestamp": "2025-11-07T17:20:00Z",       # ISO 8601 when scraped
    "weight": None,                             # Computed later
    "sentiment": None                           # Computed later
}

# DynamoDB write pattern
table.put_item(Item={
    "celebrity_id": "celeb_001",
    "source_type#timestamp": f"{source}#{timestamp}",
    **entry
})
```

**Why This Matters**:
- Post-processor (Phase 3) can re-analyze data without re-scraping
- Debugging: Can see exact API response
- Extensibility: New processing algorithms don't require re-scraping
- Data provenance: Can trace where every data point originated

---

### Error Handling Pattern

```python
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger()

# Exponential backoff
def retry_with_backoff(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return func()
        except SpecificException as e:
            if attempt == max_retries - 1:
                logger.error(f"Max retries exceeded: {e}")
                raise
            wait_time = 2 ** attempt
            logger.warning(f"Retry {attempt+1}/{max_retries} after {wait_time}s")
            time.sleep(wait_time)

# Graceful degradation
def scrape_celebrities(celebrities):
    results = []
    for celeb in celebrities:
        try:
            data = scrape_single(celeb)
            results.append({'status': 'success', 'data': data})
        except Exception as e:
            logger.error(f"Failed {celeb['name']}: {e}")
            results.append({'status': 'error', 'error': str(e)})
            # Continue with next celebrity instead of failing batch
            continue
    
    return {
        'total': len(celebrities),
        'success': len([r for r in results if r['status'] == 'success']),
        'errors': len([r for r in results if r['status'] == 'error']),
        'details': results
    }
```

---

### DynamoDB Interaction Pattern

```python
import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('celebrity-database')

# Write entry (first-hand data)
table.put_item(Item={
    'celebrity_id': celeb_id,
    'source_type#timestamp': f'{source}#{timestamp}',
    'id': entry_id,
    'name': name,
    'raw_text': raw_response,
    'source': source_url,
    'timestamp': timestamp,
    'weight': None,
    'sentiment': None
})

# Query by celebrity_id
response = table.query(
    KeyConditionExpression='celebrity_id = :id',
    ExpressionAttributeValues={':id': celeb_id}
)

# Query by name (GSI)
response = table.query(
    IndexName='name-index',
    KeyConditionExpression='name = :name',
    ExpressionAttributeValues={':name': name}
)

# Query by source (GSI)
response = table.query(
    IndexName='source-index',
    KeyConditionExpression='source = :source',
    ExpressionAttributeValues={':source': source_url}
)
```

---

### CloudWatch Metrics Pattern

```python
import boto3

cloudwatch = boto3.client('cloudwatch')

class MetricsCollector:
    def __init__(self, request_id):
        self.request_id = request_id
        self.metrics = {
            'successful_scrapes': 0,
            'failed_scrapes': 0,
            'rate_limited': 0,
            'retry_count': 0
        }
    
    def record_success(self):
        self.metrics['successful_scrapes'] += 1
    
    def record_failure(self, error_type):
        self.metrics['failed_scrapes'] += 1
    
    def publish(self):
        cloudwatch.put_metric_data(
            Namespace='InstagramScraper',
            MetricData=[
                {
                    'MetricName': 'SuccessfulScrapes',
                    'Value': self.metrics['successful_scrapes'],
                    'Unit': 'Count'
                },
                {
                    'MetricName': 'FailedScrapes',
                    'Value': self.metrics['failed_scrapes'],
                    'Unit': 'Count'
                }
            ]
        )
```

---

### Circuit Breaker Pattern (Rate Limiting Management)

```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=300):
        self.failure_threshold = failure_threshold
        self.timeout = timeout  # seconds
        self.failure_count = 0
        self.last_failure_time = None
        self.is_open = False
    
    def record_success(self):
        self.failure_count = 0
        self.is_open = False
    
    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        if self.failure_count >= self.failure_threshold:
            self.is_open = True
            logger.warning(f"Circuit breaker OPEN")
    
    def can_execute(self):
        if not self.is_open:
            return True
        
        elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
        if elapsed > self.timeout:
            self.is_open = False
            self.failure_count = 0
            logger.info("Circuit breaker CLOSED")
            return True
        
        return False

# Usage
breaker = CircuitBreaker(failure_threshold=5, timeout=300)

for celeb in celebrities:
    if not breaker.can_execute():
        logger.warning(f"Circuit breaker OPEN, skipping {celeb}")
        continue
    
    try:
        scrape_result = scrape(celeb)
        breaker.record_success()
    except RateLimitException:
        breaker.record_failure()
```

---

### Structured Logging Pattern

```python
import logging
import json
from datetime import datetime

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

logger = logging.getLogger()
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.handlers = [handler]
logger.setLevel(logging.INFO)

# Usage
logger.info("Processing celebrity", extra={'request_id': request_id})
logger.warning("Rate limited, retrying", extra={'request_id': request_id})
logger.error("Failed to scrape", extra={'request_id': request_id, 'error': str(e)})
```

---

### Account Rotation Pattern

```python
class InstagramScraper:
    def __init__(self, accounts, proxies):
        self.accounts = accounts
        self.proxies = proxies
        self.account_index = 0
        self.proxy_index = 0
    
    def get_next_account(self):
        """Rotate to next account."""
        account = self.accounts[self.account_index % len(self.accounts)]
        self.account_index += 1
        return account
    
    def get_next_proxy(self):
        """Rotate to next proxy."""
        proxy = self.proxies[self.proxy_index % len(self.proxies)]
        self.proxy_index += 1
        time.sleep(random.uniform(2, 5))  # Human-like delay
        return proxy
```

---

## 6. IMPLEMENTATION STATUS BY STAGE

### Stage 2.1: Google Search API

**Status**: ✅ **COMPLETE & PRODUCTION READY**

```
Files:
├── README.md                  ✓ Comprehensive documentation
├── QUICK_START.md            ✓ Setup guide
├── IMPLEMENTATION_SUMMARY.md ✓ Technical details
├── TESTING_REPORT.md         ✓ Test results
├── lambda_function.py        ✓ Full implementation (16KB)
├── requirements.txt          ✓ Dependencies
├── test_scraper.py          ✓ Unit tests
├── test_api_integration.py  ✓ Integration tests
├── validate_dynamodb_integration.py ✓ DynamoDB validation
├── sam_template.yaml        ✓ IaC deployment
├── key_rotation.py          ✓ API key rotation
├── key_rotation_guide.md    ✓ Key management docs
└── parallel_scraper.py      ✓ Parallel execution

Testing:
✓ Unit tests with mocks
✓ Integration tests with DynamoDB
✓ API key rotation tested
✓ Parallel execution tested
✓ DynamoDB schema validation
✓ 90%+ test coverage

Deployment:
✓ SAM template
✓ Deployment scripts
✓ CloudWatch metrics
✓ Error alarms
```

---

### Stage 2.2: Instagram (LEGACY)

**Status**: ⚠️ **DEPRECATED - See 2.3 for modern approach**

```
Reasons for deprecation:
✗ Expensive proxy costs ($50-200/month)
✗ High complexity (manual session management)
✗ Lower reliability (~60% success)
✗ Higher account ban risk

Current files:
├── README.md               - Old proxy-based approach
├── MIGRATION_SUMMARY.md    - Explains migration to 2.3
└── [Old code archived]

Recommendation:
→ Use Stage 2.3 (Instaloader) instead
→ No proxy costs
→ 80%+ reliability
→ Active maintenance
```

---

### Stage 2.3: Instagram (MODERN)

**Status**: ✅ **COMPLETE & PRODUCTION READY**

```
Files:
├── README.md                      ✓ Instaloader documentation
├── MIGRATION_SUMMARY.md           ✓ Migration details
├── ANTI_DETECTION_GUIDE.md        ✓ Anti-detection strategies
├── IMPLEMENTATION_GUIDE.md        ✓ Implementation details
├── MANUAL_LOGIN_GUIDE.md          ✓ Account setup guide
├── lambda_function.py             ✓ Main handler (524 lines)
├── example_instaloader.py         ✓ Working example
├── requirements.txt               ✓ Dependencies (instaloader)
├── requirements-dev.txt           ✓ Testing dependencies
├── sam_template.yaml              ✓ CloudFormation template
├── accounts.json                  ✓ Account credentials (sample)
├── accounts.json.template         ✓ Account template
├── proxies.json.template          ✓ Proxy config (optional)
├── validate_dynamodb_schema.py    ✓ Schema validation
├── .env.template                  ✓ Environment template
├── .env                           ✓ Configuration (local)
└── tests/
    ├── conftest.py               ✓ pytest fixtures
    ├── test_scraper.py           ✓ Unit tests (30+ cases)
    ├── test_integration.py       ✓ Integration tests
    └── local/
        ├── docker-compose.yaml   ✓ DynamoDB Local
        └── test_locally.py       ✓ Local testing
└── scripts/
    ├── validate_deployment.py    ✓ Pre-deployment checks
    └── load_test.py              ✓ Load testing

Implementation Components:
├── InstagramScraper class         - Main orchestrator
├── CircuitBreaker class           - Rate limiting management
├── MetricsCollector class         - CloudWatch metrics
├── Exception handling             - 8 exception types
├── Retry logic                    - Exponential backoff
├── Account rotation               - Optional
├── DynamoDB integration           - Full schema support
└── Structured logging             - JSON format

Testing Coverage:
✓ 30+ unit tests with mocks
✓ Integration tests (real Instaloader + mocked AWS)
✓ Local DynamoDB testing (docker-compose)
✓ Pre-deployment validation
✓ Load testing (concurrent invocations)
✓ AWS SAM local invocation
✓ 80%+ code coverage target

Cost Breakdown:
- Instaloader: $0 (open source)
- AWS Lambda: $1-5/month
- DynamoDB: Included in free tier
- Proxy service: $0 (not required)
TOTAL: $0-5/month (essentially free)

Deployment:
✓ SAM template
✓ CloudWatch dashboard
✓ CloudWatch alarms (failure rate, rate limiting)
✓ Validation scripts
✓ Load testing scripts
✓ Local testing setup
```

---

### Stage 2.4: YouTube API

**Status**: ✅ **COMPLETE & PRODUCTION READY**

```
Files:
├── README.md                  ✓ Documentation
├── QUICK_START.md            ✓ Setup guide
├── IMPLEMENTATION_SUMMARY.md ✓ Technical details
├── TESTING_REPORT.md         ✓ Test results
├── lambda_function.py        ✓ Full implementation (16KB)
├── requirements.txt          ✓ Dependencies
├── test_scraper.py          ✓ Unit tests
├── test_api_integration.py  ✓ Integration tests
├── validate_dynamodb_integration.py ✓ DynamoDB validation
├── sam_template.yaml        ✓ IaC deployment
└── seed_celebrities.py      ✓ Test data seeding

Testing:
✓ Unit tests with mocks
✓ Integration tests with DynamoDB
✓ Channel search tested
✓ Channel data fetch tested
✓ Error handling tested
✓ 85%+ test coverage

Deployment:
✓ SAM template
✓ CloudWatch metrics
✓ Error alarms
```

---

### Stage 2.3: Threads (Production)

**Status**: ✅ **COMPLETE & PRODUCTION READY**

```
Files:
├── README.md          ✓ Documentation
├── lambda_function.py ✓ Implementation
├── requirements.txt   ✓ Dependencies
├── test_scraper.py   ✓ Unit tests
├── sam_template.yaml ✓ Deployment

Architecture:
- Same as Instagram (Instaloader base)
- Threads-specific navigation
- Meta account credentials
```

---

## 7. COMPLETE TESTING ARCHITECTURE

### Testing Pyramid

```
           ╱╲
          ╱  ╲  E2E Tests (10%)
         ╱────╲ (5-10 critical workflows)
        ╱      ╲
       ╱────────╲
      ╱Integration╲ (30%)
     ╱   Tests     ╲ (Phase interactions)
    ╱──────────────╲
   ╱    Unit Tests  ╲ (60%)
  ╱ (Component, func)╲
 ╱─────────────────────╲
```

### Phase 7: Testing & Optimization

**File**: `phase-7-testing/README.md`

**Coverage**:
- ✓ Unit Testing
- ✓ Integration Testing  
- ✓ Performance Testing (DynamoDB, API, Lambda)
- ✓ Data Quality Validation
- ✓ Security Audit
- ✓ Cost Optimization

---

## 8. KEY FILES & LOCATIONS

### Documentation Files

| Location | Purpose | Status |
|----------|---------|--------|
| `README.md` | Project overview | ✓ Complete |
| `project-updated.md` | Complete 1,450+ line spec | ✓ Complete |
| `phase-1-foundation/README.md` | Phase 1 deep dive | ✓ Complete |
| `phase-1-foundation/CLAUDE.md` | Claude Code guidance | ✓ Complete |
| `phase-2-scrapers/README.md` | Phase 2 overview | ✓ Complete |
| `phase-2-scrapers/OVERVIEW.md` | Quick navigation | ✓ Complete |
| `phase-2-scrapers/INDEX.md` | Stage index | ✓ Complete |
| `phase-2-scrapers/DATABASE_INTEGRATION.md` | DynamoDB reference | ✓ Complete |
| `phase-7-testing/README.md` | Testing protocols | ✓ Complete |

### Implementation Files

| Stage | Key Files | Status |
|-------|-----------|--------|
| **2.1** | `stage-2.1-google-search/lambda_function.py` | ✅ Complete |
| **2.2** | `stage-2.2-instagram/MIGRATION_SUMMARY.md` | ⚠️ Deprecated |
| **2.3** | `stage-2.3-instagram/lambda_function.py` | ✅ Complete |
| **2.3** | `stage-2.3-threads/lambda_function.py` | ✅ Complete |
| **2.4** | `stage-2.4-youtube/lambda_function.py` | ✅ Complete |

### SAM Templates

| Stage | Template | Status |
|-------|----------|--------|
| **2.1** | `stage-2.1-google-search/sam_template.yaml` | ✅ |
| **2.3** | `stage-2.2-instagram/sam_template.yaml` | ✅ |
| **2.4** | `stage-2.4-youtube/sam_template.yaml` | ✅ |

---

## 9. CODING PRINCIPLES & BEST PRACTICES

### Error Handling

```
✓ Try-catch blocks for all external API calls
✓ Specific error handling per error type
✓ Exponential backoff with jitter (1s, 2s, 4s, 8s...)
✓ Circuit breaker pattern (for rate limiting)
✓ Graceful degradation (continue if 1 celebrity fails)
✓ Max retry limits (prevent infinite loops)
✓ Structured logging of all errors
✓ CloudWatch alarms for high failure rates
```

### Data Validation

```
✓ Validate response structure before parsing
✓ Check for required fields in responses
✓ Validate data types (string, number, bool)
✓ Verify timestamp formats (ISO 8601)
✓ Check for API error messages in responses
✓ Validate celebrity ID patterns
✓ Ensure raw_text is not null
✓ Verify DynamoDB write succeeded
```

### Robustness

```
✓ Idempotent operations (safe to run multiple times)
✓ Partial success handling (some celebrities may fail)
✓ Comprehensive logging for debugging
✓ Health checks before operations
✓ Timeout protection (no hanging requests)
✓ Connection pooling (reuse sessions)
✓ Memory management (garbage collection)
✓ Database connection cleanup
```

### Security

```
✓ API keys in AWS Secrets Manager (not hardcoded)
✓ Account credentials encrypted
✓ HTTPS for all external requests
✓ User-Agent headers (respect APIs)
✓ No sensitive data in logs
✓ Secure parameter passing (env variables)
✓ IAM roles with least privilege
✓ Encryption at rest (DynamoDB default)
✓ No hard-coded URLs or credentials
```

### Performance

```
✓ Connection reuse (single session per scraper)
✓ Batch operations where possible
✓ Rate limiting compliance
✓ Parallel execution (where applicable)
✓ Query optimization (use GSI)
✓ Timeout configuration per service
✓ Memory allocation based on workload
✓ Lambda layer for shared dependencies
```

---

## 10. DEPLOYMENT CHECKLIST

### Pre-Deployment

- [ ] Read phase README.md thoroughly
- [ ] Verify AWS credentials: `aws sts get-caller-identity`
- [ ] Check DynamoDB table exists: `aws dynamodb describe-table --table-name celebrity-database`
- [ ] Create `.env` file from `.env.template`
- [ ] Install dependencies: `pip3 install -r requirements.txt`
- [ ] Run validation script: `python scripts/validate_deployment.py --fix`
- [ ] Test locally with 1 celebrity: `python lambda_function.py --limit 1`
- [ ] Review CloudWatch logs

### Deployment

- [ ] Package function: `zip -r function.zip .`
- [ ] Deploy using SAM: `sam deploy --stack-name scraper-instagram`
- [ ] Or deploy manually: `aws lambda update-function-code --function-name scraper-instagram --zip-file fileb://function.zip`
- [ ] Set environment variables in Lambda console
- [ ] Configure EventBridge trigger (weekly schedule)

### Post-Deployment

- [ ] Test with AWS Lambda console
- [ ] Check CloudWatch logs
- [ ] Verify DynamoDB entries created
- [ ] Confirm CloudWatch metrics publishing
- [ ] Verify alarms are active
- [ ] Monitor for 1 hour

---

## SUMMARY FOR NEW DEVELOPERS

### Getting Started (10 minutes)

1. **Read the guides** (in order):
   - `README.md` (2 min)
   - `phase-1-foundation/README.md` (5 min)
   - `phase-2-scrapers/README.md` (3 min)

2. **Understand the architecture**:
   - 8 independent phases
   - Each phase self-contained
   - Phase 1 (DynamoDB) must be complete before Phase 2
   - Phase 2 has 4 stages (Google, Instagram, Threads, YouTube)

3. **Verify setup**:
   ```bash
   aws sts get-caller-identity  # Verify AWS credentials
   aws dynamodb describe-table --table-name celebrity-database  # Verify DB
   ```

### Key Concepts

- **First-Hand Data**: Raw API responses stored in `raw_text`, not parsed
- **Partition/Sort Keys**: `celebrity_id` + `source_type#timestamp`
- **Error Handling**: Retry with backoff, skip failed celebrities, continue batch
- **Testing**: Always test 1 → 5 → 100 pattern
- **Deployment**: Use SAM templates for IaC

### Common Commands

```bash
# Create DynamoDB table
cd phase-1-foundation/dynamodb-setup/
python3 create-table.py

# Seed celebrities
cd ../celebrity-seed/
python3 seed-database.py

# Test scraper locally
cd ../../phase-2-scrapers/stage-2.X-{source}/
python3 lambda_function.py --limit 1

# Deploy to AWS
sam deploy --guided
```

---

**Analysis Complete** - November 9, 2025

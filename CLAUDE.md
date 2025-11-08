# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Celebrity Multi-Source Database System** - A serverless, event-driven architecture aggregating celebrity data from 4+ sources (Google Search, Instagram, Threads, YouTube) into DynamoDB, with automatic sentiment analysis, confidence scoring, REST API, and React dashboard.

**Status**: Phase 1 complete. Phase 2 (scrapers) is production-ready with modern implementations. Phases 3-8 pending. Recent major upgrade: Stage 2.2 (Instagram) migrated from expensive proxy-based approach to free Instaloader library (November 8, 2025).

## 8-Phase Architecture

```
Phase 1: Foundation          → DynamoDB table + 100 celebrity seed data (✅ COMPLETE)
Phase 2: Scrapers (4 stages) → Parallel data collection from 4 sources (✅ PRODUCTION-READY)
  ├─ Stage 2.1: Google Search API (✅ DONE)
  ├─ Stage 2.2: Instagram Legacy (⚠️ DEPRECATED, see MIGRATION_SUMMARY.md)
  ├─ Stage 2.3: Instagram Modern + Threads (✅ DONE, Instaloader-based)
  └─ Stage 2.4: YouTube API (✅ DONE)
Phase 3: Post-Processing    → Weight (confidence) & sentiment computation (⏳ PENDING)
Phase 4: Orchestration      → EventBridge + DynamoDB Streams triggering (⏳ PENDING)
Phase 5: API Layer          → REST API endpoints (⏳ PENDING)
Phase 6: Frontend           → React dashboard (⏳ PENDING)
Phase 7: Testing            → E2E tests & performance optimization (⏳ PENDING)
Phase 8: Monitoring         → CloudWatch dashboards & alarms (⏳ PENDING)
```

## Data Model & Architecture

### Central Database: DynamoDB

Table: `celebrity-database`
- **Partition Key**: `celebrity_id` (e.g., "celeb_001")
- **Sort Key**: `source_type#timestamp` (e.g., "instagram#2025-11-07T17:20:00Z")
- **GSI**: `name-index` (query by celebrity name)
- **GSI**: `source-index` (query by data source)
- **Streams**: Enabled (NEW_AND_OLD_IMAGES) for Phase 3 post-processor triggering

### First-Hand Data Pattern

Every scraper entry MUST include:
- `id`: UUID of the entry
- `name`: Celebrity name from source
- `raw_text`: **Complete, unprocessed API response** (JSON/HTML as string)
- `source`: URL of data source
- `timestamp`: ISO 8601 timestamp
- `weight`: None (computed by Phase 3 post-processor)
- `sentiment`: None (computed by Phase 3 post-processor)

**Critical**: Store entire API response in `raw_text` for debugging, re-analysis, and data provenance.

### Integration Flow

```
EventBridge weekly schedule (Sunday 2 AM UTC)
  ↓
All Phase 2 scrapers execute in parallel
  ├─ Stage 2.1: Google Search → queries celebrity + get search results
  ├─ Stage 2.3: Instagram → scrapes profile data via Instaloader
  ├─ Stage 2.3: Threads → scrapes profile data via Instaloader
  └─ Stage 2.4: YouTube → queries YouTube Data API v3
  ↓
All write first-hand data to DynamoDB with complete API responses
  ↓
DynamoDB Streams triggers Phase 3 post-processor
  ↓
Phase 3: Computes weight (confidence) & sentiment on all entries
  ↓
Updated data available via Phase 5 REST API
  ↓
Phase 6 React Frontend displays visualizations
```

## Technology Stack

**AWS**: DynamoDB (On-Demand), Lambda, EventBridge, API Gateway, S3, CloudFront, CloudWatch, Secrets Manager

**Backend**: Python 3.11+, boto3, requests, Instaloader, BeautifulSoup4, TextBlob, pytest, moto

**Frontend**: React 18, React Router, Axios, Tailwind CSS

**External APIs**: Google Custom Search, YouTube Data API v3, Instagram Web (via Instaloader), Threads Web (via Instaloader)

## Directory Structure

```
V_central/
├── README.md                          - Project overview & quick start
├── CLAUDE.md                          - This file
├── .gitignore                         - Git ignore patterns
├── project-updated.md                 - Complete 1,450+ line specification
├── phase-1-foundation/
│   ├── README.md                      - Phase 1 detailed guide
│   ├── dynamodb-setup/
│   │   ├── create-table.py            - Creates main DynamoDB table
│   │   └── test-operations.py         - Validates table structure
│   └── celebrity-seed/
│       ├── celebrities.json           - 100 celebrities seed data
│       └── seed-database.py           - Loads celebrities into DynamoDB
├── phase-2-scrapers/
│   ├── README.md                      - Phase 2 pipeline overview
│   ├── stage-2.1-google-search/       - Google Custom Search (✅ DONE)
│   ├── stage-2.2-instagram/           - Instagram Legacy (⚠️ DEPRECATED)
│   │   ├── README.md                  - Instaloader implementation
│   │   ├── MIGRATION_SUMMARY.md       - Old vs new approach comparison
│   │   ├── lambda_function.py         - Robust scraper (524 lines)
│   │   ├── example_instaloader.py     - Working example code
│   │   ├── sam_template.yaml          - CloudFormation deployment
│   │   ├── requirements.txt           - Dependencies
│   │   ├── requirements-dev.txt       - Testing dependencies
│   │   ├── scripts/
│   │   │   ├── validate_deployment.py - Pre-deployment checks
│   │   │   └── load_test.py           - Performance testing
│   │   └── tests/
│   │       ├── test_scraper.py        - 30+ unit tests
│   │       ├── test_integration.py    - Integration tests
│   │       ├── conftest.py            - Pytest fixtures
│   │       └── local/
│   │           ├── docker-compose.yaml - Local DynamoDB
│   │           └── test_locally.py    - Local testing script
│   ├── stage-2.3-instagram/           - Instagram Modern (✅ PRODUCTION)
│   ├── stage-2.3-threads/             - Threads (✅ PRODUCTION)
│   └── stage-2.4-youtube/             - YouTube API (✅ DONE)
├── phase-3-post-processing/           - Pending
├── phase-4-orchestration/             - Pending
├── phase-5-api/                       - Pending
├── phase-6-frontend/                  - Pending
├── phase-7-testing/                   - Pending
├── phase-8-monitoring/                - Pending
└── shared/
    ├── utils/                         - Common utilities & helpers
    ├── constants/                     - Field definitions & constants
    └── config-templates/
        └── .env.template              - Environment variable template
```

## Essential Commands

### Setup (First Time)

```bash
# Verify AWS credentials
aws sts get-caller-identity

# Create DynamoDB table
cd phase-1-foundation/dynamodb-setup/
python3 create-table.py --region us-east-1

# Seed 100 celebrities
cd ../celebrity-seed/
python3 seed-database.py --region us-east-1
```

### Testing Scrapers Locally

```bash
# Install dependencies
cd phase-2-scrapers/stage-2.X-{source}/
pip3 install -r requirements.txt

# Test with 1 celebrity
python3 lambda_function.py --limit 1

# Test with 10 celebrities
python3 lambda_function.py --limit 10

# Run unit tests
pytest tests/test_scraper.py -v

# Run with coverage
pytest tests/ --cov=lambda_function --cov-report=html
```

### Local Integration Testing (DynamoDB Local)

```bash
# Start local DynamoDB
cd phase-2-scrapers/stage-2.X-{source}/tests/local/
docker-compose up -d

# Run local tests
python test_locally.py

# Stop DynamoDB
docker-compose down
```

### Pre-Deployment Validation

```bash
# Check all AWS prerequisites
python scripts/validate_deployment.py

# Auto-fix missing resources
python scripts/validate_deployment.py --fix
```

### Deploy to AWS

```bash
# Using AWS SAM
sam build
sam deploy --guided
sam deploy --stack-name scraper-instagram --parameter-overrides DynamoDBTableName=celebrity-database

# Or update existing Lambda
aws lambda update-function-code \
  --function-name scraper-instagram \
  --zip-file fileb://function.zip
```

### Load Testing

```bash
# Simple load test (50 celebrities, 5 parallel)
python scripts/load_test.py

# Custom configuration
python scripts/load_test.py --celebrities 100 --parallel 10

# Dry run (show config without executing)
python scripts/load_test.py --dry-run
```

### DynamoDB Queries

```bash
# Count total records
aws dynamodb scan --table-name celebrity-database --select COUNT

# Query specific celebrity
aws dynamodb query --table-name celebrity-database \
  --key-condition-expression "celebrity_id = :id" \
  --expression-attribute-values '{":id":{"S":"celeb_001"}}'

# Query by source (using GSI)
aws dynamodb query --table-name celebrity-database \
  --index-name source-index \
  --key-condition-expression "source = :source" \
  --expression-attribute-values '{":source":{"S":"google"}}'
```

### CloudWatch Logs

```bash
# View Lambda logs
aws logs tail /aws/lambda/scraper-instagram --follow

# Search for errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/scraper-instagram \
  --filter-pattern "ERROR"
```

## Phase 2 Scraper Stages

### Stage 2.1: Google Search API (✅ Production Ready)

**Key Features**:
- Simple API-based approach
- No authentication needed (uses API key)
- Success rate: 95-100%
- Cost: ~$0-2/month
- Implementation: 16KB, straightforward

**How to test**:
```bash
cd phase-2-scrapers/stage-2.1-google-search/
python3 lambda_function.py --limit 1
```

### Stage 2.2: Instagram Legacy (⚠️ Deprecated)

**Status**: Replaced by Stage 2.3 (Instaloader)

**Why it was replaced**:
- Old: Proxy-based approach cost $50-200/month
- New: Free Instaloader library
- Old: 60% success rate
- New: 80%+ success rate
- Detailed comparison: See `MIGRATION_SUMMARY.md`

### Stage 2.3: Instagram Modern (✅ Production Ready)

**Key Features**:
- Uses Instaloader (open-source, actively maintained)
- **Completely free** (no proxy costs)
- Works anonymously or with optional credentials
- Built-in rate limiting (~200 req/hour)
- Graceful error handling
- Success rate: 80%+

**Architecture Highlights**:
- CircuitBreaker pattern (prevents cascading failures)
- Account rotation (if multiple credentials provided)
- Exponential backoff retry logic
- CloudWatch metrics & structured JSON logging
- Comprehensive testing (unit, integration, local, load)

**Testing Infrastructure**:
- 30+ unit tests with mocks
- Integration tests with real Instaloader
- Local DynamoDB testing with docker-compose
- Pre-deployment validation script
- Load testing framework

**How to test**:
```bash
cd phase-2-scrapers/stage-2.2-instagram/  # Note: Stage 2.2 contains Stage 2.3
pip3 install -r requirements.txt
python3 lambda_function.py --limit 1
pytest tests/test_scraper.py -v
```

### Stage 2.4: YouTube API (✅ Production Ready)

**Key Features**:
- Official YouTube Data API v3
- No proxy needed
- Free quota: 10,000 units/day
- Success rate: 80-100%
- Simple implementation

**How to test**:
```bash
cd phase-2-scrapers/stage-2.4-youtube/
python3 lambda_function.py --limit 1
```

## Critical Implementation Patterns

### First-Hand Data Storage

```python
# CORRECT - Store complete API response
entry = {
    "id": str(uuid.uuid4()),
    "name": profile_data["name"],           # From source
    "raw_text": json.dumps(COMPLETE_RESPONSE),  # Entire API response!
    "source": "https://www.instagram.com",
    "timestamp": datetime.utcnow().isoformat(),
    "weight": None,    # Computed later
    "sentiment": None  # Computed later
}
table.put_item(Item=entry)
```

### Error Handling with Exponential Backoff

```python
def retry_with_backoff(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)  # 1s, 2s, 4s

# Graceful degradation: skip failed celebrities, continue batch
for celeb in celebrities:
    try:
        scrape_celebrity(celeb)
    except Exception as e:
        logging.error(f"Failed {celeb}: {e}")
        continue  # Don't fail entire batch
```

### DynamoDB Operations

```python
import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('celebrity-database')

# Write
table.put_item(Item={
    'celebrity_id': celeb_id,
    'source_type#timestamp': f'{source}#{timestamp}',
    # ... other fields
})

# Query by celebrity_id
response = table.query(
    KeyConditionExpression='celebrity_id = :id',
    ExpressionAttributeValues={':id': celeb_id}
)

# Query by name (using GSI)
response = table.query(
    IndexName='name-index',
    KeyConditionExpression='name = :name',
    ExpressionAttributeValues={':name': 'Taylor Swift'}
)
```

### CloudWatch Metrics

```python
cloudwatch = boto3.client('cloudwatch')

# Publish custom metric
cloudwatch.put_metric_data(
    Namespace='CelebrityScrapers',
    MetricData=[
        {
            'MetricName': 'successful_scrapes',
            'Value': success_count,
            'Unit': 'Count'
        }
    ]
)
```

## Testing Strategy

**Standard Testing Pattern for All Phases**:

1. **Test with minimal data** (1 celebrity)
   ```bash
   python3 script.py --limit 1
   ```
   - Verify code runs without errors
   - Check logs for warnings/errors
   - Validate DynamoDB entry format

2. **Test with medium data** (5-10 celebrities)
   ```bash
   python3 script.py --limit 10
   ```
   - Check error resilience (if one fails, others continue)
   - Verify performance is acceptable
   - Monitor DynamoDB write throughput

3. **Review logs thoroughly**
   ```bash
   tail -f logs/output.log
   ```

4. **Only after success, run full dataset** (100 celebrities)
   ```bash
   python3 script.py
   ```

5. **Validate data quality**
   ```bash
   aws dynamodb scan --table-name celebrity-database --select COUNT
   ```

## Development Workflow

### Before Starting

- [ ] Read the relevant phase README.md
- [ ] Understand the data flow from previous phase
- [ ] Verify AWS credentials: `aws sts get-caller-identity`
- [ ] Check DynamoDB table exists and is accessible
- [ ] Review data schema (field names, types, required fields)

### During Development

- [ ] Install dependencies: `pip3 install -r requirements.txt`
- [ ] Create `.env` from template with required credentials
- [ ] Test with minimal data first (--limit 1)
- [ ] Review CloudWatch logs for errors: `aws logs tail /aws/lambda/FUNCTION --follow`
- [ ] Verify data in DynamoDB matches schema
- [ ] Test error handling (invalid data, network issues, rate limiting)
- [ ] Document any schema changes or new patterns

### Testing Checklist

- [ ] Unit tests pass: `pytest tests/test_scraper.py -v`
- [ ] Integration tests pass: `pytest tests/test_integration.py -v`
- [ ] Local tests pass with DynamoDB Local
- [ ] Pre-deployment validation passes: `python scripts/validate_deployment.py --fix`
- [ ] Load tests show acceptable performance

### Before Committing

- [ ] All tests pass with minimal, medium, AND full data
- [ ] No sensitive data in code (API keys, credentials, tokens)
- [ ] Code follows patterns in existing phase
- [ ] Error messages are user-friendly
- [ ] Logs are structured (JSON format preferred)
- [ ] README updated if adding new commands or patterns
- [ ] sam_template.yaml updated if changing Lambda config
- [ ] requirements.txt includes all dependencies with pinned versions

## Cost Optimization

Target: ~$4-6/month total system cost

- **DynamoDB On-Demand**: $1-2/month (pay per request, no provisioning)
- **Lambda**: $0.70/month (weekly scrapes, lightweight compute)
- **API Gateway**: $0.50/month (low request volume)
- **S3 + CloudFront**: $1-2/month (frontend hosting)
- **EventBridge**: $0.01/month (weekly triggers)
- **CloudWatch Logs**: $0.50/month (logging)
- **DynamoDB PITR**: $0.20/month (point-in-time recovery)

**Tips**:
- Always use On-Demand DynamoDB billing (not provisioned)
- Test with small datasets to catch unexpected costs early
- Monitor consumed capacity: `aws dynamodb describe-table --table-name celebrity-database`
- Set CloudWatch alarms for unusual activity

## Common Debugging Scenarios

### "NoCredentialsError"
```bash
aws configure  # Set up AWS credentials interactively
# Or set env vars:
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
```

### "Table not found"
```bash
cd phase-1-foundation/dynamodb-setup/
python3 create-table.py --region us-east-1
```

### "AccessDeniedException"
Verify IAM role includes: `dynamodb:PutItem`, `dynamodb:Query`, `dynamodb:GetItem`, `dynamodb:DescribeTable`, `dynamodb:Scan`

### "Partial scraping failure"
- Check DynamoDB for successfully written entries
- Review CloudWatch logs for which celebrities failed
- Fix the issue and re-run (successfully scraped celebrities won't duplicate)

### Rate Limiting Issues
- Check if you're hitting API limits
- Review circuit breaker status in logs
- Increase retry delays if needed

### DynamoDB Hot Partition
Check if all writes are going to same celebrity_id (should be distributed across celeb_001-celeb_100)

## Key Files to Know

| File | Purpose |
|------|---------|
| `README.md` | Project overview & architecture |
| `CLAUDE.md` | This file (guidance for Claude Code) |
| `project-updated.md` | Complete 1,450+ line specification |
| `phase-1-foundation/README.md` | DynamoDB setup guide |
| `phase-2-scrapers/README.md` | Scraper pipeline overview |
| `phase-2-scrapers/stage-2.2-instagram/README.md` | Instaloader implementation |
| `phase-2-scrapers/stage-2.2-instagram/MIGRATION_SUMMARY.md` | Old vs new approach |
| `phase-2-scrapers/stage-2.2-instagram/lambda_function.py` | Production-ready implementation |
| `phase-1-foundation/dynamodb-setup/create-table.py` | Creates main table |
| `phase-1-foundation/celebrity-seed/seed-database.py` | Seeds 100 celebrities |
| `shared/utils/` | Reusable utilities |

## Key Concepts to Remember

1. **Test First, Scale Later**: Always test 1 → 5 → 100 celebrities pattern
2. **First-Hand Data**: Raw API responses in `raw_text`, never parsed during scraping
3. **Modular Phases**: Each phase is independent—develop and test in isolation
4. **Graceful Degradation**: If one celebrity fails, others should continue (partial success OK)
5. **Weekly Automation**: EventBridge triggers all scrapers every Sunday 2 AM UTC
6. **No Hot Partitions**: Celebrity IDs distributed evenly (celeb_001 through celeb_100)
7. **Secure Credentials**: Never commit keys—use `.env` files and AWS Secrets Manager
8. **Documentation First**: Always read the phase README before starting

## Recent Changes (November 2025)

**Stage 2.2 Instagram Migration (Nov 8, 2025)**:
- Migrated from proxy-based scraping to free Instaloader library
- Cost reduction: $50-200/month → $0/month
- Reliability improvement: 60% → 80%+
- Complexity reduction: High → Low
- Added comprehensive testing infrastructure (unit, integration, local, load)
- Added pre-deployment validation scripts
- Added AWS SAM CloudFormation template
- See `phase-2-scrapers/stage-2.2-instagram/MIGRATION_SUMMARY.md` for details

## When to Use Tools

- **Task (Explore)**: Understanding architecture, "how does X work?", architectural questions
- **Glob/Grep**: Finding specific files, searching code
- **Read**: Reading specific files for context
- **Edit/Write**: Making code changes
- **Bash**: Git operations, running commands, deployment

## References & Further Reading

- `README.md` - Quick overview and diagram
- `project-updated.md` - Complete 1,450+ line specification (everything in detail)
- `phase-{N}/README.md` - Phase-specific implementation guide
- `phase-2-scrapers/stage-2.2-instagram/README.md` - Instaloader details
- `phase-2-scrapers/stage-2.2-instagram/MIGRATION_SUMMARY.md` - Migration details
- AWS DynamoDB: https://docs.aws.amazon.com/dynamodb/
- Boto3: https://boto3.amazonaws.com/v1/documentation/api/latest/
- Instaloader: https://instaloader.github.io/

---

**Last Updated**: November 9, 2025
**Version**: 2.0 (Updated with Phase 2 production implementations and recent migrations)

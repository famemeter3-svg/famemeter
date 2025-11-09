# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the **Celebrity Multi-Source Database System** - a serverless event-driven architecture that aggregates celebrity data from 4+ sources (Google Search, Instagram, Threads, YouTube). The system stores data in DynamoDB, computes confidence scores and sentiment analysis, and serves data via a REST API with a React dashboard.

**Current Status**: Phase 1 (DynamoDB setup & seeding) is complete. Phase 2 (Scrapers) is in progress with modern Instagram/Threads implementations. Phases 3-8 are pending.

## Architecture Overview

The system is organized into **8 independent phases**, each self-contained and testable:

```
Phase 1: Foundation          → DynamoDB table creation + 100 celebrity seeding
Phase 2: Scrapers           → 4-stage data collection (Google, Instagram, Threads, YouTube)
Phase 3: Post-Processing    → Weight (confidence) & sentiment computation
Phase 4: Orchestration      → EventBridge scheduling + DynamoDB Streams handling
Phase 5: API Layer          → REST API Gateway + Lambda endpoints
Phase 6: Frontend           → React dashboard (S3 + CloudFront)
Phase 7: Testing            → E2E tests & performance validation
Phase 8: Monitoring         → CloudWatch dashboards & alarms
```

### Key Data Architecture

- **Central Database**: DynamoDB table `celebrity-database`
  - Partition Key: `celebrity_id` (e.g., "celeb_001")
  - Sort Key: `source_type#timestamp` (e.g., "instagram#2025-11-07T17:20:00Z")
  - Global Secondary Indexes: `name-index`, `source-index`
  - Streams: Enabled (NEW_AND_OLD_IMAGES) for post-processor triggering

- **Data Pattern**: Each scraper entry includes:
  - **First-hand fields** (set during scraping): `id`, `name`, `raw_text`, `source`, `timestamp`
  - **Computed fields** (set by post-processor): `weight`, `sentiment`

### Integration Flow

```
EventBridge (weekly)
  ↓
All Phase 2 Scrapers (parallel)
  ├─ Stage 2.1: Google Search API
  ├─ Stage 2.3: Instagram (Selenium + anti-detection)
  ├─ Stage 2.3: Threads (similar to Instagram)
  └─ Stage 2.4: YouTube Data API
  ↓
DynamoDB writes (first-hand data)
  ↓
DynamoDB Streams triggers Phase 3
  ↓
Post-Processor computes weight & sentiment
  ↓
REST API serves data (Phase 5)
  ↓
React Frontend displays (Phase 6)
```

## Understanding Master Records vs Scraper Entries

This is the critical distinction that defines the entire system architecture:

### Master Record (Phase 1 Creates This)

A **master record** is the initial celebrity profile created during Phase 1 seeding. There is exactly **one per celebrity**.

**Characteristics**:
- Created once per celebrity during Phase 1 seeding via `seed-database.py`
- Contains: `celebrity_id`, `name`, `birth_date`, `nationality`, `occupation`, `is_active`
- Fixed `source_type#timestamp` = `"metadata#2025-01-01T00:00:00Z"` (always this value)
- NO `raw_text` field (that's Phase 2's job)
- NO `weight` field (that's Phase 3's job)
- NO `sentiment` field (that's Phase 3's job)

**Example**:
```json
{
  "celebrity_id": "celeb_001",
  "source_type#timestamp": "metadata#2025-01-01T00:00:00Z",
  "name": "Leonardo DiCaprio",
  "birth_date": "1974-11-11",
  "nationality": "American",
  "occupation": ["Actor", "Producer"],
  "created_at": "2025-11-07T00:00:00Z",
  "updated_at": "2025-11-07T00:00:00Z",
  "is_active": true
}
```

### Scraper Entry (Phase 2 Creates This)

A **scraper entry** is created by Phase 2 scrapers for each data source. There can be **multiple per celebrity** (one per data source like Google, Instagram, YouTube, etc.).

**Characteristics**:
- Created by Phase 2 scrapers for each data source
- Multiple per celebrity (one entry per source per scrape cycle)
- Contains: `celebrity_id`, `id`, `name`, `raw_text`, `source`, `timestamp`
- Dynamic `source_type#timestamp` = `"{source}#{ISO8601_timestamp}"` (varies per scrape)
- MUST have `raw_text` containing the complete, unprocessed API response
- `weight` = null initially (Phase 3 computes this)
- `sentiment` = null initially (Phase 3 computes this)

**Example**:
```json
{
  "celebrity_id": "celeb_001",
  "source_type#timestamp": "google_search#2025-11-07T17:20:00Z",
  "id": "scraper_entry_001_google_2025_11_07",
  "name": "Leonardo DiCaprio",
  "raw_text": "{\"search_results\": [{...COMPLETE unprocessed API response...}]}",
  "source": "https://www.google.com/search",
  "timestamp": "2025-11-07T17:20:00Z",
  "weight": null,
  "sentiment": null
}
```

### Key Differences

| Field | Master Record | Scraper Entry |
|-------|---------------|---------------|
| Created By | Phase 1 (seed-database.py) | Phase 2 (scrapers) |
| Count Per Celebrity | 1 | Multiple (one per source) |
| source_type#timestamp | Fixed: `metadata#2025-01-01T00:00:00Z` | Dynamic: `{source}#{timestamp}` |
| Has raw_text? | NO | YES (complete response) |
| Has weight? | NO | null (Phase 3 adds) |
| Has sentiment? | NO | null (Phase 3 adds) |
| Purpose | Basic celebrity metadata | Raw unprocessed data |

### Querying Both Types in DynamoDB

```bash
# Get ONLY the master record for celeb_001
aws dynamodb get-item --table-name celebrity-database \
  --key '{"celebrity_id":{"S":"celeb_001"},"source_type#timestamp":{"S":"metadata#2025-01-01T00:00:00Z"}}'

# Get ALL scraper entries for celeb_001 (excludes master record)
aws dynamodb query --table-name celebrity-database \
  --key-condition-expression "celebrity_id = :id AND source_type#timestamp > :metadata" \
  --expression-attribute-values '{":id":{"S":"celeb_001"},":metadata":{"S":"metadata"}}'

# Get only Google search entries for celeb_001
aws dynamodb query --table-name celebrity-database \
  --key-condition-expression "celebrity_id = :id AND begins_with(source_type#timestamp, :source)" \
  --expression-attribute-values '{":id":{"S":"celeb_001"},":source":{"S":"google_search#"}}'

# Get ALL celebrities' master records only (metadata entries)
aws dynamodb scan --table-name celebrity-database \
  --filter-expression "source_type#timestamp = :metadata" \
  --expression-attribute-values '{":metadata":{"S":"metadata#2025-01-01T00:00:00Z"}}'
```

### Why This Design?

The **first-hand data philosophy** separates concerns:
1. **Master record** = stable, reference data (one per celebrity)
2. **Scraper entry** = raw, unprocessed data (multiple sources)
3. **Post-processed** = computed confidence and sentiment (Phase 3)

This allows:
- Easy lookup of celebrity metadata without filtering
- Multiple data sources per celebrity
- Progressive enrichment (raw → processed)
- Complete audit trail (original data preserved in raw_text)

---

## Technology Stack

**AWS Services**: DynamoDB (On-Demand), Lambda, EventBridge, API Gateway, S3, CloudFront, CloudWatch, Secrets Manager

**Backend**: Python 3.11, boto3, requests, Selenium (for Instagram/Threads), BeautifulSoup4, TextBlob (sentiment)

**Frontend**: React 18, React Router, Axios, Tailwind CSS, React Query

**External APIs**: Google Custom Search, YouTube Data API v3, Instagram Web (Selenium), Threads Web (Selenium)

## Directory Structure

```
phase-1-foundation/            ← Current phase (COMPLETE)
├── dynamodb-setup/            - Table creation scripts
├── celebrity-seed/            - 100 celebrity seeding
└── schemas/                   - Data structure documentation

phase-2-scrapers/              ← Active development
├── stage-2.1-google-search/   - Google Custom Search API (DONE)
├── stage-2.2-instagram/       - Legacy Instagram (DEPRECATED)
├── stage-2.3-instagram/       - Modern Instagram/Selenium (PRODUCTION)
├── stage-2.3-threads/         - Threads scraper (PRODUCTION)
├── stage-2.4-youtube/         - YouTube API (DONE)
└── shared-resources/          - Common utilities

phase-3-post-processing/       ← Pending
phase-4-orchestration/         ← Pending
phase-5-api/                   ← Pending
phase-6-frontend/              ← Pending
phase-7-testing/               ← Pending
phase-8-monitoring/            ← Pending

shared/                        - Cross-phase utilities
└── utils/, constants/, config-templates/, documentation/
```

## Common Commands

### DynamoDB Setup (Phase 1)

```bash
# Create the main table
cd phase-1-foundation/dynamodb-setup/
python3 create-table.py --region us-east-1

# Verify table structure
python3 test-operations.py --table celebrity-database --region us-east-1

# Seed first 10 celebrities (test)
cd ../celebrity-seed/
python3 seed-database.py --region us-east-1 --limit 10

# Seed all 100 celebrities
python3 seed-database.py --region us-east-1

# Validate seeding
python3 validate-seed.py --table celebrity-database --region us-east-1
```

### DynamoDB Queries

```bash
# Verify table exists and is active
aws dynamodb describe-table --table-name celebrity-database \
  --query 'Table.[TableStatus,BillingModeSummary.BillingMode]'

# Count total records
aws dynamodb scan --table-name celebrity-database --select COUNT

# Get specific celebrity
aws dynamodb get-item --table-name celebrity-database \
  --key '{"celebrity_id":{"S":"celeb_001"},"source_type#timestamp":{"S":"metadata#2025-01-01T00:00:00Z"}}'

# Query by name (using GSI)
aws dynamodb query --table-name celebrity-database \
  --index-name name-index \
  --key-condition-expression "name = :name" \
  --expression-attribute-values '{":name":{"S":"Leonardo DiCaprio"}}'

# Query by source (using GSI) - works after Phase 2
aws dynamodb query --table-name celebrity-database \
  --index-name source-index \
  --key-condition-expression "source = :source" \
  --expression-attribute-values '{":source":{"S":"https://www.instagram.com"}}'
```

### Development Testing Pattern

All phases follow this pattern:

```bash
# 1. Test with minimal data (1 celebrity)
python3 script.py --limit 1

# 2. Review logs and output
cat logs/output.log

# 3. Verify DynamoDB entries
aws dynamodb scan --table-name celebrity-database --select COUNT

# 4. If successful, test medium scale (5-10)
python3 script.py --limit 10

# 5. Only after validation, run full scale
python3 script.py
```

## Phase 2 Scraper Development

### Current Status

- **Stage 2.1 (Google Search)**: ✅ Production ready
- **Stage 2.2 (Instagram Legacy)**: ⚠️ Deprecated (replaced by 2.3)
- **Stage 2.3 (Instagram Modern)**: ✅ Production ready with Selenium + anti-detection
- **Stage 2.4 (YouTube)**: ✅ Production ready
- **Stage 2.3 (Threads)**: ✅ Production ready with Selenium + anti-detection

### Modern Instagram/Threads Architecture (Stage 2.3)

The Instagram and Threads scrapers use a sophisticated architecture to avoid detection:

**Key Components**:
- `instagram_scraper.py` - Main orchestrator
- `browser_manager.py` - Selenium WebDriver with stealth injection
- `instagram_navigator.py` - Page automation and interaction
- `data_extractor.py` - DOM parsing and data extraction
- `proxy_manager.py` - Proxy rotation with health checks

**Features**:
- Multi-browser execution (concurrent execution of 3+ browsers)
- Anti-detection: JavaScript injection, fingerprint randomization
- Account rotation from credential pool
- Proxy rotation with health checks
- Collects: profile metadata, posts, reels, comments, engagement

**How to Run**:

```bash
cd phase-2-scrapers/stage-2.3-instagram/

# Install dependencies
pip3 install -r requirements.txt

# Set up credentials in .env
cp .env.template .env
# Edit .env with Instagram accounts and proxy list

# Test with single celebrity
python3 lambda_function.py --test --celebrity-id celeb_001

# View logs
tail -f logs/instagram_scraper.log

# Check DynamoDB for new entries
aws dynamodb query --table-name celebrity-database \
  --key-condition-expression "celebrity_id = :id" \
  --expression-attribute-values '{":id":{"S":"celeb_001"}}'
```

### When Adding New Scrapers

Follow the same pattern as existing scrapers:

1. Create `phase-2-scrapers/stage-2.X-{source}/` directory
2. Implement `lambda_function.py` with `lambda_handler(event, context)` function
3. Store data using first-hand pattern (raw_text, source, timestamp)
4. Include error handling and retry logic
5. Write `requirements.txt` with all dependencies
6. Create `.env.template` for credentials
7. Test with minimal data first (--limit 1)
8. Document in phase README

## Critical Implementation Patterns

### First-Hand Data Storage

All scrapers **must** store the complete, unprocessed response in the `raw_text` field:

```python
# Correct - stores entire API response
entry = {
    'id': f'scraper_{source}_{timestamp}',
    'name': data['name'],  # From source
    'raw_text': json.dumps(complete_api_response),  # Entire response
    'source': 'https://api.example.com',
    'timestamp': iso8601_timestamp,
    'weight': None,  # Will be computed later
    'sentiment': None  # Will be computed later
}
```

### Error Handling

All operations should include:

```python
import logging
import boto3
from botocore.exceptions import ClientError

# Exponential backoff for retries
def retry_with_backoff(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return func()
        except ClientError as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)

# Graceful degradation
try:
    # Scrape celebrity
except Exception as e:
    logging.error(f"Failed for {celeb_id}: {e}")
    # Continue with next celebrity instead of failing entire batch
    continue
```

### DynamoDB Operations

Always use boto3 with On-Demand billing:

```python
import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('celebrity-database')

# Write entry
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
```

## Key Files and Locations

| File/Directory | Purpose |
|---|---|
| `README.md` | Project overview and quick start |
| `project-updated.md` | Complete 1,450-line specification |
| `phase-1-foundation/README.md` | Phase 1 detailed documentation |
| `phase-1-foundation/dynamodb-setup/create-table.py` | Creates the main DynamoDB table |
| `phase-1-foundation/celebrity-seed/celebrities.json` | 100 celebrity seed data |
| `phase-2-scrapers/stage-2.3-instagram/` | Production Instagram scraper |
| `phase-2-scrapers/stage-2.3-threads/` | Production Threads scraper |
| `shared/utils/` | Common utilities (DynamoDB helpers, logging, validation) |
| `shared/constants/` | Field definitions and constants |
| `shared/config-templates/.env.template` | Environment variable template |

## Development Checklist

When working on any phase:

### Before Starting
- [ ] Read the phase-specific README.md
- [ ] Understand the data flow from previous phase
- [ ] Verify you have AWS credentials configured: `aws sts get-caller-identity`
- [ ] Check DynamoDB table exists and is accessible
- [ ] Review the data schema for that phase

### During Development
- [ ] Install dependencies: `pip3 install -r requirements.txt`
- [ ] Create `.env` file from template and add credentials
- [ ] Test with minimal data first (1-5 items)
- [ ] Check CloudWatch logs for errors
- [ ] Verify data in DynamoDB matches expected schema
- [ ] Test error handling (network failure, invalid data, etc.)
- [ ] Document any changes to data schema

### Before Committing
- [ ] All tests pass with minimal data
- [ ] All tests pass with medium dataset (5-50 items)
- [ ] No sensitive data in code (keys, passwords, tokens)
- [ ] Error messages are user-friendly (not stack traces)
- [ ] Code follows existing patterns in the phase
- [ ] README updated with any new instructions

### Before Moving to Next Phase
- [ ] Phase data is complete and validated
- [ ] All dependencies documented in requirements.txt
- [ ] Error handling implemented and tested
- [ ] Monitoring/logging in place
- [ ] Documentation complete

## Debugging

### Common Issues

**"NoCredentialsError"**
```bash
aws configure  # Set up AWS credentials
# or
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
```

**"Table not found"**
```bash
# Create table first
cd phase-1-foundation/dynamodb-setup/
python3 create-table.py
```

**"AccessDeniedException"**
```bash
# Verify IAM permissions include:
# dynamodb:PutItem, dynamodb:Query, dynamodb:Scan, dynamodb:GetItem, dynamodb:DescribeTable
```

**"Partial scraping failure"**
- Check DynamoDB for entries that were successfully written
- Review CloudWatch logs for which celebrities failed
- Fix the issue and re-run - successfully scraped celebrities won't be duplicated if using proper ID patterns

### Viewing Logs and Debugging

```bash
# CloudWatch logs for Lambda functions
aws logs tail /aws/lambda/scraper-instagram --follow

# DynamoDB debug queries
aws dynamodb scan --table-name celebrity-database \
  --filter-expression 'contains(#n, :celeb)' \
  --expression-attribute-names '{"#n":"name"}' \
  --expression-attribute-values '{":celeb":{"S":"Taylor"}}'

# Check if stream is receiving events (Phase 3)
aws dynamodbstreams list-streams --table-name celebrity-database
```

## Cost Optimization

The system is designed for ~$4-6/month:

- **DynamoDB On-Demand**: $1-2/month (pay per request, no provisioning)
- **Lambda**: $0.70/month (weekly scrapes, lightweight compute)
- **API Gateway**: $0.50/month (low request volume)
- **S3 + CloudFront**: $1-2/month (frontend static hosting)
- **EventBridge**: $0.01/month (weekly trigger)
- **CloudWatch**: $0.50/month (logging)
- **DynamoDB PITR**: $0.20/month (backup)

Tips:
- Always use On-Demand billing mode (not provisioned)
- Test with small datasets to avoid unexpected charges
- Monitor DynamoDB consumed capacity: `aws dynamodb describe-table --table-name celebrity-database`
- Set CloudWatch alarms for unusual activity

## When to Use Task Tool

This codebase is complex with multiple phases. When exploring:

- Use `Task` tool with `Explore` subagent for understanding architecture and answering "how do X work?" questions
- Use direct tools (Glob, Grep, Read) for finding specific files or code
- Use Bash for git and terminal operations
- Use Edit/Write for making code changes

## Important Notes

1. **Test Before Scale**: Always test with 1 celebrity → 10 celebrities → 100 celebrities pattern
2. **First-Hand Data Philosophy**: Raw API responses stored in `raw_text`, post-processing happens in Phase 3
3. **Modular Design**: Each phase is independent - develop and test in isolation
4. **Error Resilience**: If one celebrity fails, others should continue (partial success is acceptable)
5. **Weekly Updates**: EventBridge triggers all scrapers every Sunday 2 AM UTC
6. **No Hot Partitions**: Celebrity IDs are evenly distributed (celeb_001 through celeb_100)
7. **Secure Credentials**: Never commit API keys, use `.env` files and AWS Secrets Manager
8. **Documentation First**: Each phase has detailed README - read it before starting

## References

- `README.md` - Quick overview and architecture diagram
- `project-updated.md` - Complete 1,450+ line specification (all details)
- `phase-{N}/README.md` - Phase-specific implementation guide
- AWS Documentation: https://docs.aws.amazon.com/dynamodb/
- Boto3: https://boto3.amazonaws.com/v1/documentation/api/latest/

---

**Last Updated**: November 9, 2025

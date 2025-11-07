# Phase 2 Preparation Guide

**Phase 1 Status**: ✅ Complete
**Phase 2 Status**: 🎯 Ready to Begin
**Estimated Duration**: 2-3 weeks

---

## What Phase 2 Will Do

Phase 2 focuses on **data collection** from multiple sources using Lambda functions (scrapers).

### Data Sources to Integrate

1. **TMDb (The Movie Database)**
   - Movies, TV shows, cast information
   - High quality structured data
   - Requires API key

2. **Wikipedia**
   - Biographical information
   - Career details
   - References and links

3. **News API**
   - Recent news about celebrities
   - Trending information
   - Multiple news sources

4. **Social Media**
   - Twitter/X posts
   - Instagram profiles
   - Engagement metrics

---

## Infrastructure Ready for Phase 2

### ✅ DynamoDB Table
- Table: `celebrity-database` (ACTIVE in us-east-1)
- 100 celebrity records seeded
- DynamoDB Streams **enabled** for event triggering
- GSIs ready for Phase 2 query patterns

### ✅ Data Structure
Each Phase 2 scraper will add records like:

```json
{
  "celebrity_id": "celeb_001",
  "source_type#timestamp": "tmdb#2025-11-07T17:20:00Z",
  "id": "scraper_entry_001_tmdb_2025_11_07",
  "name": "周潤發",
  "raw_text": "{...complete API response...}",
  "source": "https://api.themoviedb.org/3/person/search",
  "timestamp": "2025-11-07T17:20:00Z",
  "weight": null,
  "sentiment": null,
  "metadata": {
    "scraper_name": "scraper-tmdb",
    "source_type": "tmdb",
    "processed": false,
    "error": null
  }
}
```

### ✅ Validation Tests
- Run test-operations.py before deploying Phase 2
- Verify table still ACTIVE
- Confirm streams still operational

---

## Phase 2 Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    External APIs                         │
│  TMDb  Wikipedia  NewsAPI  Twitter  Instagram  etc.    │
└────────────────┬──────────────────────────────────────┘
                 │
        ┌────────┴──────────┬────────────┬─────────────┐
        │                   │            │             │
        ▼                   ▼            ▼             ▼
   ┌─────────┐         ┌─────────┐ ┌────────┐    ┌──────────┐
   │ Lambda  │         │ Lambda  │ │Lambda  │    │  Lambda  │
   │TMDb     │         │Wikipedia│ │News    │    │  Social  │
   │Scraper  │         │Scraper  │ │Scraper │    │  Scraper │
   └────┬────┘         └────┬────┘ └───┬────┘    └─────┬────┘
        │                   │          │               │
        └───────────────────┼──────────┼───────────────┘
                            │
                            ▼
        ┌──────────────────────────────────────┐
        │   DynamoDB Table                     │
        │   celebrity-database (us-east-1)     │
        │                                      │
        │  100 metadata records +              │
        │  Scraper entry records               │
        └──────────────────┬───────────────────┘
                           │
                    ┌──────▼──────┐
                    │ DynamoDB    │
                    │ Streams     │
                    │ (Events)    │
                    └──────┬──────┘
                           │
                           ▼
        ┌──────────────────────────────────┐
        │   Post-Processor Lambda          │
        │   (Phase 3)                      │
        │                                  │
        │  - Compute weight/confidence    │
        │  - Sentiment analysis           │
        │  - Update records               │
        └──────────────────────────────────┘
```

### Component Responsibilities

| Component | Purpose | Input | Output |
|-----------|---------|-------|--------|
| **TMDb Scraper** | Fetch movie/TV data | celebrity_id | Scraper entry with raw_text |
| **Wikipedia Scraper** | Fetch biography | celebrity_id | Scraper entry with raw_text |
| **News Scraper** | Fetch recent news | celebrity_id | Scraper entry with raw_text |
| **Social Scraper** | Fetch social media | celebrity_id | Scraper entry with raw_text |
| **Post-Processor** | Enrich data | DynamoDB Stream event | Updated record with weight/sentiment |

---

## Phase 2 Development Roadmap

### Week 1: Setup & TMDb Integration
- [ ] Set up Lambda development environment
- [ ] Create TMDb scraper Lambda
- [ ] Obtain TMDb API key
- [ ] Test TMDb scraper locally
- [ ] Deploy TMDb scraper to AWS
- [ ] Add records to DynamoDB
- [ ] Verify records structure

### Week 2: Additional Scrapers
- [ ] Create Wikipedia scraper
- [ ] Create News API scraper (NewsAPI.org)
- [ ] Deploy both scrapers
- [ ] Test all 3 scrapers together
- [ ] Verify data quality
- [ ] Handle errors gracefully

### Week 3: Optimization & Post-Processor
- [ ] Create post-processor Lambda
- [ ] Connect to DynamoDB Streams
- [ ] Implement weight/confidence scoring
- [ ] Implement sentiment analysis
- [ ] Deploy post-processor
- [ ] Test end-to-end flow
- [ ] Monitor and optimize

---

## Scraper Implementation Template

Each Phase 2 scraper will follow this pattern:

```python
import boto3
import json
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('celebrity-database')

def lambda_handler(event, context):
    """
    Scraper Lambda function

    Event format: { "celebrity_id": "celeb_001" }
    Writes: Scraper entry record to DynamoDB
    """

    celebrity_id = event.get('celebrity_id')

    try:
        # 1. Call external API
        api_response = call_api(celebrity_id)

        # 2. Create scraper entry record
        timestamp = datetime.utcnow().isoformat() + 'Z'
        entry = {
            'celebrity_id': celebrity_id,
            'source_type#timestamp': f'{SOURCE_TYPE}#{timestamp}',
            'id': f'scraper_entry_{celebrity_id}_{SOURCE_TYPE}_{timestamp}',
            'name': api_response.get('name'),
            'raw_text': json.dumps(api_response),  # Complete API response
            'source': API_SOURCE_URL,
            'timestamp': timestamp,
            'weight': None,  # Will be computed by post-processor
            'sentiment': None,  # Will be computed by post-processor
            'metadata': {
                'scraper_name': f'scraper-{SOURCE_TYPE}',
                'source_type': SOURCE_TYPE,
                'processed': False,  # Post-processor will set to True
                'error': None
            }
        }

        # 3. Write to DynamoDB
        table.put_item(Item=entry)

        return {
            'statusCode': 200,
            'body': json.dumps(f'Successfully scraped {celebrity_id}')
        }

    except Exception as e:
        # Log error in entry
        error_entry = {
            'celebrity_id': celebrity_id,
            'source_type#timestamp': f'{SOURCE_TYPE}#{datetime.utcnow().isoformat()}Z',
            'metadata': {
                'scraper_name': f'scraper-{SOURCE_TYPE}',
                'source_type': SOURCE_TYPE,
                'processed': False,
                'error': str(e)
            }
        }
        table.put_item(Item=error_entry)

        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }

def call_api(celebrity_id):
    # TODO: Implement API call
    # Return: { 'name': '...', 'data': {...} }
    pass
```

---

## Data Flow Example

### Step 1: Scraper Fetches Data
```
Lambda TMDb Scraper triggered
↓
Calls: https://api.themoviedb.org/3/search/person?query=周潤發
↓
Response: {
  "results": [{
    "id": 3224,
    "name": "周潤發",
    "popularity": 45.2,
    "profile_path": "/image.jpg",
    "known_for": [...]
  }]
}
```

### Step 2: Record Written to DynamoDB
```
Table: celebrity-database
Partition Key: celebrity_id = "celeb_001"
Sort Key: source_type#timestamp = "tmdb#2025-11-07T17:20:00Z"

Fields written:
{
  "celebrity_id": "celeb_001",
  "source_type#timestamp": "tmdb#2025-11-07T17:20:00Z",
  "id": "scraper_entry_001_tmdb_...",
  "raw_text": "{...complete API response...}",
  "source": "https://api.themoviedb.org/3/search/person",
  "timestamp": "2025-11-07T17:20:00Z",
  "weight": null,
  "sentiment": null,
  "metadata": {
    "scraper_name": "scraper-tmdb",
    "source_type": "tmdb",
    "processed": false,
    "error": null
  }
}
```

### Step 3: DynamoDB Stream Event Triggered
```
Stream record:
{
  "eventID": "xyz123",
  "eventName": "INSERT",
  "dynamodb": {
    "Keys": {
      "celebrity_id": {"S": "celeb_001"},
      "source_type#timestamp": {"S": "tmdb#2025-11-07T17:20:00Z"}
    },
    "NewImage": {...full record...}
  }
}
```

### Step 4: Post-Processor Lambda Triggered
```
Receives DynamoDB Stream event
↓
Extracts raw_text
↓
Computes:
  - weight: Confidence score (0-1) based on data quality
  - sentiment: NLP analysis (positive, negative, neutral)
↓
Updates record:
{
  "weight": 0.85,
  "sentiment": "positive",
  "metadata.processed": true
}
```

### Step 5: Final Record in DynamoDB
```
Complete record now has:
{
  "celebrity_id": "celeb_001",
  "source_type#timestamp": "tmdb#2025-11-07T17:20:00Z",
  "raw_text": "{...complete response...}",
  "weight": 0.85,           # ← Added by post-processor
  "sentiment": "positive",   # ← Added by post-processor
  "metadata.processed": true # ← Updated by post-processor
}
```

---

## Testing Phase 2 Scrapers

### 1. Test Locally
```bash
# Install dependencies
pip install boto3 requests

# Run scraper function locally
python scraper.py --celebrity celeb_001

# Verify output format
```

### 2. Deploy to AWS Lambda
```bash
# Create Lambda function
aws lambda create-function \
  --function-name scraper-tmdb \
  --runtime python3.11 \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://scraper.zip \
  --role arn:aws:iam::ACCOUNT_ID:role/lambda-role

# Set environment variables
aws lambda update-function-configuration \
  --function-name scraper-tmdb \
  --environment Variables=TMDB_API_KEY=xxx
```

### 3. Test in AWS
```bash
# Invoke Lambda
aws lambda invoke \
  --function-name scraper-tmdb \
  --payload '{"celebrity_id":"celeb_001"}' \
  response.json

# Check response
cat response.json

# Verify record in DynamoDB
aws dynamodb query --table-name celebrity-database \
  --key-condition-expression "celebrity_id = :id" \
  --expression-attribute-values "{\":id\":{\"S\":\"celeb_001\"}}"
```

### 4. Monitor in Production
```bash
# View CloudWatch logs
aws logs tail /aws/lambda/scraper-tmdb --follow

# Check for errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/scraper-tmdb \
  --filter-pattern "ERROR"

# Track invocations
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=scraper-tmdb
```

---

## Pre-Phase 2 Checklist

Before starting Phase 2, verify Phase 1:

```bash
# 1. Verify table still exists and ACTIVE
aws dynamodb describe-table --table-name celebrity-database \
  --query 'Table.TableStatus'

# 2. Verify all 100 celebrities still loaded
aws dynamodb scan --table-name celebrity-database \
  --select COUNT

# 3. Run validation tests
cd phase-1-foundation/dynamodb-setup/
python3 test-operations.py --table celebrity-database

# 4. Verify streams still operational
aws dynamodb describe-table --table-name celebrity-database \
  --query 'Table.LatestStreamArn'
```

All should return:
- Table Status: ACTIVE ✅
- Record Count: 100 ✅
- Tests: 12/12 PASSED ✅
- Stream ARN: Present ✅

---

## External API Requirements

### TMDb
- **Website**: https://www.themoviedb.org/
- **API Docs**: https://developer.themoviedb.org/reference/intro/getting-started
- **Auth**: API Key required
- **Rate Limit**: 40 requests/10 seconds
- **Data Quality**: High (structured, reliable)

### Wikipedia
- **Website**: https://www.wikipedia.org/
- **API Docs**: https://en.wikipedia.org/w/api.php
- **Auth**: None required
- **Rate Limit**: Reasonable (check docs)
- **Data Quality**: Medium (varies by person)

### News API
- **Website**: https://newsapi.org/
- **API Docs**: https://newsapi.org/docs
- **Auth**: API Key required
- **Rate Limit**: 100-250 requests/day (plan dependent)
- **Data Quality**: High (real news sources)

### Social Media
- **Twitter/X**: https://developer.twitter.com/
- **Instagram**: Limited API (consider Web Scraping)
- **Auth**: OAuth/API Keys required
- **Rate Limits**: Vary by endpoint
- **Data Quality**: Medium (social media noise)

---

## Error Handling Strategy

### Scraper Errors
```python
try:
    api_response = call_api(celebrity_id)
except APIError as e:
    # Write error record to DynamoDB
    error_record = {
        'celebrity_id': celebrity_id,
        'source_type#timestamp': f'{SOURCE}#{timestamp}Z',
        'metadata': {
            'error': str(e),
            'processed': False,
            'scraper_name': f'scraper-{SOURCE}'
        }
    }
    table.put_item(Item=error_record)
    # Still considered a "record" - documents the failure
```

### Post-Processor Errors
```python
try:
    weight = compute_weight(raw_text)
    sentiment = analyze_sentiment(raw_text)
except ProcessingError as e:
    # Update with error metadata, keep existing weight/sentiment
    table.update_item(
        Key={...},
        UpdateExpression='SET #metadata.#error = :error',
        ExpressionAttributeNames={
            '#metadata': 'metadata',
            '#error': 'error'
        },
        ExpressionAttributeValues={
            ':error': str(e)
        }
    )
```

---

## Success Metrics for Phase 2

### Scraper Performance
- [ ] All 100 celebrities scraped successfully
- [ ] Average scrape time < 2 seconds per celebrity
- [ ] < 1% failure rate
- [ ] All records contain raw_text
- [ ] All timestamps valid

### Data Quality
- [ ] Records properly formatted
- [ ] All required fields present
- [ ] < 5% incomplete records
- [ ] No duplicate scraper entries per source per date
- [ ] raw_text field not truncated

### Post-Processor Performance
- [ ] < 1 second latency per record
- [ ] 100% of records processed
- [ ] weight values 0-1 valid range
- [ ] sentiment values in {positive, negative, neutral}
- [ ] metadata.processed = true on all

---

## Transition from Phase 2 to Phase 3

### What Phase 3 Will Do
Phase 3 focuses on **data processing and aggregation**:
- Conflict resolution (multiple sources for same data)
- Data deduplication
- Master data compilation
- API exposure for frontend

### Prerequisites
- All Phase 2 scrapers deployed and working
- At least 1 week of scraper data accumulated
- Post-processor successfully computing weight/sentiment

---

## Resources & Documentation

### Key Files to Reference
- `DEPLOYMENT_REPORT.md` - Phase 1 details
- `PHASE_1_SUCCESS.md` - What was built
- `README.md` - Original specifications
- `dynamodb-setup/table-definition.json` - DynamoDB schema
- `celebrity-seed/celebrities.json` - Celebrity list

### AWS Documentation
- [Lambda Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- [DynamoDB Streams](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Streams.html)
- [Lambda with DynamoDB Streams](https://docs.aws.amazon.com/lambda/latest/dg/with-ddb.html)

### External APIs
- TMDb API: https://developer.themoviedb.org/
- Wikipedia API: https://en.wikipedia.org/w/api.php
- NewsAPI: https://newsapi.org/docs
- Twitter API: https://developer.twitter.com/

---

## Phase 2 Success Definition

✅ **Phase 2 Complete When**:
1. All 4 scrapers deployed and operational
2. Each celebrity has at least 1 scraper record
3. Post-processor updating all new records
4. weight and sentiment fields populated
5. No errors in CloudWatch logs
6. Database contains mix of metadata + scraper records
7. Query patterns working (by source, by date range)

---

## Questions?

- **About Phase 1?** See DEPLOYMENT_REPORT.md
- **About DynamoDB?** See AWS documentation
- **About API setup?** Check external API docs
- **About Lambda?** See AWS Lambda docs

---

*Phase 1 Complete ✅*
*Ready for Phase 2 Development 🚀*
*Estimated Start: After Phase 1 sign-off*

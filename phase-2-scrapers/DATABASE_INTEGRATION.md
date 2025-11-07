# Phase 2: Database Integration Guide

## Overview

This guide explains how Phase 2 scrapers integrate with the **DynamoDB database established in Phase 1**. All scrapers write to the same `celebrity-database` table using a consistent schema and query patterns.

## Phase 1 Foundation (Reference)

### Table Details

| Property | Value |
|----------|-------|
| **Table Name** | `celebrity-database` |
| **Region** | `us-east-1` |
| **Billing Mode** | On-Demand (pay-per-request) |
| **Status** | ACTIVE & OPERATIONAL |
| **Initial Records** | 100 celebrity metadata records |

### Partition Key

```
Key: celebrity_id
Type: String (S)
Format: celeb_NNN (e.g., celeb_001, celeb_002)
Purpose: Groups all data for one celebrity
```

### Sort Key

```
Key: source_type#timestamp
Type: String (S)
Format: {source_type}#{ISO8601_timestamp}
Examples:
  - metadata#2025-01-01T00:00:00Z        (Phase 1 seed data)
  - google_search#2025-11-07T17:20:00Z   (Stage 2.1)
  - instagram#2025-11-07T17:21:00Z       (Stage 2.2)
  - threads#2025-11-07T17:22:00Z         (Stage 2.3)
  - youtube#2025-11-07T17:23:00Z         (Stage 2.4)
Purpose: Enables source-specific and time-series queries
```

### Global Secondary Indexes (GSI)

| Index Name | Partition Key | Sort Key | Purpose |
|-----------|---------------|----------|---------|
| **name-index** | `name` (S) | None | Search celebrities by name |
| **source-index** | `source` (S) | `timestamp` (S) | Query by data source |

### DynamoDB Streams

- **Status**: ENABLED
- **View Type**: NEW_AND_OLD_IMAGES
- **Purpose**: Triggers Phase 3 post-processor for weight/sentiment computation

## Phase 1 Data Structure (Seed Records)

Each celebrity has a metadata record:

```json
{
  "celebrity_id": "celeb_001",
  "source_type#timestamp": "metadata#2025-01-01T00:00:00Z",
  "name": "周潤發",
  "birth_date": "1955-05-18",
  "nationality": "台灣",
  "occupation": ["演員", "製片人"],
  "created_at": "2025-11-07T11:03:26.192920Z",
  "updated_at": "2025-11-07T11:03:26.192920Z",
  "is_active": true
}
```

## Phase 2 Data Structure (Scraper Records)

Phase 2 scrapers add records with the same `celebrity_id` but different sort keys:

```json
{
  "celebrity_id": "celeb_001",
  "source_type#timestamp": "tmdb#2025-11-07T17:20:00Z",
  "id": "scraper_entry_001_tmdb_2025_11_07",
  "name": "周潤發",
  "raw_text": "{...complete unprocessed API response...}",
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

### Field Breakdown

| Field | Type | Set During | Example | Notes |
|-------|------|-----------|---------|-------|
| `celebrity_id` | String | Write | `celeb_001` | Same as seed record |
| `source_type#timestamp` | String | Write | `tmdb#2025-11-07T17:20:00Z` | Composite key for source/time |
| `id` | String | Write | `scraper_entry_001_tmdb` | Unique scraper entry ID |
| `name` | String | Write | `周潤發` | Celebrity name from source |
| `raw_text` | String | Write | `{...JSON...}` | **Complete unprocessed response** |
| `source` | String | Write | `https://api.themoviedb.org...` | Source API endpoint |
| `timestamp` | ISO8601 | Write | `2025-11-07T17:20:00Z` | When data was scraped |
| `weight` | Float/Null | Phase 3 | `null` → `0.85` | Confidence score (0-1) |
| `sentiment` | String/Null | Phase 3 | `null` → `positive` | Sentiment classification |
| `metadata` | Object | Write | See below | Scraper-specific metadata |

### Metadata Object Structure

```json
{
  "scraper_name": "scraper-tmdb",
  "source_type": "tmdb",
  "processed": false,
  "error": null,
  "retry_count": 0,
  "last_updated": "2025-11-07T17:20:00Z"
}
```

## DynamoDB Operations for Phase 2 Scrapers

### 1. Read Celebrity Metadata

**Purpose**: Get celebrity name and ID for API calls

**Query Pattern**:
```python
response = dynamodb.query(
    TableName='celebrity-database',
    KeyConditionExpression='celebrity_id = :id AND source_type#timestamp = :key',
    ExpressionAttributeValues={
        ':id': {'S': 'celeb_001'},
        ':key': {'S': 'metadata#2025-01-01T00:00:00Z'}
    }
)

# Returns the celebrity metadata record
# Fields available: name, birth_date, nationality, occupation
```

**CLI Equivalent**:
```bash
aws dynamodb query --table-name celebrity-database \
  --key-condition-expression "celebrity_id = :id AND source_type#timestamp = :key" \
  --expression-attribute-values \
    "{\":id\":{\"S\":\"celeb_001\"},\":key\":{\"S\":\"metadata#2025-01-01T00:00:00Z\"}}" \
  --region us-east-1
```

### 2. Write Scraper Entry

**Purpose**: Store scraped data in database

**Write Pattern**:
```python
dynamodb.put_item(
    TableName='celebrity-database',
    Item={
        'celebrity_id': {'S': 'celeb_001'},
        'source_type#timestamp': {'S': 'tmdb#2025-11-07T17:20:00Z'},
        'id': {'S': 'scraper_entry_001_tmdb_2025_11_07'},
        'name': {'S': '周潤發'},
        'raw_text': {'S': json.dumps(api_response)},
        'source': {'S': 'https://api.themoviedb.org/3/person/search'},
        'timestamp': {'S': '2025-11-07T17:20:00Z'},
        'weight': {'NULL': True},
        'sentiment': {'NULL': True},
        'metadata': {'M': {
            'scraper_name': {'S': 'scraper-tmdb'},
            'source_type': {'S': 'tmdb'},
            'processed': {'BOOL': False},
            'error': {'NULL': True}
        }}
    }
)
```

**Using Boto3 (Recommended)**:
```python
import json
import uuid
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('celebrity-database')

scraper_entry = {
    'celebrity_id': 'celeb_001',
    'source_type#timestamp': f"tmdb#{datetime.utcnow().isoformat()}Z",
    'id': str(uuid.uuid4()),
    'name': celebrity_name,
    'raw_text': json.dumps(api_response),  # IMPORTANT: Store complete response
    'source': 'https://api.themoviedb.org/3/person/search',
    'timestamp': datetime.utcnow().isoformat() + 'Z',
    'weight': None,
    'sentiment': None,
    'metadata': {
        'scraper_name': 'scraper-tmdb',
        'source_type': 'tmdb',
        'processed': False,
        'error': None
    }
}

table.put_item(Item=scraper_entry)
```

### 3. Query Scraper Records (By Source)

**Purpose**: Retrieve all records from specific source

**Query Pattern**:
```python
response = table.query(
    KeyConditionExpression='celebrity_id = :id AND source_type#timestamp BEGINS_WITH :prefix',
    ExpressionAttributeValues={
        ':id': 'celeb_001',
        ':prefix': 'tmdb#'
    }
)

# Returns all TMDb records for this celebrity
# Sorted by timestamp (most recent last)
```

**CLI Equivalent**:
```bash
aws dynamodb query --table-name celebrity-database \
  --key-condition-expression "celebrity_id = :id AND source_type#timestamp BEGINS_WITH :prefix" \
  --expression-attribute-values \
    "{\":id\":{\"S\":\"celeb_001\"},\":prefix\":{\"S\":\"tmdb#\"}}" \
  --region us-east-1
```

### 4. Query All Data for Celebrity

**Purpose**: Get metadata + all scraper entries

**Query Pattern**:
```python
response = table.query(
    KeyConditionExpression='celebrity_id = :id',
    ExpressionAttributeValues={
        ':id': 'celeb_001'
    }
)

# Returns:
# - 1 metadata record (source_type#timestamp = metadata#...)
# - N scraper records (source_type#timestamp = google_search#..., tmdb#..., etc.)
```

**CLI Equivalent**:
```bash
aws dynamodb query --table-name celebrity-database \
  --key-condition-expression "celebrity_id = :id" \
  --expression-attribute-values "{\":id\":{\"S\":\"celeb_001\"}}" \
  --region us-east-1
```

### 5. Search by Celebrity Name (Using GSI)

**Purpose**: Find celebrity by name

**Query Pattern**:
```python
response = table.query(
    IndexName='name-index',
    KeyConditionExpression='#n = :name',
    ExpressionAttributeNames={'#n': 'name'},
    ExpressionAttributeValues={
        ':name': '周潤發'
    }
)

# Returns all records with this name
# Use to verify celebrity exists before scraping
```

**CLI Equivalent**:
```bash
aws dynamodb query --table-name celebrity-database \
  --index-name name-index \
  --key-condition-expression "name = :name" \
  --expression-attribute-values "{\":name\":{\"S\":\"周潤發\"}}" \
  --region us-east-1
```

### 6. Update Record (Weight/Sentiment - Phase 3)

**Purpose**: Add computed fields after post-processing

**Update Pattern** (Used by Phase 3):
```python
table.update_item(
    Key={
        'celebrity_id': 'celeb_001',
        'source_type#timestamp': 'tmdb#2025-11-07T17:20:00Z'
    },
    UpdateExpression='SET #w = :weight, #s = :sentiment',
    ExpressionAttributeNames={
        '#w': 'weight',
        '#s': 'sentiment'
    },
    ExpressionAttributeValues={
        ':weight': 0.85,
        ':sentiment': 'neutral'
    }
)
```

## DynamoDB Write Requirements

### For Every Scraper Entry:

1. **Must Include Partition & Sort Keys**
   ```
   celebrity_id: "celeb_NNN"
   source_type#timestamp: "{source}#{timestamp}"
   ```

2. **Must Include First-Hand Data Fields**
   ```
   - id: unique identifier
   - name: from source
   - raw_text: COMPLETE unprocessed response
   - source: API endpoint URL
   - timestamp: ISO 8601
   ```

3. **Must Initialize Null Fields**
   ```
   - weight: null (will be computed)
   - sentiment: null (will be computed)
   ```

4. **Must Include Metadata**
   ```
   metadata.scraper_name: "scraper-{source}"
   metadata.source_type: "{source}"
   metadata.processed: false
   metadata.error: null
   ```

## Query Patterns by Stage

### Stage 2.1: Google Search

```
Write Key: google_search#{timestamp}
Query Pattern: celebrity_id = "celeb_NNN" AND source_type#timestamp BEGINS_WITH "google_search#"
Sample Source URL: https://www.googleapis.com/customsearch/v1
```

### Stage 2.2: Instagram

```
Write Key: instagram#{timestamp}
Query Pattern: celebrity_id = "celeb_NNN" AND source_type#timestamp BEGINS_WITH "instagram#"
Sample Source URL: https://www.instagram.com/{handle}
```

### Stage 2.3: Threads

```
Write Key: threads#{timestamp}
Query Pattern: celebrity_id = "celeb_NNN" AND source_type#timestamp BEGINS_WITH "threads#"
Sample Source URL: https://www.threads.net/@{handle}
```

### Stage 2.4: YouTube

```
Write Key: youtube#{timestamp}
Query Pattern: celebrity_id = "celeb_NNN" AND source_type#timestamp BEGINS_WITH "youtube#"
Sample Source URL: https://www.googleapis.com/youtube/v3/channels
```

## Lambda Configuration for DynamoDB Access

### IAM Permissions Required

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:Query",
        "dynamodb:Scan",
        "dynamodb:GetItem"
      ],
      "Resource": "arn:aws:dynamodb:us-east-1:*:table/celebrity-database"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:UpdateItem"
      ],
      "Resource": "arn:aws:dynamodb:us-east-1:*:table/celebrity-database"
    }
  ]
}
```

### Environment Variables for Lambda

```bash
DYNAMODB_TABLE=celebrity-database
AWS_REGION=us-east-1
```

### Python Code Pattern

```python
import boto3
import os

dynamodb = boto3.resource(
    'dynamodb',
    region_name=os.environ.get('AWS_REGION', 'us-east-1')
)

table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])

# Now use table for queries/writes
```

## Data Flow: Phase 1 → Phase 2 → Phase 3

### Phase 1 (Foundation)
```
DynamoDB Table Created
    ↓
100 Metadata Records Seeded (celebrity_id + metadata#...)
    ↓
DynamoDB Streams Enabled
```

### Phase 2 (Scrapers)
```
Scraper Lambda Runs
    ↓
Reads Metadata Record (celebrity_id + metadata#...)
    ↓
Calls External API
    ↓
Creates Scraper Entry (celebrity_id + source#timestamp)
    ↓
Writes to DynamoDB
    ↓
DynamoDB Streams Triggers Event
```

### Phase 3 (Post-Processing)
```
DynamoDB Stream Event Received
    ↓
Post-Processor Lambda Triggered
    ↓
Reads Scraper Entry (raw_text field)
    ↓
Computes Weight & Sentiment
    ↓
Updates Record (weight & sentiment fields)
```

## Monitoring & Verification

### Verify Scraper Entry Was Written

```bash
aws dynamodb get-item \
  --table-name celebrity-database \
  --key '{"celebrity_id":{"S":"celeb_001"},"source_type#timestamp":{"S":"tmdb#2025-11-07T17:20:00Z"}}' \
  --region us-east-1
```

### Count Scraper Entries by Source

```bash
aws dynamodb scan --table-name celebrity-database \
  --filter-expression "begins_with(#key, :source)" \
  --expression-attribute-names "{\"#key\":\"source_type#timestamp\"}" \
  --expression-attribute-values "{\":source\":{\"S\":\"tmdb#\"}}" \
  --select COUNT \
  --region us-east-1
```

### Verify DynamoDB Streams

```bash
aws dynamodb describe-stream \
  --stream-arn "arn:aws:dynamodb:us-east-1:ACCOUNT:table/celebrity-database/stream/2025-11-07T..." \
  --region us-east-1
```

### Monitor Raw_Text Size

```bash
# Check if raw_text is exceeding limits
aws dynamodb query --table-name celebrity-database \
  --key-condition-expression "celebrity_id = :id" \
  --expression-attribute-values "{\":id\":{\"S\":\"celeb_001\"}}" \
  --region us-east-1 | jq '.Items[].raw_text | length'
```

## Troubleshooting

### Issue: Write Fails with Throughput Error

```
Solution: On-Demand billing should auto-scale
Check: Verify table is in On-Demand mode
aws dynamodb describe-table --table-name celebrity-database \
  --query 'Table.BillingModeSummary.BillingMode'
```

### Issue: Query Returns No Metadata Record

```
Solution: Metadata sort key must be exactly "metadata#2025-01-01T00:00:00Z"
Verify: Query with that exact sort key value
aws dynamodb query --table-name celebrity-database \
  --key-condition-expression "celebrity_id = :id AND source_type#timestamp = :key" \
  --expression-attribute-values "{\":id\":{\"S\":\"celeb_001\"},\":key\":{\"S\":\"metadata#2025-01-01T00:00:00Z\"}}"
```

### Issue: Raw_Text Field Contains Null Values

```
Solution: raw_text must be complete JSON string
Fix: json.dumps(api_response) before storing
Wrong: 'raw_text': api_response  # This becomes NULL
Right: 'raw_text': json.dumps(api_response)  # This is a string
```

### Issue: DynamoDB Streams Not Triggering Post-Processor

```
Solution: Check if streams are enabled and configured
Verify:
aws dynamodb describe-table --table-name celebrity-database \
  --query 'Table.StreamSpecification'
# Should show "StreamViewType": "NEW_AND_OLD_IMAGES"
```

## Cost Implications for Phase 2

### Write Operations

- **Per-celebrity scrape**: 1 write = ~100 bytes = 1 write unit
- **All 100 celebrities × 4 sources**: 400 writes/week = ~57 writes/day
- **Cost**: Included in On-Demand pricing (~$0.01 for 10M writes)

### Query Operations

- **Pre-scrape metadata lookup**: 1 query × 100 celebrities = 100 reads/week
- **Post-scrape verification**: 1 query × 100 celebrities = 100 reads/week
- **Cost**: Included in On-Demand pricing (~$0.01 for 10M reads)

### Storage

- **Baseline (Phase 1)**: ~0.5 MB (100 metadata records)
- **After Phase 2 (4 sources)**: ~2-4 MB (400 scraper records @ 5-10 KB each)
- **Cost**: ~$1.25/GB/month × 4 MB = <$0.01/month

**Total Phase 2 Database Cost**: ~$1-2/month (included in existing On-Demand tier)

## Best Practices

1. **Always Store Complete raw_text**
   - No parsing or extraction
   - Full API response as JSON string
   - Enables re-processing in Phase 3

2. **Use Consistent Timestamps**
   - Format: ISO 8601 with Z suffix
   - Example: `2025-11-07T17:20:00Z`
   - Never use milliseconds (DynamoDB limitations)

3. **Implement Idempotent Writes**
   - Safe to run multiple times
   - Same celebrity_id + source_type#timestamp = same data
   - Use PutItem (not UpdateItem) to overwrite

4. **Monitor raw_text Size**
   - DynamoDB item limit: 400 KB
   - Most APIs under 50 KB
   - Warn if exceeding 100 KB

5. **Implement Exponential Backoff**
   - On write failures, retry with delay
   - Cap at 5 retries before marking failure
   - Log all failures for post-mortem

## Integration Checklist

- [ ] Verified `celebrity-database` table exists and is ACTIVE
- [ ] Confirmed 100 metadata records in Phase 1
- [ ] Tested IAM permissions for DynamoDB access
- [ ] Verified DynamoDB Streams are enabled
- [ ] Created Lambda with environment variables set
- [ ] Tested write pattern with test celebrity
- [ ] Verified write succeeded in DynamoDB
- [ ] Confirmed metadata retrieval works
- [ ] Set up CloudWatch logging for DynamoDB operations

---

**Phase 2 Database Integration**: Complete
**Phase 1 Dependency Status**: ✅ Complete
**Ready to Deploy Scrapers**: YES

For questions about Phase 1, see `/phase-1-foundation/PHASE_1_SUCCESS.md`

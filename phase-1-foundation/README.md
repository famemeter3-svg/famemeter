# Phase 1: Foundation - DynamoDB Setup & Celebrity Seeding

## Executive Summary

This phase establishes the central database infrastructure for the entire Celebrity Multi-Source Database System. It creates a DynamoDB table with optimized schema design and seeds it with 100 initial celebrities. This foundation is critical - all subsequent phases depend on successful completion here.

**Critical Path Item**: Do NOT proceed to Phase 2 until Phase 1 is fully validated.

## Overview

Phase 1 accomplishes two primary tasks:
1. **Infrastructure Setup**: Create DynamoDB table with proper schema, indexes, and streaming
2. **Data Initialization**: Populate database with 100 celebrities and validate data integrity

This phase is foundational - any errors here will propagate through all downstream phases.

## Components

### `dynamodb-setup/` - Table Creation & Configuration
Creates the central DynamoDB table with:
- Proper partition and sort key design
- Global Secondary Indexes for efficient querying
- DynamoDB Streams for change tracking
- On-Demand billing for cost optimization
- Point-in-Time Recovery for data protection

**Key Files**:
- `README.md` - Detailed setup instructions
- `table-definition.json` - Complete DynamoDB schema
- `create-table.py` - Main table creation script
- `test-operations.py` - Validation and testing script

### `celebrity-seed/` - Initial Data Population
Initializes the database with 100 celebrities for scraping:
- Structured JSON format with consistent fields
- Proper ID generation and naming conventions
- Batch operations for efficient database writes
- Comprehensive validation and error reporting

**Key Files**:
- `README.md` - Seeding instructions
- `celebrities.json` - 100 celebrity records
- `seed-database.py` - Main seeding script
- `validate-seed.py` - Data validation script

### `schemas/` - Data Structure Documentation
Reference documentation for all data structures used in the system.

### `docs/` - Phase-Specific Documentation
Additional documentation and troubleshooting guides.

## Timeline

**Week 1-2** (10 business days)
- Day 1-2: Setup and validation
- Day 3-4: Table creation and verification
- Day 5-6: Data seeding
- Day 7-8: Validation and testing
- Day 9-10: Documentation and backup verification

## Architecture & Design Principles

### Data Model Design
The DynamoDB table uses a composite key design:

```
Partition Key: celebrity_id
  - String type
  - Format: celeb_NNN (e.g., celeb_001)
  - Enables grouping all data for one celebrity

Sort Key: source_type#timestamp
  - String type
  - Format: {source}#{ISO8601_timestamp}
  - Examples:
    * tmdb#2025-11-07T17:20:00Z
    * wikipedia#2025-11-07T17:21:00Z
    * metadata#2025-01-01T00:00:00Z
  - Enables querying by source and time
```

### Why This Design?

1. **Efficient Queries**
   - All data for one celebrity in one partition
   - Range queries by source and time
   - Supports both GET and complex QUERY operations

2. **Scalability**
   - Even data distribution across partitions
   - On-Demand billing scales automatically
   - No hot partitions from popular celebrities

3. **Performance**
   - Single-digit millisecond latency
   - DynamoDB Streams for change tracking
   - GSI supports additional query patterns

## Complete Data Structure

### Scraper Entry (created by Phase 2)
This is the PRIMARY data structure that gets stored in DynamoDB. Each scraper creates entries following this schema:

```json
{
  "celebrity_id": "celeb_001",
  "source_type#timestamp": "tmdb#2025-11-07T17:20:00Z",
  "id": "scraper_entry_001_tmdb_2025_11_07",
  "name": "Leonardo DiCaprio",
  "raw_text": "{...complete API response or HTML...}",
  "source": "https://api.themoviedb.org/3/person/search",
  "timestamp": "2025-11-07T17:20:00Z",
  "weight": 0.85,
  "sentiment": "neutral",
  "metadata": {
    "scraper_name": "scraper-tmdb",
    "source_type": "tmdb",
    "processed": true,
    "error": null
  }
}
```

### Field Definitions

| Field | Type | When Set | Description | Example |
|-------|------|----------|-------------|---------|
| `celebrity_id` | String | During Scrape | Partition key - groups all data for one celebrity | `celeb_001` |
| `source_type#timestamp` | String | During Scrape | Sort key - source type + ISO8601 timestamp | `tmdb#2025-11-07T17:20:00Z` |
| `id` | String | During Scrape | Unique identifier per scraper entry | `scraper_entry_001_tmdb_2025_11_07` |
| `name` | String | During Scrape | Celebrity name from source (first-hand) | `Leonardo DiCaprio` |
| `raw_text` | String | During Scrape | Raw HTML/JSON response from API (entire response stored) | `{...full API response...}` |
| `source` | String | During Scrape | Source URL where data originated | `https://api.themoviedb.org/3/person/search` |
| `timestamp` | ISO8601 | During Scrape | When data was scraped (first-hand) | `2025-11-07T17:20:00Z` |
| `weight` | Float 0-1 | Post-Processing | Confidence score (computed in Phase 3) | `0.85` |
| `sentiment` | String | Post-Processing | Sentiment classification (computed in Phase 3) | `positive`, `negative`, `neutral` |

### Data Flow Pattern

```
┌─────────────────────────────────────────┐
│     FIRST-HAND (During Scrape)         │
├─────────────────────────────────────────┤
│ ✓ id                                    │
│ ✓ name                                  │
│ ✓ raw_text (entire API response)        │
│ ✓ source                                │
│ ✓ timestamp                             │
│ ✓ metadata.scraper_name                 │
│ ✓ metadata.source_type                  │
└─────────────────────────────────────────┘
           │
           │ Phase 2: Scraper writes to DynamoDB
           │
           ▼
┌─────────────────────────────────────────┐
│  Stored in DynamoDB (waiting)           │
├─────────────────────────────────────────┤
│ weight: null (will be computed)         │
│ sentiment: null (will be computed)      │
└─────────────────────────────────────────┘
           │
           │ DynamoDB Stream triggers
           │ Phase 3: Post-Processor reads entry
           │
           ▼
┌─────────────────────────────────────────┐
│    COMPUTED (Post-Processing)           │
├─────────────────────────────────────────┤
│ ✓ weight (via scoring algorithm)        │
│ ✓ sentiment (via NLP/sentiment analysis)│
│ ✓ metadata.processed = true             │
└─────────────────────────────────────────┘
           │
           │ Phase 3: Post-Processor updates DynamoDB
           │
           ▼
┌─────────────────────────────────────────┐
│  Complete Entry (Ready for API/Frontend)│
├─────────────────────────────────────────┤
│ All first-hand fields: ✓                │
│ All computed fields: ✓                  │
│ Ready for display in Phase 6 Frontend   │
└─────────────────────────────────────────┘
```

### Master Record (Seed Data Only - Phase 1)
The initial celebrity master list is used ONLY for seeding. Once scraped, all data comes from scraper entries above.

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

**Note**: Master records have fixed `source_type#timestamp` of `metadata#2025-01-01T00:00:00Z` to distinguish them from scraper entries

## Key Features

### Global Secondary Indexes (GSI)

**1. name-index**
- Partition Key: `name` (String)
- Use Case: Search celebrities by name
- Projection: ALL attributes
- Billing: On-Demand

**2. source-index**
- Partition Key: `source` (String)
- Sort Key: `timestamp` (String)
- Use Case: Find all entries from a specific source
- Projection: ALL attributes
- Billing: On-Demand

### DynamoDB Streams
- **Status**: Enabled
- **View Type**: NEW_AND_OLD_IMAGES
- **Use Case**: Trigger post-processor Lambda when new entries added
- **Retention**: 24 hours (AWS default)

### Billing Mode
- **Type**: ON_DEMAND
- **Cost**: Pay per request (optimal for variable workloads)
- **Scaling**: Automatic with no provisioning required
- **Estimated Cost**: $1-2/month for 100 celebrities with weekly updates

### Point-in-Time Recovery (PITR)
- **Status**: Enabled
- **Retention**: 35 days
- **Use Case**: Recover from data corruption or accidental deletion
- **Cost**: ~$0.20/month
- **RPO**: 5 minutes

## Success Criteria - Detailed

### ✅ DynamoDB Table Creation
- [ ] Table name: `celebrity-database`
- [ ] Partition key: `celebrity_id` (String)
- [ ] Sort key: `source_type#timestamp` (String)
- [ ] Billing mode: ON_DEMAND (not provisioned)
- [ ] Streams enabled: NEW_AND_OLD_IMAGES view type
- [ ] All attributes indexed: celebrity_id, name, source, timestamp
- [ ] PITR enabled: 35-day retention

**Validation Command**:
```bash
aws dynamodb describe-table --table-name celebrity-database \
  --query 'Table.[TableStatus,BillingModeSummary.BillingMode,StreamSpecification.StreamViewType]'

# Expected output:
# ["ACTIVE", "PAY_PER_REQUEST", "NEW_AND_OLD_IMAGES"]
```

### ✅ Celebrity Seeding
- [ ] 100 celebrities inserted
- [ ] All required fields populated: name, birth_date, nationality, occupation
- [ ] No duplicate IDs
- [ ] All timestamps valid (ISO 8601 format)
- [ ] All entries have is_active=true
- [ ] Celebrity IDs follow pattern: celeb_001 through celeb_100

**Validation Commands**:
```bash
# Count total records
aws dynamodb scan --table-name celebrity-database --select COUNT

# Verify first record
aws dynamodb get-item \
  --table-name celebrity-database \
  --key '{"celebrity_id":{"S":"celeb_001"},"source_type#timestamp":{"S":"metadata#2025-01-01T00:00:00Z"}}'

# Check for duplicates
aws dynamodb scan --table-name celebrity-database \
  --projection-expression "celebrity_id" | jq -r '.Items[].celebrity_id.S' | sort | uniq -d
```

### ✅ GSI Indexes Functional
- [ ] name-index returns results when searching by name
- [ ] source-index returns results when filtering by source
- [ ] Both indexes have correct projection settings
- [ ] Both indexes are in ACTIVE state

**Validation**:
```bash
# Query by name
aws dynamodb query --table-name celebrity-database \
  --index-name name-index \
  --key-condition-expression "name = :name" \
  --expression-attribute-values "{\":name\":{\"S\":\"Leonardo DiCaprio\"}}"

# Query by source
aws dynamodb query --table-name celebrity-database \
  --index-name source-index \
  --key-condition-expression "source = :source" \
  --expression-attribute-values "{\":source\":{\"S\":\"https://api.themoviedb.org\"}}"
```

### ✅ DynamoDB Streams Enabled
- [ ] StreamSpecification enabled
- [ ] StreamViewType = NEW_AND_OLD_IMAGES
- [ ] StreamArn returned when table described
- [ ] Stream receives events from put_item operations

**Validation**:
```bash
aws dynamodb describe-table --table-name celebrity-database \
  --query 'Table.LatestStreamArn'

# Should return an ARN like:
# arn:aws:dynamodb:us-east-1:ACCOUNT_ID:table/celebrity-database/stream/2025-11-07T00:00:00.000
```

### ✅ First-Hand Data Validation (Critical)
- [ ] `id` field populated with unique identifier per scraper entry
- [ ] `name` field contains celebrity name from scraper (first-hand data)
- [ ] `raw_text` field stores COMPLETE API response (entire JSON/HTML, not parsed)
- [ ] `source` field contains source URL where data originated
- [ ] `timestamp` field in ISO 8601 format (when data was scraped)
- [ ] All first-hand fields populated DURING scrape (not null)
- [ ] raw_text can handle large responses (up to 400 KB DynamoDB limit)
- [ ] Retrieved data matches original format exactly

**Validation Checklist**:
```json
{
  "id": "scraper_entry_001_tmdb_2025_11_07",
  "name": "Leonardo DiCaprio",
  "raw_text": "{...COMPLETE API response, not parsed...}",
  "source": "https://api.themoviedb.org/3/person/search",
  "timestamp": "2025-11-07T17:20:00Z",
  "weight": null,
  "sentiment": null
}
```

**Expected Test Results**:
- ✓ raw_text size: 50-200 KB for typical API response
- ✓ raw_text is valid JSON (if from JSON API)
- ✓ name matches what's in raw_text
- ✓ source URL is valid and accessible
- ✓ timestamp parses as ISO 8601

## Error Handling & Robustness

### Table Creation Errors

**Error**: Table already exists
```
Response: ResourceInUseException
Handling: Log warning and skip creation, verify existing table matches schema
Recovery: Use existing table for seeding
```

**Error**: Insufficient IAM permissions
```
Response: AccessDeniedException
Handling: Log error with required permissions, exit gracefully
Recovery: Update IAM role, re-run script
```

**Error**: Region not available
```
Response: InvalidParameterException
Handling: Validate region format, log available regions
Recovery: Use valid region, re-run script
```

**Error**: Service quota exceeded
```
Response: ValidationException
Handling: Check current table count, log quota info
Recovery: Delete unused tables, request quota increase
```

### Seeding Errors

**Error**: Duplicate celebrity ID
```
Response: ConditionalCheckFailedException
Handling: Log error with existing record, skip record
Recovery: Check for ID collisions, use different ID range
```

**Error**: Invalid JSON in celebrities.json
```
Response: JSONDecodeError
Handling: Log line number and content, exit gracefully
Recovery: Fix JSON syntax, re-run script
```

**Error**: Write throughput exceeded (On-Demand mode rare)
```
Response: ProvisionedThroughputExceededException
Handling: Implement exponential backoff, retry with delay
Recovery: Reduce batch size, retry with slower rate
```

**Error**: Network timeout
```
Response: ConnectionError / Timeout
Handling: Log error with timestamp, implement exponential backoff
Recovery: Retry with longer timeout, check network connectivity
```

### Data Validation Errors

**Error**: Missing required fields
```
Validation: Check all fields present before write
Handling: Log missing fields, skip record
Recovery: Correct source data, re-run
```

**Error**: Invalid timestamp format
```
Validation: Verify ISO 8601 format
Handling: Log error with value, skip record
Recovery: Fix timestamp formatting
```

**Error**: Duplicate entries
```
Validation: Check for duplicate celebrity_id values
Handling: Log duplicate, use first occurrence
Recovery: Clean celebrities.json, re-run
```

## Testing Protocol

### Phase 1A: Table Creation Testing

**Step 1: Pre-flight Checks**
```bash
# Verify AWS credentials
aws sts get-caller-identity

# Check region configuration
aws configure list

# List existing tables
aws dynamodb list-tables
```

**Step 2: Create Table**
```bash
cd dynamodb-setup/
python3 create-table.py --region us-east-1
# Expected: Table created or already exists warning
```

**Step 3: Verify Table Structure**
```bash
python3 test-operations.py --table celebrity-database --region us-east-1
# Expected: All validation checks pass
```

**Step 4: Test Write Operations (Single Record)**
```bash
aws dynamodb put-item \
  --table-name celebrity-database \
  --item '{
    "celebrity_id":{"S":"celeb_test"},
    "source_type#timestamp":{"S":"test#2025-11-07T00:00:00Z"},
    "name":{"S":"Test Celebrity"},
    "is_active":{"BOOL":true}
  }'

# Verify write succeeded
aws dynamodb get-item \
  --table-name celebrity-database \
  --key '{"celebrity_id":{"S":"celeb_test"},"source_type#timestamp":{"S":"test#2025-11-07T00:00:00Z"}}'
```

**Step 5: Clean Up Test Data**
```bash
aws dynamodb delete-item \
  --table-name celebrity-database \
  --key '{"celebrity_id":{"S":"celeb_test"},"source_type#timestamp":{"S":"test#2025-11-07T00:00:00Z"}}'
```

### Phase 1B: Data Seeding Testing

**Step 1: Seed Initial Batch**
```bash
cd celebrity-seed/
# Seed with first 10 celebrities only
python3 seed-database.py --region us-east-1 --limit 10
# Expected: ✓ 10 celebrities inserted
```

**Step 2: Validate Batch**
```bash
# Count records
aws dynamodb scan --table-name celebrity-database \
  --filter-expression "attribute_exists(birth_date)" \
  --select COUNT

# Should show count = 10
```

**Step 3: Test Read Operations**
```bash
# Query by celebrity_id
aws dynamodb query --table-name celebrity-database \
  --key-condition-expression "celebrity_id = :id" \
  --expression-attribute-values "{\":id\":{\"S\":\"celeb_001\"}}"

# Query by name (using GSI)
aws dynamodb query --table-name celebrity-database \
  --index-name name-index \
  --key-condition-expression "name = :name" \
  --expression-attribute-values "{\":name\":{\"S\":\"Leonardo DiCaprio\"}}"
```

**Step 4: Test Stream Events**
```bash
# Get stream ARN
STREAM_ARN=$(aws dynamodb describe-table \
  --table-name celebrity-database \
  --query 'Table.LatestStreamArn' \
  --output text)

# Get stream records (verify events generated)
aws dynamodbstreams describe-stream --stream-arn $STREAM_ARN
```

**Step 5: **STOP IF ERRORS FOUND**
If any validation fails:
- Log all error details
- Check CloudWatch logs
- Verify AWS credentials and permissions
- **Do NOT proceed to seeding all 100** until first 10 fully validated
- Fix errors and re-run validation

**Step 6: Seed Full Dataset**
Once first 10 verified successfully:
```bash
python3 seed-database.py --region us-east-1
# Expected: ✓ All 100 celebrities inserted successfully
```

**Step 7: Final Validation**
```bash
# Verify all 100 records
aws dynamodb scan --table-name celebrity-database \
  --filter-expression "attribute_exists(celebrity_id)" \
  --select COUNT

# Should return Count: 100

# Check for duplicates
python3 validate-seed.py --table celebrity-database --region us-east-1
# Expected: ✓ No duplicates found
# Expected: ✓ All required fields present
# Expected: ✓ Data integrity verified
```

### Phase 1C: Index & Stream Testing

**Step 1: Test GSI - name-index**
```bash
# Search by name
aws dynamodb query --table-name celebrity-database \
  --index-name name-index \
  --key-condition-expression "name = :name" \
  --expression-attribute-values "{\":name\":{\"S\":\"Leonardo DiCaprio\"}}"

# Verify result matches expected celebrity
# Verify index is in ACTIVE state
aws dynamodb describe-table --table-name celebrity-database \
  --query 'Table.GlobalSecondaryIndexes[0]'
```

**Step 2: Test GSI - source-index**
```bash
# This will work after Phase 2 when scrapers add data
# For now, verify index structure exists
aws dynamodb describe-table --table-name celebrity-database \
  --query 'Table.GlobalSecondaryIndexes[1]'
```

**Step 3: Test DynamoDB Streams**
```bash
# Verify streams enabled
aws dynamodb describe-table --table-name celebrity-database \
  --query 'Table.StreamSpecification'

# Expected output:
# {
#     "StreamEnabled": true,
#     "StreamViewType": "NEW_AND_OLD_IMAGES"
# }
```

## Fallback & Recovery Strategies

### Table Already Exists
**Scenario**: Running create-table.py twice
```
Detection: ResourceInUseException
Response: Check if existing table matches schema
Action: Use existing table, skip creation, proceed to seeding
```

### Partial Seeding Completed
**Scenario**: Script fails after seeding 50 celebrities
```
Detection: Scan table, count records < 100
Response: Identify which celebrities were seeded (check IDs celeb_001-celeb_050)
Action: Resume seeding starting from celeb_051
Recovery: Implement resume logic that skips already-seeded records
```

### Corrupted Data
**Scenario**: Invalid data in DynamoDB
```
Detection: Validation script finds inconsistencies
Response: Enable PITR and restore from known good snapshot
Action: Restore to point before corruption, re-seed
```

### Network Interruption During Seeding
**Scenario**: Connection drops mid-operation
```
Detection: Timeout or connection reset error
Response: Implement exponential backoff and retry
Action: Check which records were written, resume from last successful
```

## Coding Principles & Best Practices

### Error Handling
✅ **Implemented**:
- Try-catch blocks for all AWS API calls
- Graceful error messages (not cryptic exceptions)
- Logging at DEBUG, INFO, WARNING, ERROR levels
- Exponential backoff for transient failures
- Fallback paths for common errors

### Data Validation
✅ **Implemented**:
- Pre-write validation (check all required fields)
- Post-write verification (read back and compare)
- Data type validation (string, number, list, etc.)
- Format validation (ISO 8601 timestamps, ID patterns)
- Duplicate detection

### Robustness
✅ **Implemented**:
- Idempotent operations (safe to run multiple times)
- Partial failure handling (continue if some records fail)
- Retry logic with exponential backoff
- Comprehensive logging for debugging
- Health checks before operations

### Performance
✅ **Implemented**:
- Batch operations (25 items per batch max)
- Connection reuse (single boto3 client)
- Minimal API calls
- Efficient queries using GSI
- On-Demand billing (no cold starts)

### Security
✅ **Implemented**:
- IAM role-based authentication (no hardcoded keys)
- Encryption at rest (DynamoDB default)
- Encryption in transit (HTTPS)
- Environment variables for configuration
- No sensitive data in logs

### Documentation
✅ **Implemented**:
- Inline code comments for complex logic
- Docstrings for all functions
- README for setup and usage
- Error codes with explanations
- Example commands and outputs

## Troubleshooting

### Problem: "NoCredentialsError"
**Cause**: AWS credentials not configured
**Solution**:
```bash
aws configure
# or
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
```

### Problem: "UnauthorizedOperation"
**Cause**: IAM role lacks DynamoDB permissions
**Solution**:
```bash
# Add this policy to IAM role:
{
  "Effect": "Allow",
  "Action": [
    "dynamodb:CreateTable",
    "dynamodb:PutItem",
    "dynamodb:Query",
    "dynamodb:Scan",
    "dynamodb:GetItem",
    "dynamodb:DescribeTable",
    "dynamodb:UpdateContinuousBackups"
  ],
  "Resource": "arn:aws:dynamodb:*:*:table/celebrity-database*"
}
```

### Problem: "ResourceLimitExceeded"
**Cause**: Too many tables created
**Solution**:
```bash
# Check current tables
aws dynamodb list-tables

# Delete unused tables
aws dynamodb delete-table --table-name old-table-name
```

### Problem: "ValidationException: One or more parameter values were invalid"
**Cause**: Invalid attribute types or names
**Solution**:
- Verify attribute names match schema
- Ensure data types match (String vs Number)
- Check timestamp format (must be ISO 8601)

## Current Implementation Status

### ✅ Completed
- [x] Directory structure created
- [x] DynamoDB setup scripts (create-table.py)
- [x] Celebrity seed data (celebrities.json)
- [x] Seed script (seed-database.py)
- [x] Complete error handling

### 🟡 In Progress
- [ ] Running initial tests
- [ ] Verifying table creation
- [ ] Seeding 100 celebrities
- [ ] Validation testing

### ⏳ Not Started
- [ ] Phase 2 (Scrapers)

## Next Phase

**Phase 2: Data Source Scrapers** (Week 3-6)
- Deploy Lambda scrapers for TMDb, Wikipedia, News, Social Media
- Implement data collection from each source
- Validate scraped data matches expected schema

**Do NOT proceed until**:
- ✅ DynamoDB table fully created
- ✅ 100 celebrities seeded
- ✅ All validation tests passing
- ✅ GSI and Streams confirmed working

## References

- Project Plan: `../../project-updated.md`
- AWS DynamoDB Docs: https://docs.aws.amazon.com/dynamodb/
- Boto3 DynamoDB: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb.html
- Best Practices: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html

## Contact & Support

For issues:
1. Check troubleshooting section above
2. Review error message and log
3. Consult project-updated.md
4. Check AWS documentation
5. Verify IAM permissions

---

**Phase 1 Status**: Ready for Implementation
**Created**: November 7, 2025
**Last Updated**: November 7, 2025

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working on Phase 3 Post-Processing in this repository.

## Phase 3 Overview

**Phase 3: Post-Processing & Semantic Enrichment** transforms raw scraped data from Phase 2 into enriched, analyzed data with computed fields. This is an intelligence layer that adds value to first-hand data without modifying the original sources.

**Key Responsibility**: Enrich every scraper entry with 4 computed fields:
1. `weight` (0-1) - Confidence/reliability score based on data completeness and source
2. `sentiment` (string) - Emotional tone classification (positive/negative/neutral)
3. `cleaned_text` (string) - Formatted readable text extracted from raw API responses
4. `summary` (string) - Concise one-line summary for quick scanning

**Status**: ✅ Production-ready documentation | 🟡 Gemini integration pending deployment

## Architecture

### How Phase 3 Works

```
Phase 2 Scrapers Write to DynamoDB
  ↓
DynamoDB Streams captures INSERT/MODIFY events
  ↓
Stream automatically triggers Lambda (post-processor)
  ↓
Lambda processes records in batches (up to 100 per invocation)
  ↓
For each entry:
  1. Extract raw_text and source URL
  2. Calculate weight (completeness + source reliability)
  3. Analyze sentiment (TextBlob or AWS Comprehend)
  4. Generate cleaned_text via Gemini API
  5. Generate summary via Gemini API
  ↓
Update DynamoDB with all computed fields
  ↓
Log success/failure
```

### Key Design Principles

- **Event-driven**: Triggered automatically by DynamoDB Streams, no polling
- **Stateless**: No persistent state, safe to retry
- **Graceful degradation**: Partial failures don't fail entire batch
- **Cost-optimized**: Uses free Gemini API with rate limiting
- **Async**: Batch processing (100 records per Lambda invocation)

## File Structure

```
phase-3-post-processing/
├── CLAUDE.md                          - This file (Phase 3 guidance)
├── README.md                          - Comprehensive Phase 3 specification (1,500+ lines)
└── post-processor/
    ├── lambda_function.py             - Main Lambda handler (313 lines, production-ready)
    ├── requirements.txt               - Dependencies (3 packages + Gemini)
    └── (tests/ and scripts/ pending)
```

## Technology Stack

- **Runtime**: Python 3.11
- **AWS Services**: Lambda, DynamoDB, DynamoDB Streams, Secrets Manager, CloudWatch
- **Dependencies**:
  - `boto3` (AWS SDK)
  - `textblob` (Sentiment analysis fallback)
  - `google.generativeai` (Gemini API integration)
- **External**: Google Gemini API (free tier)

## Computed Fields Reference

### 1. Weight (Confidence Score)

**Type**: Float (0.0 - 1.0)

**Purpose**: Quantify how confident we are in an entry's quality

**Formula**: `weight = (completeness_score × 0.5) + (source_reliability_score × 0.5)`

**Completeness Score** (0-1):
- Counts non-empty JSON fields divided by total fields
- Poor data (malformed JSON): 0.3 fallback
- Typical range: 0.3 - 1.0

**Source Reliability Score** (fixed per source):
- TMDb API: 0.95 (well-structured, validated data)
- Wikipedia: 0.90 (community-edited, stable)
- YouTube: 0.85 (official API, good structure)
- News APIs: 0.85 (aggregators, may have bias)
- Instagram/Twitter: 0.75 (social media, variable quality)
- Unknown sources: 0.50 (default neutral)

**Examples**:
- Complete TMDb response: `(1.0 × 0.5) + (0.95 × 0.5) = 0.975` → High confidence
- Partial Wikipedia: `(0.5 × 0.5) + (0.90 × 0.5) = 0.70` → Good confidence
- Malformed response: `(0.3 × 0.5) + (0.5 × 0.5) = 0.40` → Low confidence

### 2. Sentiment (Emotional Tone)

**Type**: String (enum: "positive", "negative", "neutral")

**Purpose**: Classify emotional tone of content

**Method A: TextBlob (Default)**
- Fast, local, no cost
- Uses polarity score (-1.0 to +1.0)
- Thresholds: `> 0.1` = positive, `< -0.1` = negative, else = neutral
- Limited accuracy for complex texts

**Method B: AWS Comprehend (Optional)**
- Higher accuracy, understands context and sarcasm
- Requires API call (slower, ~$0.0001 per 100 units)
- Toggle with `USE_AWS_COMPREHEND=true` env var

**Text Extraction**:
- JSON: Extract all string values and join them
- Plain text: Use raw_text as-is
- Limit to 500 chars for performance

**Fallback**: "neutral" (safe default when extraction fails)

### 3. Cleaned Text (Formatted Readable Text)

**Type**: String (max 2000 chars)

**Purpose**: Extract human-readable, formatted text from raw API responses

**Source**: Gemini API `gemini-1.5-flash`

**Process**:
1. Extract text pieces from raw JSON
2. Send to Gemini with prompt: "Clean and format this text about [celebrity]. Focus on readability, remove technical jargon."
3. Return 2-3 sentence formatted response
4. Limit to 2000 chars

**Example**:
```
Raw JSON: {"items": [{"title": "Leonardo DiCaprio", "snippet": "Oscar-winning actor..."}]}
Cleaned Text: "Leonardo DiCaprio is an acclaimed actor known for roles in major films..."
```

**Fallback**: Empty string (if Gemini fails, field is empty but entry still valid)

### 4. Summary (One-Line Summary)

**Type**: String (max 300 chars)

**Purpose**: Concise one-line summary for quick scanning

**Source**: Gemini API `gemini-1.5-flash`

**Process**:
1. Take cleaned_text (from field 3)
2. Send to Gemini with prompt: "Create one-sentence summary about [celebrity]. Focus on most newsworthy information."
3. Enforce single sentence (truncate after first period if needed)
4. Limit to 300 chars

**Examples**:
- Activity: "DiCaprio releases climate-focused documentary on ocean conservation."
- Film: "DiCaprio cast in $200M superhero film releasing in 2026."
- Social: "DiCaprio's environmental post receives 2M likes."

**Fallback**: Empty string (if Gemini fails, field is empty but entry still valid)

## Environment Variables

```bash
# DynamoDB Configuration
AWS_REGION=us-east-1
DYNAMODB_TABLE=celebrity-database
LOG_LEVEL=INFO

# Sentiment Analysis
USE_AWS_COMPREHEND=false          # true = AWS Comprehend, false = TextBlob (default)
AWS_COMPREHEND_REGION=us-east-1  # If using Comprehend

# Gemini API Configuration
GEMINI_API_KEY=your_api_key       # From Google AI Studio (free)
GEMINI_MODEL=gemini-1.5-flash     # Fast model, free tier eligible
GEMINI_ENABLED=true                # Enable Gemini for cleaned_text & summary
GEMINI_TIMEOUT=30                  # Seconds to wait for response

# Text Processing Limits
MAX_TEXT_LENGTH=5000               # Max chars to send to Gemini
CLEANED_TEXT_MAX_LENGTH=2000       # Max chars for cleaned_text output
SUMMARY_MAX_LENGTH=300             # Max chars for summary output
```

## Lambda Configuration

| Setting | Value | Rationale |
|---------|-------|-----------|
| Function Name | `post-processor` | Clear, descriptive |
| Runtime | Python 3.11 | Latest stable, good performance |
| Memory | 1024 MB | Sufficient for text processing + API calls |
| Timeout | 15 minutes | Allows batch processing of 100 records |
| Trigger | DynamoDB Streams | Automatic on data arrival |
| Batch Size | 100 | Efficient batch processing |
| Starting Position | LATEST | Don't reprocess old data |

## IAM Permissions Required

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetRecords",
        "dynamodb:GetShardIterator",
        "dynamodb:DescribeStream",
        "dynamodb:ListStreams",
        "dynamodb:ListStreamConsumers"
      ],
      "Resource": "arn:aws:dynamodb:*:*:table/celebrity-database/stream/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:UpdateItem"
      ],
      "Resource": "arn:aws:dynamodb:*:*:table/celebrity-database"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "comprehend:DetectSentiment"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:*:*:secret:gemini/*"
    }
  ]
}
```

## Essential Commands

### Setup & Configuration

```bash
# Verify AWS credentials and region
aws sts get-caller-identity
aws configure get region

# Create Gemini API secret in Secrets Manager
aws secretsmanager create-secret \
  --name gemini/api-key \
  --secret-string "your_gemini_api_key"

# Verify DynamoDB table exists and has streams enabled
aws dynamodb describe-table --table-name celebrity-database \
  --query 'Table.[TableStatus, LatestStreamArn]'
```

### Local Testing

```bash
# Install dependencies
pip3 install -r post-processor/requirements.txt

# Test weight calculation alone
python3 -c "from post-processor.lambda_function import calculate_weight; print(calculate_weight('{\"a\": 1, \"b\": 2}', 'api.themoviedb.org'))"

# Test sentiment analysis alone
python3 -c "from post-processor.lambda_function import calculate_sentiment; print(calculate_sentiment('I love this movie!'))"

# Test with 1 entry (manual)
aws dynamodb put-item --table-name celebrity-database \
  --item '{
    "celebrity_id": {"S": "celeb_test"},
    "source_type#timestamp": {"S": "test#2025-11-09T00:00:00Z"},
    "raw_text": {"S": "{\"title\": \"Test\", \"bio\": \"Test bio\"}"},
    "source": {"S": "test.api"},
    "timestamp": {"S": "2025-11-09T00:00:00Z"}
  }'

# Monitor Lambda logs
aws logs tail /aws/lambda/post-processor --follow
```

### Testing Phase 3

```bash
# Test 1: Verify weight calculation works
python3 << 'EOF'
from post_processor.lambda_function import calculate_weight
tests = [
    ('{"a":1,"b":2,"c":3}', 'api.themoviedb.org', 0.97),
    ('invalid json', 'unknown.api', 0.4),
]
for raw_text, source, expected in tests:
    result = calculate_weight(raw_text, source)
    status = "✓" if abs(result - expected) < 0.05 else "✗"
    print(f"{status} weight({source}) = {result}")
EOF

# Test 2: Verify sentiment classification
python3 << 'EOF'
from post_processor.lambda_function import calculate_sentiment
tests = [
    ('I love this amazing movie!', 'positive'),
    ('This is terrible and awful.', 'negative'),
    ('Leonardo DiCaprio is an actor.', 'neutral'),
]
for text, expected in tests:
    result = calculate_sentiment(text)
    status = "✓" if result == expected else "✗"
    print(f"{status} sentiment: {result}")
EOF

# Test 3: Insert test entry and verify processing
TEST_ID="celeb_001"
TEST_TIMESTAMP="test#2025-11-09T12:00:00Z"

aws dynamodb put-item --table-name celebrity-database \
  --item "{
    \"celebrity_id\": {\"S\": \"$TEST_ID\"},
    \"source_type#timestamp\": {\"S\": \"$TEST_TIMESTAMP\"},
    \"raw_text\": {\"S\": \"{\\\"name\\\": \\\"Test\\\", \\\"bio\\\": \\\"Test biography\\\"}\"},
    \"source\": {\"S\": \"test.api\"},
    \"timestamp\": {\"S\": \"2025-11-09T12:00:00Z\"}
  }"

# Wait for stream processing (5-15 seconds)
sleep 10

# Verify computed fields were added
aws dynamodb get-item --table-name celebrity-database \
  --key "{\"celebrity_id\": {\"S\": \"$TEST_ID\"}, \"source_type#timestamp\": {\"S\": \"$TEST_TIMESTAMP\"}}" \
  --query 'Item.[weight,sentiment,cleaned_text,summary]'

# Test 4: Query DynamoDB for entry counts by source
aws dynamodb scan --table-name celebrity-database \
  --filter-expression "attribute_exists(weight)" \
  --select COUNT
```

### Debugging & Monitoring

```bash
# View Lambda execution logs (last 1 hour)
aws logs tail /aws/lambda/post-processor --follow --since 1h

# Filter for errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/post-processor \
  --filter-pattern "ERROR" \
  --query 'events[].message'

# Filter for Gemini-specific logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/post-processor \
  --filter-pattern "Gemini" \
  --query 'events[].message'

# Check Lambda invocations (last hour)
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=post-processor \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum

# Check Lambda errors (last hour)
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=post-processor \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum

# Check Lambda average duration
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=post-processor \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average,Maximum
```

### DynamoDB Queries

```bash
# Count entries with computed fields
aws dynamodb scan --table-name celebrity-database \
  --filter-expression "attribute_exists(weight) AND attribute_exists(sentiment)" \
  --select COUNT

# Find entries missing computed fields (should be minimal)
aws dynamodb scan --table-name celebrity-database \
  --filter-expression "attribute_not_exists(weight) OR attribute_not_exists(sentiment)" \
  --select COUNT

# Check weight distribution
aws dynamodb scan --table-name celebrity-database \
  --filter-expression "attribute_exists(weight)" \
  --projection-expression "weight" \
  --query 'Items[*].weight.N' | jq 'length'

# Check sentiment distribution
aws dynamodb scan --table-name celebrity-database \
  --filter-expression "attribute_exists(sentiment)" \
  --projection-expression "sentiment" \
  --query 'Items[*].sentiment.S | group_by(.) | map({sentiment: .[0], count: length})'

# Get sample entry with all computed fields
aws dynamodb scan --table-name celebrity-database \
  --filter-expression "attribute_exists(weight) AND attribute_exists(sentiment) AND attribute_exists(cleaned_text)" \
  --limit 1 \
  --query 'Items[0]'
```

## Testing Protocol

### Phase 3A: Unit Testing (Local)

**Goal**: Verify individual functions work correctly

```bash
# 1. Test weight calculation with edge cases
pytest tests/test_weight.py -v

# 2. Test sentiment analysis with various inputs
pytest tests/test_sentiment.py -v

# 3. Test Gemini API integration
pytest tests/test_gemini.py -v

# 4. Test error handling and fallbacks
pytest tests/test_error_handling.py -v
```

### Phase 3B: Integration Testing (With DynamoDB)

**Goal**: Verify Lambda processes DynamoDB Stream events correctly

**Step 1**: Insert 1 test entry
```bash
aws dynamodb put-item --table-name celebrity-database \
  --item '{
    "celebrity_id": {"S": "celeb_001"},
    "source_type#timestamp": {"S": "tmdb#2025-11-09T12:00:00Z"},
    "raw_text": {"S": "{\"id\": 287462, \"name\": \"Leonardo DiCaprio\", \"popularity\": 24.28}"},
    "source": {"S": "https://api.themoviedb.org"},
    "timestamp": {"S": "2025-11-09T12:00:00Z"}
  }'
```

**Step 2**: Wait 10-15 seconds for Lambda processing
```bash
sleep 15
```

**Step 3**: Verify ALL computed fields are populated
```bash
aws dynamodb get-item --table-name celebrity-database \
  --key '{"celebrity_id":{"S":"celeb_001"},"source_type#timestamp":{"S":"tmdb#2025-11-09T12:00:00Z"}}' \
  --query 'Item.[weight,sentiment,cleaned_text,summary]'
```

**Step 4**: Check Lambda logs for details
```bash
aws logs tail /aws/lambda/post-processor --follow
```

**Expected Output**:
```
[0.975, "neutral", "Leonardo DiCaprio is an Oscar-winning actor...", "Acclaimed actor known for major film roles."]
```

**Step 5**: **STOP HERE if errors found**
- Review Lambda logs for error details
- Check IAM permissions
- Verify DynamoDB Streams are enabled
- Fix issues before proceeding

**Step 6**: Test with 10 entries
```bash
# Insert 10 test entries for different celebrities
for i in {1..10}; do
  aws dynamodb put-item --table-name celebrity-database \
    --item "{\"celebrity_id\":{\"S\":\"celeb_00$i\"},\"source_type#timestamp\":{\"S\":\"test#2025-11-09T12:00:0${i}Z\"},\"raw_text\":{\"S\":\"{\\\"name\\\":\\\"Celebrity $i\\\"}\"},\"source\":{\"S\":\"test.api\"},\"timestamp\":{\"S\":\"2025-11-09T12:00:0${i}Z\"}}"
done

sleep 20

# Verify all have computed fields
aws dynamodb scan --table-name celebrity-database \
  --filter-expression "attribute_exists(weight) AND attribute_exists(sentiment)" \
  --select COUNT
```

### Phase 3C: Production Validation

**Goal**: Ensure Phase 3 works correctly with real Phase 2 data

**Step 1**: Check data population
```bash
# Count entries processed by Phase 3
aws dynamodb scan --table-name celebrity-database \
  --filter-expression "attribute_exists(weight)" \
  --select COUNT

# Expected: Should match number of entries Phase 2 wrote
```

**Step 2**: Validate data quality
```bash
# Check for invalid weights
aws dynamodb scan --table-name celebrity-database \
  --filter-expression "weight < :zero OR weight > :one" \
  --expression-attribute-values '{":zero":{"N":"0"},":one":{"N":"1"}}' \
  --select COUNT

# Expected: 0 (all weights should be 0.0-1.0)
```

**Step 3**: Validate sentiment values
```bash
# Check for invalid sentiments
aws dynamodb scan --table-name celebrity-database \
  --filter-expression "sentiment NOT IN ('positive', 'negative', 'neutral')" \
  --select COUNT

# Expected: 0 (all should be valid enum values)
```

**Step 4**: Monitor Lambda metrics
```bash
# Check error rate
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=post-processor \
  --start-time $(date -u -d '1 day ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum

# Expected: <1% error rate
```

## Development Workflow

### Before Starting

- [ ] Read the full `README.md` in this directory
- [ ] Understand DynamoDB table structure (see root CLAUDE.md)
- [ ] Have AWS credentials configured: `aws sts get-caller-identity`
- [ ] Verify DynamoDB table exists: `aws dynamodb describe-table --table-name celebrity-database`
- [ ] Check if DynamoDB Streams are enabled
- [ ] Get Gemini API key from https://ai.google.dev

### During Development

- [ ] Install dependencies: `pip3 install -r post-processor/requirements.txt`
- [ ] Create `.env` file with environment variables
- [ ] Test weight calculation locally first
- [ ] Test sentiment analysis with various inputs
- [ ] Test Gemini API integration (if implementing cleaned_text/summary)
- [ ] Review Lambda logs continuously: `aws logs tail /aws/lambda/post-processor --follow`
- [ ] Test with 1 entry first, verify all 4 fields
- [ ] Test with 10 entries, check error rate
- [ ] Review CloudWatch metrics for anomalies

### Before Committing

- [ ] All unit tests pass: `pytest tests/ -v`
- [ ] Integration test passes with 10+ entries
- [ ] No errors in Lambda logs (expected: 100% success rate)
- [ ] Weight values all in 0.0-1.0 range
- [ ] Sentiment values all valid (positive/negative/neutral)
- [ ] Cleaned_text fields populated (>90% of entries)
- [ ] Summary fields populated (>90% of entries)
- [ ] Environment variables documented
- [ ] Requirements.txt updated with all dependencies
- [ ] No API keys in code (use Secrets Manager)

## Critical Implementation Notes

### Weight Calculation

```python
# CORRECT - Uses weighted average of two factors
weight = (completeness_score * 0.5) + (source_reliability * 0.5)

# WRONG - Don't use simple average
weight = (completeness_score + source_reliability) / 2  # ❌

# WRONG - Don't multiply them together
weight = completeness_score * source_reliability  # ❌
```

### Sentiment Fallback Chain

```python
# Prefer TextBlob (free, no cost)
# Fall back to AWS Comprehend if USE_AWS_COMPREHEND=true
# If both fail, use "neutral" as safe default

# WRONG - Fail entire batch if sentiment analysis fails
if sentiment_fails:
    raise Exception("Cannot continue")  # ❌

# CORRECT - Continue with fallback
try:
    sentiment = analyze_sentiment(text)
except:
    sentiment = "neutral"  # ✓
```

### Gemini API Handling

```python
# WRONG - Block entire batch on Gemini timeout
try:
    cleaned_text = call_gemini()
except TimeoutError:
    raise Exception("Gemini timeout")  # ❌

# CORRECT - Continue with empty fields
try:
    cleaned_text = call_gemini()
except TimeoutError:
    cleaned_text = ""  # ✓ - entry still valid with weight/sentiment
```

### DynamoDB Update

```python
# CORRECT - Use UpdateExpression for efficient updates
table.update_item(
    Key={...},
    UpdateExpression="SET #weight = :weight, #sentiment = :sentiment",
    ExpressionAttributeNames={'#weight': 'weight'},
    ExpressionAttributeValues={':weight': 0.85}
)  # ✓

# WRONG - Don't read entire item, modify, write back
item = table.get_item(Key={...})
item['weight'] = 0.85
table.put_item(Item=item)  # ❌ - inefficient, overwrites other fields
```

## Common Issues & Solutions

### Issue: "Table not found"
```bash
# Solution: Verify DynamoDB table exists
aws dynamodb describe-table --table-name celebrity-database

# If not found, create it (Phase 1)
cd ../phase-1-foundation/dynamodb-setup/
python3 create-table.py --region us-east-1
```

### Issue: "DynamoDB Streams not enabled"
```bash
# Check if streams are enabled
aws dynamodb describe-table --table-name celebrity-database \
  --query 'Table.LatestStreamArn'

# If null/empty, enable streams in AWS Console or via:
aws dynamodb update-table --table-name celebrity-database \
  --stream-specification StreamEnabled=true,StreamViewType=NEW_AND_OLD_IMAGES
```

### Issue: "Lambda not triggered by DynamoDB Streams"
```bash
# Get stream ARN
STREAM_ARN=$(aws dynamodb describe-table --table-name celebrity-database \
  --query 'Table.LatestStreamArn' --output text)

# Create event source mapping
aws lambda create-event-source-mapping \
  --event-source-arn $STREAM_ARN \
  --function-name post-processor \
  --enabled \
  --batch-size 100 \
  --starting-position LATEST
```

### Issue: "Gemini API returns 401 Unauthorized"
```bash
# Verify API key is valid
GEMINI_KEY=$(aws secretsmanager get-secret-value --secret-id gemini/api-key \
  --query SecretString --output text)

python3 << 'EOF'
import google.generativeai as genai
genai.configure(api_key=os.environ.get('GEMINI_API_KEY'))
response = genai.models.generate_content(model='gemini-1.5-flash', contents='Test')
print("✓ Valid" if response.text else "✗ Invalid")
EOF
```

### Issue: "Gemini API rate limit (429)"
```bash
# Solution: Increase wait time between requests
# Update GEMINI_TIMEOUT to 60 seconds
# Reduce batch size from 100 to 50
# Implement exponential backoff in code

# Monitor current usage
echo "Check usage at: https://aistudio.google.com/app/apikey"
```

### Issue: "Weight values outside 0-1 range"
```bash
# Solution: Add validation before updating
weight = max(0.0, min(1.0, weight))  # Clamp to [0.0, 1.0]

# Debug: Check source reliability mapping
print(f"Completeness: {completeness}")
print(f"Reliability: {reliability}")
print(f"Weight: {weight}")
```

### Issue: "Sentiment always returns 'neutral'"
```bash
# Check if text extraction is working
text = extract_text(raw_text)
print(f"Extracted: {text[:100]}")

# If empty, raw_text may be malformed
# Try different text extraction logic

# Switch to AWS Comprehend for debugging
USE_AWS_COMPREHEND=true
```

## Performance Considerations

### Lambda Optimization

| Setting | Impact | Recommendation |
|---------|--------|-----------------|
| Memory | CPU allocated scales with memory | 1024 MB minimum for Gemini calls |
| Batch Size | More records = faster processing | 100 (default) for optimal balance |
| Timeout | Must fit batch processing time | 15 minutes for 100 records |
| Parallelization | Concurrent invocations | 10 (default) for smooth processing |

### Cost Optimization

| Service | Monthly Cost | Notes |
|---------|--------------|-------|
| Lambda | ~$0.70 | DynamoDB Streams trigger, <1M requests |
| DynamoDB Streams | Free | Included with table |
| Gemini API | Free | Up to 60 req/min, 4M tokens/min free tier |
| AWS Comprehend | ~$0.50 | Only if USE_AWS_COMPREHEND=true |
| **Total** | **~$1.20** | Very cost-effective |

## Data Validation Rules

| Field | Validation | Action if Invalid |
|-------|-----------|-------------------|
| weight | 0.0 ≤ weight ≤ 1.0 | Clamp to range |
| sentiment | ∈ {positive, negative, neutral} | Default to "neutral" |
| cleaned_text | String, ≤ 2000 chars | Truncate if needed |
| summary | String, ≤ 300 chars, ≤ 2 sentences | Truncate to first sentence |
| timestamp | ISO 8601 format | Use current time if invalid |

## Monitoring & Alerting

### Key Metrics to Track

```bash
# Invocation rate (should spike during scraper runs)
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=post-processor \
  --start-time $(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 86400 \
  --statistics Sum

# Error rate (should stay < 1%)
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=post-processor \
  --period 3600 \
  --statistics Sum
```

### CloudWatch Alarms to Create

```bash
# Alert on high error rate
aws cloudwatch put-metric-alarm \
  --alarm-name post-processor-high-errors \
  --alarm-description "Alert if error rate > 5%" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold

# Alert on high duration
aws cloudwatch put-metric-alarm \
  --alarm-name post-processor-slow \
  --alarm-description "Alert if duration > 60 seconds" \
  --metric-name Duration \
  --namespace AWS/Lambda \
  --statistic Maximum \
  --period 300 \
  --threshold 60000 \
  --comparison-operator GreaterThanThreshold
```

## Gemini API Setup

### Step 1: Get Free API Key

1. Go to https://ai.google.dev
2. Click "Get API Key" or "Sign In"
3. Create new project if needed
4. Enable Generative AI API
5. Copy the API key

### Step 2: Store in Secrets Manager

```bash
aws secretsmanager create-secret \
  --name gemini/api-key \
  --secret-string "your_api_key_here"
```

### Step 3: Configure Lambda

Add to Lambda environment variables:
```
GEMINI_API_KEY=from-secrets-manager
GEMINI_MODEL=gemini-1.5-flash
GEMINI_ENABLED=true
```

### Step 4: Test Connectivity

```bash
python3 << 'EOF'
import google.generativeai as genai
import os

api_key = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=api_key)

try:
    response = genai.models.generate_content(
        model='gemini-1.5-flash',
        contents='Test: Say "Gemini is working"'
    )
    print(f"✓ Gemini API working: {response.text}")
except Exception as e:
    print(f"✗ Gemini API failed: {str(e)}")
EOF
```

## References

- **Root CLAUDE.md**: `/README.md` - Project-wide architecture and patterns
- **Phase 3 Specification**: `README.md` - Complete Phase 3 documentation (1,500+ lines)
- **Lambda Function**: `post-processor/lambda_function.py` - Implementation (313 lines)
- **Dependencies**: `post-processor/requirements.txt` - Python packages
- **DynamoDB**: See root CLAUDE.md for DynamoDB patterns
- **Google Gemini**: https://ai.google.dev
- **AWS DynamoDB Streams**: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Streams.html
- **AWS Lambda**: https://docs.aws.amazon.com/lambda/

## Key Takeaways

1. **Event-Driven**: Phase 3 runs automatically when Phase 2 writes data
2. **Graceful Degradation**: Partial failures don't break the entire batch
3. **Four Computed Fields**: weight, sentiment, cleaned_text, summary
4. **Cost-Effective**: Uses free Gemini API, ~$1.20/month
5. **Testable**: Test with 1 → 10 entries before production
6. **Secure**: All API keys stored in Secrets Manager, not in code
7. **Idempotent**: Safe to retry failed records
8. **Monitored**: CloudWatch logs and metrics for visibility

---

**Phase 3 Status**: ✅ Documentation Complete | 🟡 Gemini Implementation Pending
**Created**: November 9, 2025
**Last Updated**: November 9, 2025
**For**: Claude Code AI Agent


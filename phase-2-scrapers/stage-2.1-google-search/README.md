# Stage 2.1: Google Search API - Simple Text Cleaning

## Overview

Stage 2.1 collects search results and basic information about celebrities using Google Search API with straightforward raw text cleaning. This is the simplest and most accessible data collection stage.

## Purpose
Collect search results and basic information about celebrities using Google Search API with straightforward raw text cleaning.

## Data Source
- **Source**: Google Custom Search API or Google Search with SERP parsing
- **API Tier**: Free tier (100 searches/day) or paid ($0.05 per search)
- **Data**: Search results, snippets, basic information, news references
- **Rate Limiting**: 100 requests/day (free), higher with paid tier
- **Status**: ✅ Production Ready

## Lambda Configuration

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

## Data Collection Flow

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
   ├─ Populate: id, name, raw_text, source, timestamp
   ├─ Initialize: weight = null, sentiment = null
   └─ Add metadata

5. WRITE to DynamoDB
   ├─ Key: celebrity_id + google_search#timestamp
   ├─ Exponential backoff on failure
   └─ Verify write succeeded

6. RETURN Status
   ├─ Success: {status: 'success'}
   └─ Error: {status: 'error', error: message}
```

## Implementation

### Raw Text Cleaning

```python
def clean_raw_text(response_data):
    """
    Clean raw Google API response.
    - Normalize whitespace
    - Remove null bytes
    - Ensure valid UTF-8 encoding
    - Preserve structure of JSON
    """
    import re
    import json

    try:
        data = json.loads(response_data) if isinstance(response_data, str) else response_data
        cleaned = json.dumps(data, ensure_ascii=False)
        return cleaned
    except:
        text = str(response_data)
        text = re.sub(r'\s+', ' ', text)
        text = text.encode('utf-8', 'ignore').decode('utf-8')
        return text
```

### Main Lambda Handler

```python
import requests
from datetime import datetime
import uuid
import json
import os
import boto3

dynamodb = boto3.resource('dynamodb')

def fetch_google_search_data(celebrity_name, api_key, search_engine_id):
    """Fetch search results from Google Custom Search API."""
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        'q': celebrity_name,
        'key': api_key,
        'cx': search_engine_id,
        'num': 10
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return {
            'success': True,
            'raw_text': json.dumps(data),
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
    table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])
    api_key = os.environ['GOOGLE_API_KEY']
    search_engine_id = os.environ['GOOGLE_SEARCH_ENGINE_ID']

    # Get all celebrities
    celebrities = get_all_celebrities(table)

    results = []
    for celeb in celebrities:
        try:
            google_result = fetch_google_search_data(
                celeb['name'],
                api_key,
                search_engine_id
            )

            if google_result['success']:
                scraper_entry = {
                    "id": str(uuid.uuid4()),
                    "name": celeb['name'],
                    "raw_text": google_result['raw_text'],
                    "source": "https://www.googleapis.com/customsearch/v1",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "weight": None,
                    "sentiment": None
                }

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

## Error Handling

| Error | Scenario | Handling | Recovery | Fallback |
|-------|----------|----------|----------|----------|
| **Timeout** | API doesn't respond within 10s | Log timeout | Retry 3x with backoff (1s, 2s, 4s) | Skip celebrity |
| **Invalid Key** | API key invalid/expired | Log error, don't retry | Verify in Secrets Manager | Exit scraper |
| **Rate Limit (429)** | Too many requests | Check Retry-After header | Exponential backoff | Skip remaining |
| **Malformed Response** | Invalid JSON | Log sample, validate | Store raw text anyway | Skip celebrity |
| **DynamoDB Failure** | Write fails | Log error with details | Retry with backoff | Skip entry |

## Testing Protocol

### Phase 2.1A: API Key Setup

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
cd stage-2.1-google-search/
cp .env.template .env
# Edit .env and add:
# GOOGLE_API_KEY=your_actual_key
# GOOGLE_SEARCH_ENGINE_ID=your_engine_id
# DYNAMODB_TABLE=celebrity-database
```

**Step 3: Test with Single Celebrity (Offline)**
```bash
python3 lambda_function.py --test-mode --celebrity "Leonardo DiCaprio"
# Expected: ✓ Function runs without crashes
# Expected: ✓ Error handling works
# Expected: ✓ Logging is clear
```

### Phase 2.1B: Test Single Celebrity (Online)

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

### Phase 2.1C: Verify Data in DynamoDB

```bash
aws dynamodb query --table-name celebrity-database \
  --key-condition-expression "celebrity_id = :id" \
  --expression-attribute-values "{\":id\":{\"S\":\"celeb_001\"}}" \
  --query 'Items[] | [?begins_with(source_type#timestamp, `google_search`)]'

# Expected: google_search entry with id, name, raw_text, source, timestamp
# - raw_text contains valid JSON from Google API
# - weight and sentiment are null
```

### Phase 2.1D: STOP IF ERRORS

- [ ] Log all CloudWatch errors
- [ ] Check API key validity and quota
- [ ] Verify IAM role has DynamoDB permissions
- [ ] **DO NOT proceed to batch test** until this passes
- [ ] Fix errors and re-run

### Phase 2.1E: Batch Testing (5 Celebrities)

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

### Phase 2.1F: Full Deployment (100 Celebrities)

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

# Expected: 100 entries
```

## File Structure

```
stage-2.1-google-search/
├── README.md                 # This file
├── lambda_function.py        # Main scraper code
├── requirements.txt          # Python dependencies
├── test_scraper.py          # Local testing script
├── .env.template            # Environment variables template
└── config.json             # Configuration (optional)
```

## Dependencies

```
requests==2.31.0
boto3==1.28.0
python-dateutil==2.8.2
```

## Cost Estimate

- **Free Tier**: $0/month (100 searches/day)
- **Paid Tier**: ~$0.05 per search × 100 celebrities = $5/month for weekly updates

**Total: $0-2/month**

## Timeline

**Week 3**:
- [ ] Code implementation
- [ ] Testing with 1, 5, then 100 celebrities
- [ ] Validation and debugging

## Status

- ✅ Architecture documented
- ⏳ Implementation pending
- ⏳ Testing pending

---

**Created**: November 7, 2025
**Version**: 1.0
**Status**: Ready for Implementation

# Stage 2.4: YouTube API - Official API Integration

## Overview

Stage 2.4 collects YouTube channel and video data using the official YouTube Data API v3 for reliable, authorized data collection. This is the most straightforward and stable of all stages.

## Purpose
Collect YouTube channel and video data using the official YouTube Data API for reliable, authorized data collection with generous rate limits.

## Data Source
- **Source**: YouTube Data API v3
- **API Tier**: Free tier (10,000 quota units/day)
- **Data**: Channel subscribers, video count, view count, upload stats
- **Rate Limiting**: Quota-based (generous free tier)
- **Status**: ✅ Production Ready

## Lambda Configuration

**Function Name**: `scraper-youtube`
- **Runtime**: Python 3.11
- **Memory**: 512 MB
- **Timeout**: 5 minutes
- **Trigger**: EventBridge (weekly)

**Environment Variables**:
```bash
YOUTUBE_API_KEY=your_api_key_here
DYNAMODB_TABLE=celebrity-database
AWS_REGION=us-east-1
LOG_LEVEL=INFO
YOUTUBE_TIMEOUT=10
```

## Data Collection Flow

```
1. GET Celebrity from DynamoDB
   ├─ Extract: name, celebrity_id
   ├─ Get YouTube channel handle (if stored)
   └─ Validate: handle not empty

2. SEARCH YouTube API
   ├─ Use /search endpoint with celebrity name
   ├─ Filter for channels
   ├─ Get channel ID from results
   └─ Timeout after 10 seconds

3. FETCH Channel Data
   ├─ Use /channels endpoint
   ├─ Get: subscriber count, view count, video count
   ├─ Get: upload playlist ID
   └─ Get: latest upload date

4. PARSE Response
   ├─ Validate JSON response format
   ├─ Extract required fields
   ├─ Store complete raw response
   └─ Check for API errors

5. CREATE Scraper Entry (FIRST-HAND)
   ├─ id, name, raw_text, source, timestamp
   ├─ raw_text contains complete API response
   └─ weight = null, sentiment = null

6. WRITE to DynamoDB
   └─ Key: celebrity_id + youtube#timestamp

7. RETURN Status
   └─ Success/Error with video count
```

## Implementation

### Main Lambda Handler

```python
import requests
import json
import uuid
from datetime import datetime
import os
import boto3

dynamodb = boto3.resource('dynamodb')

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"

def search_youtube_channel(celebrity_name, api_key):
    """Search for celebrity YouTube channel."""
    url = f"{YOUTUBE_API_BASE}/search"
    params = {
        'q': celebrity_name,
        'part': 'snippet',
        'type': 'channel',
        'key': api_key,
        'maxResults': 1
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()

        if data.get('items') and len(data['items']) > 0:
            channel_id = data['items'][0]['id']['channelId']
            return {'channel_id': channel_id, 'error': None}
        else:
            return {'channel_id': None, 'error': 'Channel not found'}

    except requests.Timeout:
        return {'channel_id': None, 'error': 'API timeout'}
    except Exception as e:
        return {'channel_id': None, 'error': str(e)}

def fetch_channel_data(channel_id, api_key):
    """Fetch detailed channel information."""
    url = f"{YOUTUBE_API_BASE}/channels"
    params = {
        'id': channel_id,
        'part': 'snippet,statistics,contentDetails',
        'key': api_key
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        return {
            'success': True,
            'raw_text': json.dumps(data),
            'channel_data': data.get('items', [{}])[0]
        }

    except requests.HTTPError as e:
        return {
            'success': False,
            'error': f'HTTP {e.response.status_code}',
            'raw_text': None
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'raw_text': None
        }

def lambda_handler(event, context):
    table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])
    api_key = os.environ['YOUTUBE_API_KEY']

    # Get all celebrities
    celebrities = get_all_celebrities(table)

    results = []
    for celeb in celebrities:
        try:
            # Search for YouTube channel
            search_result = search_youtube_channel(celeb['name'], api_key)

            if not search_result['channel_id']:
                results.append({
                    'celebrity_id': celeb['celebrity_id'],
                    'status': 'not_found',
                    'error': search_result['error']
                })
                continue

            # Fetch channel data
            channel_result = fetch_channel_data(search_result['channel_id'], api_key)

            if channel_result['success']:
                # Create scraper entry (FIRST-HAND)
                scraper_entry = {
                    'id': str(uuid.uuid4()),
                    'name': celeb['name'],
                    'raw_text': channel_result['raw_text'],
                    'source': 'https://www.googleapis.com/youtube/v3/channels',
                    'timestamp': datetime.utcnow().isoformat() + 'Z',
                    'weight': None,
                    'sentiment': None
                }

                # Write to DynamoDB
                table.put_item(Item={
                    'celebrity_id': celeb['celebrity_id'],
                    'source_type#timestamp': f"youtube#{scraper_entry['timestamp']}",
                    **scraper_entry
                })

                # Extract subscriber count for logging
                channel_data = channel_result['channel_data']
                subscriber_count = channel_data.get('statistics', {}).get('subscriberCount', 'hidden')

                results.append({
                    'celebrity_id': celeb['celebrity_id'],
                    'status': 'success',
                    'subscribers': subscriber_count,
                    'channel_id': search_result['channel_id']
                })
            else:
                results.append({
                    'celebrity_id': celeb['celebrity_id'],
                    'status': 'error',
                    'error': channel_result['error']
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
        'not_found': len([r for r in results if r['status'] == 'not_found']),
        'details': results
    }
```

## Error Handling

| Error | Scenario | Handling | Recovery | Fallback |
|-------|----------|----------|----------|----------|
| **Channel Not Found** | No YouTube channel | Log warning | None | Skip celebrity |
| **Quota Exceeded** | 10k daily quota hit | Check usage | Wait 24 hours | Continue |
| **Invalid API Key** | Key invalid/expired | Log error | Verify in Secrets | Exit scraper |
| **Timeout** | API not responding | Retry | Exponential backoff | Skip |
| **API Error** | Service error | Log error | Retry once | Skip |

## Testing Protocol

### Phase 2.4A: API Key Setup

**Step 1: Obtain API Key**
```bash
# 1. Visit https://console.cloud.google.com
# 2. Create project "celebrity-database"
# 3. Enable YouTube Data API v3
# 4. Create API key (Credentials > Create API Key)
# 5. Copy API key
```

**Step 2: Configure Environment**
```bash
cd stage-2.4-youtube/
cp .env.template .env
# Edit .env and add:
# YOUTUBE_API_KEY=your_actual_key
# DYNAMODB_TABLE=celebrity-database
```

### Phase 2.4B: Test Single Celebrity

```bash
aws lambda invoke \
  --function-name scraper-youtube-dev \
  --payload '{"celebrities":[{"celebrity_id":"celeb_003","name":"Kylie Jenner"}]}' \
  response.json

cat response.json | jq '.'
# Expected: Success with subscriber count
```

### Phase 2.4C: Verify Data

```bash
aws dynamodb query --table-name celebrity-database \
  --key-condition-expression "celebrity_id = :id" \
  --expression-attribute-values "{\":id\":{\"S\":\"celeb_003\"}}" \
  --query 'Items[] | [?begins_with(source_type#timestamp, `youtube`)]'

# Expected: YouTube entry with:
# - raw_text containing complete API response
# - source: https://www.googleapis.com/youtube/v3/channels
```

### Phase 2.4D: Batch Testing (5 Celebrities)

```bash
aws lambda invoke \
  --function-name scraper-youtube-dev \
  --payload '{"limit": 5}' \
  response.json

# Expected: Likely 4-5 successful (most celebrities have YouTube)
```

### Phase 2.4E: Full Deployment (100 Celebrities)

```bash
aws lambda update-function-code \
  --function-name scraper-youtube \
  --zip-file fileb://function.zip

aws lambda invoke \
  --function-name scraper-youtube \
  --payload '{}' \
  response.json

# Final verification
aws dynamodb scan --table-name celebrity-database \
  --filter-expression "begins_with(#key, :source)" \
  --expression-attribute-names "{\"#key\":\"source_type#timestamp\"}" \
  --expression-attribute-values "{\":source\":{\"S\":\"youtube#\"}}" \
  --select COUNT

# Expected: 80-100 entries (most celebrities have YouTube)
```

### Phase 2.4F: Monitor Quota

```bash
# Check API quota usage
# Dashboard: https://console.cloud.google.com

# Typical daily consumption:
# - 100 celebrities × 2 API calls = 200 quota units
# - Leaves 9,800 units for retries and other use

# Quota resets at 00:00 PT daily
```

## File Structure

```
stage-2.4-youtube/
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
```

## Cost Estimate

- **YouTube Data API**: Free (within quota limits)
- **Lambda**: Minimal (5 min timeout)

**Total: Free**

## Timeline

**Week 6**:
- [ ] Code implementation
- [ ] Testing with 1, 5, then 100 celebrities
- [ ] Validation
- [ ] All 4 stages running in parallel

## Status

- ✅ Architecture documented
- ⏳ Implementation pending
- ⏳ Testing pending

---

**Created**: November 7, 2025
**Version**: 1.0
**Status**: Ready for Implementation

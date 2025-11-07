# Celebrity Multi-Source Database System
## Project Overview

A personal research tool for aggregating celebrity data from multiple sources using AWS serverless architecture. The system will collect, store, and manage data for 100 celebrities (initially) with 100+ data points per person, updated weekly.

**Architecture Pattern**: Microservices-based event-driven architecture with Lambda functions per data source
**Update Frequency**: Weekly batch processing
**Target Scale**: 100 celebrities → 1,000 celebrities
**Cost Priority**: Minimize AWS costs through serverless architecture

---

## System Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────────────────────┐
│                      EventBridge Scheduler                       │
│                   (Weekly Cron: Every Sunday)                    │
└────────────┬────────────────────────────────────────────────────┘
             │
             │ Triggers all Lambda scrapers
             ▼
┌────────────────────────────────────────────────────────────────────┐
│                    DATA SOURCE LAYER (Lambdas)                      │
├─────────────┬─────────────┬──────────────┬──────────────┬─────────┤
│  Lambda 1   │  Lambda 2   │   Lambda 3   │   Lambda 4   │  Lambda n│
│   TMDb API  │ Wiki Scraper│ News API     │ Social Stats │   ...   │
└──────┬──────┴──────┬──────┴──────┬───────┴──────┬───────┴─────┬───┘
       │             │              │              │             │
       │             │              │              │             │
       ▼             ▼              ▼              ▼             ▼
┌────────────────────────────────────────────────────────────────────┐
│                         DynamoDB                                    │
│              Single Source of Truth Database                        │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────┐      │
│  │ Partition Key: celebrity_id (e.g., "celeb_001")         │      │
│  │ Sort Key: source_type#timestamp                         │      │
│  │                                                          │      │
│  │ Scraper Entry Data Structure:                           │      │
│  │ ┌─────────────────────────────────────────────────┐    │      │
│  │ │ FIRST-HAND DATA (collected during scrape):      │    │      │
│  │ │ • id - unique entry identifier                  │    │      │
│  │ │ • name - celebrity name from source             │    │      │
│  │ │ • raw_text - raw HTML/JSON response             │    │      │
│  │ │ • source - source URL                           │    │      │
│  │ │ • timestamp - when data was scraped             │    │      │
│  │ └─────────────────────────────────────────────────┘    │      │
│  │                                                          │      │
│  │ ┌─────────────────────────────────────────────────┐    │      │
│  │ │ COMPUTED DATA (post-processing):                │    │      │
│  │ │ • weight - confidence score (0-1)               │    │      │
│  │ │ • sentiment - positive/negative/neutral         │    │      │
│  │ └─────────────────────────────────────────────────┘    │      │
│  │                                                          │      │
│  │ Each scraper creates separate entries per source        │      │
│  │ Examples:                                               │      │
│  │ - celeb_001 + tmdb#2025-11-07 → TMDb data entry       │      │
│  │ - celeb_001 + wikipedia#2025-11-07 → Wiki entry       │      │
│  │ - celeb_001 + news#2025-11-07 → News entry            │      │
│  │ - celeb_001 + social#2025-11-07 → Social entry        │      │
│  └─────────────────────────────────────────────────────────┘      │
└────────────┬───────────────────────────────────────────────────────┘
             │
             │ DynamoDB Streams
             ▼
┌────────────────────────────────────────────────────────────────────┐
│              Lambda - Post-Processing Handler                       │
│    (Computes weight & sentiment for each scraper entry)            │
└────────────────────────────────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────────────────┐
│                      API LAYER                                      │
│                   API Gateway (REST)                                │
│                                                                     │
│  Endpoints:                                                        │
│  - GET  /celebrities (list all with filters)                      │
│  - GET  /celebrities/{id} (get single celebrity)                  │
│  - PUT  /celebrities/{id} (manual edit)                           │
│  - GET  /celebrities/{id}/sources (all scraper entries)           │
│  - GET  /celebrities/{id}/source/{source} (source-specific data)  │
│  - POST /celebrities (add new celebrity)                          │
│  - POST /refresh/{id} (trigger manual refresh)                    │
└────────────┬───────────────────────────────────────────────────────┘
             │
             │ HTTPS
             ▼
┌────────────────────────────────────────────────────────────────────┐
│                    FRONTEND DASHBOARD                               │
│                     React SPA (S3 + CloudFront)                     │
│                                                                     │
│  Features:                                                         │
│  - Celebrity list with search/filter                               │
│  - Detailed celebrity profile view                                 │
│  - Data source tabs (TMDb, Wiki, News, Social)                    │
│  - Display weight & sentiment for each source                      │
│  - Manual edit interface                                           │
│  - Data freshness indicators                                       │
│  - Refresh triggers                                                │
└────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Foundation (Week 1-2)

### Step 1.1: DynamoDB Table Setup ⚡
**Goal**: Create the central database with proper schema design

**Tasks**:
- [ ] Create DynamoDB table `celebrity-database`
- [ ] Configure partition key: `celebrity_id` (String)
- [ ] Configure sort key: `source_type#timestamp` (String)
- [ ] Set billing mode to **On-Demand** (pay per request - cheapest for weekly updates)
- [ ] Enable DynamoDB Streams (for change tracking)
- [ ] Create GSI (Global Secondary Index):
  - `name-index`: For searching by celebrity name
  - `source-index`: For querying by data source

**Modified Data Model** (Updated Schema):

Each scraper entry contains the following core fields:

```json
{
  "celebrity_id": "celeb_001",
  "source_type#timestamp": "tmdb#2025-11-07T17:20:00Z",
  "id": "scraper_entry_001_tmdb_2025_11_07",
  "name": "Leonardo DiCaprio",
  "raw_text": "Raw HTML/JSON response from TMDb API: {\"adult\": false, \"also_known_as\": [...], ...}",
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

**Field Definitions**:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `id` | String | Unique identifier for each scraper entry | `scraper_entry_001_tmdb_2025_11_07` |
| `name` | String | Celebrity name extracted/first-hand from scraper | `Leonardo DiCaprio` |
| `raw_text` | String | Raw response from data source (HTML/JSON) | `{...full API response...}` |
| `source` | String | Source URL where data originated | `https://api.themoviedb.org/3/person/search` |
| `timestamp` | ISO 8601 String | When the data was scraped (first-hand) | `2025-11-07T17:20:00Z` |
| `weight` | Float (0-1) | Confidence/importance score (computed post-scrape) | `0.85` |
| `sentiment` | String | Sentiment classification (computed post-scrape) | `positive`, `negative`, `neutral` |

**Field Collection Pattern**:

```
┌─────────────────────────────────────────┐
│     FIRST-HAND (During Scrape)         │
├─────────────────────────────────────────┤
│ ✓ id                                    │
│ ✓ name                                  │
│ ✓ raw_text                              │
│ ✓ source                                │
│ ✓ timestamp                             │
└─────────────────────────────────────────┘
           │
           │ Processed by Post-Processing Lambda
           ▼
┌─────────────────────────────────────────┐
│    COMPUTED (Post-Processing Stage)     │
├─────────────────────────────────────────┤
│ ✓ weight (via scoring algorithm)        │
│ ✓ sentiment (via NLP/Sentiment analysis)│
└─────────────────────────────────────────┘
```

**DynamoDB Table Structure**:

```json
{
  "TableName": "celebrity-database",
  "AttributeDefinitions": [
    {
      "AttributeName": "celebrity_id",
      "AttributeType": "S"
    },
    {
      "AttributeName": "source_type#timestamp",
      "AttributeType": "S"
    },
    {
      "AttributeName": "name",
      "AttributeType": "S"
    },
    {
      "AttributeName": "source",
      "AttributeType": "S"
    }
  ],
  "KeySchema": [
    {
      "AttributeName": "celebrity_id",
      "KeyType": "HASH"
    },
    {
      "AttributeName": "source_type#timestamp",
      "KeyType": "RANGE"
    }
  ],
  "BillingMode": "PAY_PER_REQUEST",
  "StreamSpecification": {
    "StreamViewType": "NEW_AND_OLD_IMAGES"
  },
  "GlobalSecondaryIndexes": [
    {
      "IndexName": "name-index",
      "KeySchema": [
        {
          "AttributeName": "name",
          "KeyType": "HASH"
        }
      ],
      "Projection": {
        "ProjectionType": "ALL"
      }
    },
    {
      "IndexName": "source-index",
      "KeySchema": [
        {
          "AttributeName": "source",
          "KeyType": "HASH"
        },
        {
          "AttributeName": "timestamp",
          "KeyType": "RANGE"
        }
      ],
      "Projection": {
        "ProjectionType": "ALL"
      }
    }
  ]
}
```

**For Each Scraper - Data Capture Workflow**:

Each scraper Lambda function follows this pattern:

```python
# Step 1: FIRST-HAND Data Collection (During Scrape)
scraper_entry = {
    "id": generate_unique_id(),  # Unique per entry
    "name": extract_from_source(),  # e.g., name from API response
    "raw_text": json.dumps(api_response),  # Store raw response
    "source": source_url,  # Where the data came from
    "timestamp": datetime.utcnow().isoformat() + "Z",  # When scraped
}

# Step 2: Write to DynamoDB
dynamodb.put_item(
    Item={
        "celebrity_id": celebrity_id,
        "source_type#timestamp": f"{scraper_name}#{scraper_entry['timestamp']}",
        **scraper_entry,
        "weight": None,  # Will be computed later
        "sentiment": None  # Will be computed later
    }
)

# Step 3: Post-Processing (Separate Lambda or Phase 2)
# - Compute weight via algorithm
# - Compute sentiment via NLP
# - Update DynamoDB with computed fields
```

**Testing Criteria**:
- ✅ Table created successfully
- ✅ Can write sample scraper entry with all fields
- ✅ Can read entry by `celebrity_id`
- ✅ GSI query works for name search
- ✅ GSI query works for source search
- ✅ Streams are capturing changes
- ✅ Raw text field stores large JSON responses correctly

**Cost Estimate**: ~$1-2/month for 100 celebrities with weekly updates

---

### Step 1.2: Celebrity Master List Setup
**Goal**: Initialize the database with 100 celebrities

**Tasks**:
- [ ] Create `celebrities-seed.json` with initial 100 celebrities
- [ ] Include: name, birth_date, nationality, occupation
- [ ] Create Lambda function `seed-database` to bulk insert
- [ ] Run seed function once

**Sample Seed Data**:
```json
[
  {
    "celebrity_id": "celeb_001",
    "name": "Leonardo DiCaprio",
    "birth_date": "1974-11-11",
    "nationality": "American",
    "occupation": ["Actor", "Producer"]
  },
  {
    "celebrity_id": "celeb_002",
    "name": "Taylor Swift",
    "birth_date": "1989-12-13",
    "nationality": "American",
    "occupation": ["Singer", "Songwriter"]
  }
  // ... 98 more
]
```

**Testing Criteria**:
- ✅ Seed function runs without errors
- ✅ All 100 records inserted
- ✅ Can query any celebrity by ID
- ✅ Can search by name via GSI

---

## Phase 2: Data Source Scrapers (Week 3-6)

### Step 2.1: Lambda Scraper 1 - TMDb API 🎬
**Goal**: Collect filmography and movie data

**Data Sources**:
- TMDb API (The Movie Database): https://www.themoviedb.org/
- Free tier: 1000 requests/day
- Data: Movies, TV shows, credits, popularity scores

**Lambda Function**: `scraper-tmdb`
- **Runtime**: Python 3.11
- **Memory**: 512 MB
- **Timeout**: 5 minutes
- **Trigger**: EventBridge (weekly)

**Tasks**:
- [ ] Register for TMDb API key
- [ ] Create Lambda function
- [ ] Install `requests` library via Lambda Layer
- [ ] Implement API calls:
  - Search person by name
  - Get person details
  - Get movie credits
  - Get popularity metrics
- [ ] Parse and structure data
- [ ] Write to DynamoDB with fields: `id`, `name`, `raw_text`, `source`, `timestamp`
- [ ] Add error handling and retry logic
- [ ] Implement rate limiting (max 10 requests/second)

**Code Structure**:
```python
import boto3
import requests
import json
from datetime import datetime
import uuid

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('celebrity-database')

TMDB_API_KEY = os.environ['TMDB_API_KEY']
TMDB_BASE_URL = "https://api.themoviedb.org/3"

def lambda_handler(event, context):
    # Get all celebrities from DynamoDB
    celebrities = get_all_celebrities()
    
    results = []
    for celeb in celebrities:
        try:
            # Search TMDb for celebrity
            tmdb_data = fetch_tmdb_data(celeb['name'])
            
            # Create scraper entry (FIRST-HAND data)
            scraper_entry = {
                "id": str(uuid.uuid4()),
                "name": tmdb_data.get("name", celeb['name']),
                "raw_text": json.dumps(tmdb_data),
                "source": f"{TMDB_BASE_URL}/person/search",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "weight": None,  # Will be computed in post-processing
                "sentiment": None  # Will be computed in post-processing
            }
            
            # Update DynamoDB
            update_celebrity_data(celeb['celebrity_id'], 'tmdb', scraper_entry)
            
            results.append({
                'celebrity_id': celeb['celebrity_id'],
                'status': 'success'
            })
            
            # TEST: Log after each celebrity
            print(f"✓ Updated {celeb['name']} with TMDb data")
            
        except Exception as e:
            # TEST: Report errors immediately
            print(f"✗ ERROR for {celeb['name']}: {str(e)}")
            results.append({
                'celebrity_id': celeb['celebrity_id'],
                'status': 'error',
                'error': str(e)
            })
    
    # TEST: Return summary
    return {
        'total': len(celebrities),
        'success': len([r for r in results if r['status'] == 'success']),
        'errors': len([r for r in results if r['status'] == 'error']),
        'details': results
    }

def fetch_tmdb_data(celebrity_name):
    # Implementation details...
    pass

def update_celebrity_data(celebrity_id, scraper_name, scraper_entry):
    timestamp = scraper_entry['timestamp']
    table.put_item(
        Item={
            'celebrity_id': celebrity_id,
            'source_type#timestamp': f"{scraper_name}#{timestamp}",
            **scraper_entry
        }
    )
```

**Testing Criteria**:
- ✅ Test with 1 celebrity first (e.g., Leonardo DiCaprio)
- ✅ Verify data written to DynamoDB correctly with all fields
- ✅ Check that `id`, `name`, `raw_text`, `source`, `timestamp` are populated
- ✅ Test error handling with invalid celebrity name
- ✅ Test with 5 celebrities
- ✅ Review logs for any issues
- ✅ **STOP if any errors - report bugs before proceeding**
- ✅ If all pass, run for all 100 celebrities

**Cost Estimate**: ~$0.10/month (100 celebrities × 4 weeks × $0.20 per 1M requests)

---

### Step 2.2: Lambda Scraper 2 - Wikipedia 📚
**Goal**: Extract biographical information

**Data Sources**:
- Wikipedia API: https://www.mediawiki.org/wiki/API:Main_page
- Free, no API key required
- Data: Biography, career summary, personal life, awards

**Lambda Function**: `scraper-wikipedia`
- **Runtime**: Python 3.11
- **Memory**: 512 MB
- **Timeout**: 5 minutes
- **Trigger**: EventBridge (weekly)

**Tasks**:
- [ ] Create Lambda function
- [ ] Install `wikipedia-api` library via Layer
- [ ] Implement Wikipedia page search
- [ ] Extract structured data (infobox)
- [ ] Parse biography sections
- [ ] Extract awards and achievements
- [ ] Write to DynamoDB with fields: `id`, `name`, `raw_text`, `source`, `timestamp`
- [ ] Handle disambiguation pages
- [ ] Add caching to avoid repeated requests

**Testing Criteria** (TEST AT EACH STEP):
- ✅ Test with 1 celebrity - verify bio extracted and fields populated
- ✅ Verify `raw_text` contains full Wikipedia response
- ✅ Test with celebrity having disambiguation page
- ✅ Test with 5 celebrities
- ✅ Check error logs
- ✅ **STOP if bugs found - fix before continuing**
- ✅ Run for all 100 celebrities

**Cost Estimate**: ~$0.10/month

---

### Step 2.3: Lambda Scraper 3 - News Aggregation 📰
**Goal**: Collect recent news articles

**Data Sources**:
- NewsAPI: https://newsapi.org/ (Free: 100 requests/day)
- Or Google News RSS feeds (Free, unlimited)
- Data: Recent articles, headlines, sentiment

**Lambda Function**: `scraper-news`
- **Runtime**: Python 3.11
- **Memory**: 512 MB
- **Timeout**: 5 minutes
- **Trigger**: EventBridge (weekly)

**Tasks**:
- [ ] Choose news source (NewsAPI or RSS)
- [ ] Create Lambda function
- [ ] Implement news search by celebrity name
- [ ] Filter articles from last 7 days
- [ ] Extract: title, URL, published date, source
- [ ] Optional: Add sentiment analysis (AWS Comprehend)
- [ ] Write to DynamoDB with fields: `id`, `name`, `raw_text`, `source`, `timestamp`
- [ ] Handle rate limits

**Testing Criteria**:
- ✅ Test with popular celebrity (many articles) - verify `raw_text` has article list
- ✅ Test with less popular celebrity (few articles)
- ✅ Verify article count accuracy
- ✅ Test with 5 celebrities
- ✅ **STOP and report if bugs found**
- ✅ Full run for 100 celebrities

**Cost Estimate**: ~$0.10/month + NewsAPI free tier

---

### Step 2.4: Lambda Scraper 4 - Social Media Stats 📱
**Goal**: Collect follower counts and engagement metrics

**Data Sources**:
- Instagram (via unofficial APIs or web scraping)
- Twitter/X API (Free tier available)
- YouTube API (Free: 10,000 quota/day)
- TikTok (web scraping)

**Note**: Social media APIs have strict rate limits. Start with public aggregator APIs.

**Lambda Function**: `scraper-social`
- **Runtime**: Python 3.11
- **Memory**: 512 MB
- **Timeout**: 5 minutes
- **Trigger**: EventBridge (weekly)

**Tasks**:
- [ ] Research available free social media APIs
- [ ] Create Lambda function
- [ ] Implement data collection for each platform
- [ ] Handle missing social media profiles
- [ ] Calculate engagement rate if possible
- [ ] Write to DynamoDB with fields: `id`, `name`, `raw_text`, `source`, `timestamp`
- [ ] Add robust error handling (many celebrities may not have all platforms)

**Testing Criteria**:
- ✅ Test with celebrity active on all platforms
- ✅ Test with celebrity on only Instagram
- ✅ Test with celebrity with no social media
- ✅ Verify follower counts are reasonable in `raw_text`
- ✅ **STOP if data looks incorrect**
- ✅ Test with 10 celebrities
- ✅ Full run for 100 celebrities

**Cost Estimate**: ~$0.15/month

---

### Step 2.5: Lambda Scrapers 5-10 - Additional Sources 🌐
**Goal**: Expand data coverage

**Potential Sources**:
1. **IMDb** (via web scraping): Ratings, awards, trivia
2. **Spotify API**: Music data for musicians
3. **Forbes/Celebrity Net Worth**: Estimated net worth
4. **Rotten Tomatoes**: Movie/show ratings
5. **Google Trends**: Search popularity
6. **YouTube**: Channel stats, video counts

**Note**: Implement 2-3 additional sources based on data needs

**Testing Protocol for Each**:
1. Test with 1 celebrity
2. Review logs and data quality (ensure all first-hand fields populated)
3. Test with 5 celebrities
4. **STOP if issues - report bugs**
5. Full deployment

**Cost Estimate**: ~$0.10/month per scraper

---

## Phase 3: Post-Processing & Sentiment Analysis (Week 7)

### Step 3.1: Post-Processing Lambda - Weight & Sentiment Computation ⚙️
**Goal**: Compute `weight` and `sentiment` for all scraped data

**Lambda Function**: `post-processor`
- **Runtime**: Python 3.11
- **Memory**: 1024 MB
- **Timeout**: 15 minutes
- **Trigger**: DynamoDB Stream (triggered after scrapers complete)

**Tasks**:
- [ ] Create Lambda function
- [ ] Subscribe to DynamoDB Streams
- [ ] For each new scraper entry:
  - [ ] Compute `weight` (confidence score 0-1)
  - [ ] Compute `sentiment` (positive/negative/neutral)
  - [ ] Update DynamoDB with computed fields
- [ ] Implement scoring algorithms:
  - [ ] Weight: Based on data completeness, source reliability
  - [ ] Sentiment: Using AWS Comprehend or TextBlob
- [ ] Add error handling and retry logic
- [ ] Test at each step

**Weight Calculation Logic**:
```python
def calculate_weight(raw_text, source):
    """
    Calculate confidence score (0-1) based on:
    - Data completeness
    - Source reliability rating
    - Recency of data
    """
    weight = 0.0
    
    # Check data completeness
    try:
        data = json.loads(raw_text)
        field_count = len([v for v in data.values() if v is not None])
        completeness_score = min(field_count / 10, 1.0)  # 0-1
    except:
        completeness_score = 0.3
    
    # Source reliability mapping
    source_reliability = {
        "https://api.themoviedb.org": 0.95,
        "https://en.wikipedia.org": 0.90,
        "newsapi.org": 0.85,
        "twitter.com": 0.80
    }
    
    reliability_score = next(
        (v for k, v in source_reliability.items() if k in source),
        0.5
    )
    
    # Combine scores
    weight = (completeness_score * 0.5) + (reliability_score * 0.5)
    
    return round(weight, 2)

def calculate_sentiment(raw_text):
    """
    Calculate sentiment using AWS Comprehend or TextBlob
    Returns: positive, negative, neutral
    """
    # Implementation using AWS Comprehend or TextBlob
    pass
```

**Sentiment Analysis Logic**:
```python
def calculate_sentiment(raw_text):
    """
    Analyze sentiment of raw text
    Returns: positive, negative, neutral
    """
    from textblob import TextBlob
    
    try:
        # Extract text content from raw_text
        if raw_text.startswith('{'):
            data = json.loads(raw_text)
            # Extract relevant text fields
            text_content = ' '.join([
                str(v) for k, v in data.items() 
                if isinstance(v, str) and k not in ['id', 'raw_text']
            ])
        else:
            text_content = raw_text
        
        # Analyze sentiment
        blob = TextBlob(text_content)
        polarity = blob.sentiment.polarity
        
        if polarity > 0.1:
            return "positive"
        elif polarity < -0.1:
            return "negative"
        else:
            return "neutral"
    except:
        return "neutral"
```

**Testing Criteria**:
- ✅ Test with 1 scraper entry - verify weight and sentiment computed
- ✅ Test with 10 scraper entries from different sources
- ✅ Verify weight scores are between 0-1
- ✅ Verify sentiment is one of: positive, negative, neutral
- ✅ Test error handling for malformed raw_text
- ✅ **STOP if computation produces invalid values**
- ✅ Test with all 100 celebrities × 4 sources
- ✅ Update DynamoDB successfully

**Cost Estimate**: ~$0.20/month

---

## Phase 4: Orchestration & Automation (Week 8)

### Step 4.1: EventBridge Scheduler Setup ⏰
**Goal**: Automate weekly data collection and post-processing

**Tasks**:
- [ ] Create EventBridge rule: `celebrity-weekly-scrape`
- [ ] Set cron schedule: `cron(0 2 ? * SUN *)` (Every Sunday at 2 AM UTC)
- [ ] Add all Lambda scrapers as targets
- [ ] Configure input parameters for each Lambda
- [ ] Set up retry policy (3 retries with exponential backoff)
- [ ] Enable EventBridge logging

**Architecture**:
```
EventBridge Rule (Weekly)
├── Target: Lambda scraper-tmdb
├── Target: Lambda scraper-wikipedia
├── Target: Lambda scraper-news
├── Target: Lambda scraper-social
└── Target: Lambda scraper-[additional]
     └── (After 5 minutes)
         └── Target: Lambda post-processor (triggered by DynamoDB Streams)
```

**Testing Criteria**:
- ✅ Manually trigger EventBridge rule
- ✅ Verify all Lambdas execute in parallel
- ✅ Check CloudWatch Logs for all functions
- ✅ Verify DynamoDB has scraper entries with first-hand fields
- ✅ Wait for post-processor to trigger and verify weight/sentiment added
- ✅ Verify all entries have: id, name, raw_text, source, timestamp, weight, sentiment
- ✅ **STOP if any Lambda fails - investigate before scheduling**
- ✅ Enable weekly schedule

**Cost Estimate**: ~$0.01/month (EventBridge is very cheap)

---

### Step 4.2: DynamoDB Streams Handler 📊
**Goal**: Track changes and log updates

**Lambda Function**: `stream-change-handler`
- **Runtime**: Python 3.11
- **Memory**: 256 MB
- **Timeout**: 1 minute
- **Trigger**: DynamoDB Stream

**Tasks**:
- [ ] Create Lambda function
- [ ] Configure DynamoDB Stream as trigger
- [ ] Process INSERT, MODIFY, REMOVE events
- [ ] Log changes to CloudWatch
- [ ] Optional: Send notifications (SNS/Email) for significant changes
- [ ] Track data freshness metrics

**Testing Criteria**:
- ✅ Manually update a celebrity record
- ✅ Verify stream handler is triggered
- ✅ Check CloudWatch Logs for change record
- ✅ Test with multiple rapid updates
- ✅ **STOP if stream processing fails**

**Cost Estimate**: ~$0.05/month

---

## Phase 5: API Layer (Week 9-10)

### Step 5.1: API Gateway Setup 🔌
**Goal**: Create REST API for frontend access

**API Endpoints**:

| Method | Endpoint | Description | Lambda Backend |
|--------|----------|-------------|-----------------|
| GET | `/celebrities` | List all celebrities (with pagination, filters) | `api-list-celebrities` |
| GET | `/celebrities/{id}` | Get single celebrity details | `api-get-celebrity` |
| GET | `/celebrities/{id}/sources` | Get all scraped data for celebrity | `api-get-all-sources` |
| GET | `/celebrities/{id}/source/{source}` | Get source-specific data | `api-get-source-data` |
| PUT | `/celebrities/{id}` | Update celebrity (manual edits) | `api-update-celebrity` |
| POST | `/celebrities` | Add new celebrity | `api-create-celebrity` |
| POST | `/refresh/{id}` | Trigger manual refresh | `api-refresh-celebrity` |
| DELETE | `/celebrities/{id}` | Delete celebrity | `api-delete-celebrity` |

**Tasks**:
- [ ] Create API Gateway REST API: `celebrity-api`
- [ ] Configure CORS for React frontend
- [ ] Set up request validation
- [ ] Add API key authentication (for security)
- [ ] Create Lambda functions for each endpoint
- [ ] Implement pagination (limit, offset)
- [ ] Add filtering (by name, nationality, occupation)
- [ ] Add sorting options
- [ ] Deploy to stage: `prod`

**Testing Criteria** (TEST EACH ENDPOINT):
- ✅ Test GET `/celebrities` - returns list
- ✅ Test pagination with limit=10
- ✅ Test filtering by name
- ✅ Test GET `/celebrities/celeb_001` - returns details
- ✅ Test GET `/celebrities/celeb_001/sources` - returns all scraper entries
- ✅ Test GET `/celebrities/celeb_001/source/tmdb` - returns TMDb data only
- ✅ Test PUT to update celebrity notes
- ✅ Test POST to create new celebrity
- ✅ **STOP at any endpoint failure - fix bugs**
- ✅ Test all endpoints with Postman
- ✅ Performance test with 100 requests

**Cost Estimate**: ~$0.50/month (assuming low traffic)

---

### Step 5.2: Lambda API Functions
**Goal**: Implement business logic for each endpoint

**Function 1: `api-list-celebrities-with-sources`**
```python
def lambda_handler(event, context):
    # Parse query parameters
    limit = int(event.get('queryStringParameters', {}).get('limit', 20))
    offset = int(event.get('queryStringParameters', {}).get('offset', 0))
    name_filter = event.get('queryStringParameters', {}).get('name')
    
    # Query DynamoDB for celebrities
    response = table.scan(
        Limit=limit,
        # Apply filters...
    )
    
    # For each celebrity, fetch latest scraper entries
    enriched_celebrities = []
    for celeb in response['Items']:
        sources = get_latest_scraper_entries(celeb['celebrity_id'])
        enriched_celebrities.append({
            **celeb,
            'sources': sources,
            'weight_avg': calculate_average_weight(sources),
            'sentiment_summary': summarize_sentiments(sources)
        })
    
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        },
        'body': json.dumps({
            'celebrities': enriched_celebrities,
            'count': len(enriched_celebrities),
            'total': response.get('ScannedCount', 0)
        })
    }
```

**Function 2: `api-get-all-sources`**
```python
def lambda_handler(event, context):
    celebrity_id = event['pathParameters']['id']
    
    # Query all scraper entries for this celebrity
    response = table.query(
        KeyConditionExpression='celebrity_id = :cid',
        ExpressionAttributeValues={':cid': celebrity_id}
    )
    
    sources_grouped = {}
    for item in response['Items']:
        source_type = item.get('source_type#timestamp', '').split('#')[0]
        if source_type not in sources_grouped:
            sources_grouped[source_type] = []
        
        sources_grouped[source_type].append({
            'id': item['id'],
            'name': item['name'],
            'raw_text': item['raw_text'],
            'source': item['source'],
            'timestamp': item['timestamp'],
            'weight': item.get('weight'),
            'sentiment': item.get('sentiment')
        })
    
    return {
        'statusCode': 200,
        'body': json.dumps(sources_grouped)
    }
```

**Testing Protocol for Each Function**:
1. Unit test with mock data
2. Integration test with DynamoDB
3. API Gateway test
4. **STOP if errors - report and fix**
5. Deploy to production

---

## Phase 6: Frontend Dashboard (Week 11-13)

### Step 6.1: React App Setup ⚛️
**Goal**: Build user interface for viewing and editing data

**Tech Stack**:
- React 18
- React Router (for navigation)
- Axios (for API calls)
- Tailwind CSS (for styling)
- React Query (for data fetching)

**Pages**:
1. **Home/List Page**: Grid of celebrities with search/filter
2. **Detail Page**: Single celebrity with all data sources in tabs
3. **Edit Page**: Form to manually edit celebrity data
4. **Add Page**: Form to add new celebrity

**Tasks**:
- [ ] Create React app: `npx create-react-app celebrity-dashboard`
- [ ] Install dependencies
- [ ] Configure API endpoint (API Gateway URL)
- [ ] Implement celebrity list component
- [ ] Add search and filter functionality
- [ ] Implement celebrity detail view
- [ ] Create tabbed interface for data sources
- [ ] Display weight and sentiment for each source
- [ ] Build edit form
- [ ] Add data freshness indicators
- [ ] Implement manual refresh button

**Component Structure**:
```
src/
├── components/
│   ├── CelebrityCard.jsx
│   ├── CelebrityList.jsx
│   ├── CelebrityDetail.jsx
│   ├── DataSourceTabs.jsx
│   ├── SourceEntry.jsx (displays id, name, raw_text preview, weight, sentiment)
│   ├── EditForm.jsx
│   └── SearchFilter.jsx
├── pages/
│   ├── HomePage.jsx
│   ├── DetailPage.jsx
│   ├── EditPage.jsx
│   └── AddPage.jsx
├── services/
│   └── api.js (API calls)
├── App.jsx
└── index.jsx
```

**Testing Criteria**:
- ✅ Test list page loads all celebrities
- ✅ Test search functionality
- ✅ Test filter by nationality
- ✅ Test detail page navigation
- ✅ Test each data source tab displays weight and sentiment
- ✅ Test weight ranges 0-1 correctly
- ✅ Test sentiment displays as positive/negative/neutral
- ✅ Test edit form submission
- ✅ Test manual refresh button
- ✅ **STOP if any component fails - debug before continuing**
- ✅ Cross-browser testing (Chrome, Firefox, Safari)
- ✅ Mobile responsiveness test

---

### Step 6.2: Deployment to S3 + CloudFront 🚀
**Goal**: Host React app on AWS

**Tasks**:
- [ ] Build React app: `npm run build`
- [ ] Create S3 bucket: `celebrity-dashboard-frontend`
- [ ] Configure bucket for static website hosting
- [ ] Upload build files to S3
- [ ] Create CloudFront distribution
- [ ] Configure custom domain (optional)
- [ ] Set up HTTPS certificate (ACM)
- [ ] Configure caching rules

**Testing Criteria**:
- ✅ Access via S3 endpoint
- ✅ Access via CloudFront URL
- ✅ Test all pages load correctly
- ✅ Test API calls work
- ✅ Verify weight and sentiment display correctly
- ✅ **STOP if frontend can't reach API**
- ✅ Performance test (load time < 3 seconds)

**Cost Estimate**: ~$1-2/month (S3 + CloudFront for low traffic)

---

## Phase 7: Testing & Optimization (Week 14-15)

### Step 7.1: End-to-End Testing
**Goal**: Ensure entire system works together

**Test Scenarios**:
1. **Full Data Refresh**:
   - Trigger EventBridge rule manually
   - All scrapers run successfully
   - Each scraper creates entries with: id, name, raw_text, source, timestamp
   - Post-processor adds: weight, sentiment
   - DynamoDB updated with all fields
   - Frontend shows updated data with weight/sentiment

2. **Manual Edit**:
   - Edit celebrity from frontend
   - Changes saved to DynamoDB
   - Changes reflected immediately

3. **Add New Celebrity**:
   - Add celebrity from frontend
   - Next scrape cycle collects data for new celebrity
   - All data sources populated with first-hand fields
   - Post-processor computes weight/sentiment

4. **Error Handling**:
   - Test with invalid celebrity name
   - Test with API rate limit exceeded
   - Verify error messages in CloudWatch

**Testing Protocol**:
- ✅ Run each scenario 3 times
- ✅ Document any issues
- ✅ Verify weight/sentiment accuracy
- ✅ **STOP if critical bugs found**
- ✅ Fix all bugs before proceeding
- ✅ Re-test after fixes

---

### Step 7.2: Cost Optimization
**Goal**: Minimize AWS costs

**Optimization Tasks**:
- [ ] Review CloudWatch metrics
- [ ] Identify unused resources
- [ ] Optimize Lambda memory allocation
- [ ] Review DynamoDB capacity (ensure On-Demand mode)
- [ ] Set up CloudWatch alarms for cost spikes
- [ ] Implement Lambda reserved concurrency (limit parallel executions)
- [ ] Review S3 storage class (use Standard for frequently accessed data)

**Cost Breakdown Estimate**:
| Service | Monthly Cost |
|---------|--------------|
| DynamoDB (On-Demand) | $1-2 |
| Lambda (All functions) | $0.50 |
| API Gateway | $0.50 |
| S3 + CloudFront | $1-2 |
| EventBridge | $0.01 |
| CloudWatch Logs | $0.50 |
| **Total** | **~$4-6/month** |

---

## Phase 8: Monitoring & Maintenance (Ongoing)

### Step 8.1: CloudWatch Dashboards
**Goal**: Monitor system health

**Metrics to Track**:
- Lambda invocation count and errors
- DynamoDB read/write capacity
- API Gateway request count and latency
- Scraper success rate
- Data freshness (time since last update)
- Weight distribution (average weight across entries)
- Sentiment distribution (positive/negative/neutral counts)

**Tasks**:
- [ ] Create CloudWatch Dashboard: `celebrity-database-monitoring`
- [ ] Add widgets for key metrics
- [ ] Set up alarms:
  - Lambda error rate > 5%
  - API Gateway 5xx errors > 10
  - Scraper failure (no data updated in 8 days)
  - Weight computation failures

---

### Step 8.2: Backup & Recovery
**Goal**: Protect against data loss

**Tasks**:
- [ ] Enable DynamoDB Point-in-Time Recovery
- [ ] Set up automated daily backups
- [ ] Document restore procedure
- [ ] Test restore from backup (quarterly)

**Cost**: ~$0.20/month for PITR

---

## Technology Stack Summary

### AWS Services
| Service | Purpose | Cost/Month |
|---------|---------|------------|
| DynamoDB | Central database | $1-2 |
| Lambda | Serverless scrapers + API functions + post-processor | $0.70 |
| EventBridge | Scheduler for scrapers | $0.01 |
| API Gateway | REST API | $0.50 |
| S3 | Frontend hosting | $0.20 |
| CloudFront | CDN | $1 |
| CloudWatch | Logging & monitoring | $0.50 |
| DynamoDB Streams | Change tracking | $0.05 |

### External APIs/Services
- TMDb API (Free tier)
- Wikipedia API (Free)
- NewsAPI or RSS (Free)
- Social media APIs (Free tiers)
- AWS Comprehend (optional, for sentiment analysis - ~$0.0001 per unit)

### Frontend
- React 18
- React Router
- Axios
- Tailwind CSS
- React Query

### Backend
- Python 3.11 (Lambda runtime)
- boto3 (AWS SDK)
- requests (HTTP library)
- TextBlob or AWS Comprehend (sentiment analysis)

---

## Data Collection Reference

### Field Definitions Summary

**First-Hand Fields** (Collected during scrape):
- `id`: Unique identifier per scraper entry (UUID)
- `name`: Celebrity name from source
- `raw_text`: Raw response from API/website (JSON or HTML string)
- `source`: Source URL (e.g., https://api.themoviedb.org/3/person/search)
- `timestamp`: ISO 8601 timestamp when data was scraped

**Computed Fields** (Added during post-processing):
- `weight`: Confidence score 0-1 (based on completeness + source reliability)
- `sentiment`: String (positive, negative, neutral) from NLP analysis

### Data Sources Reference

### 1. TMDb (The Movie Database)
- **URL**: https://www.themoviedb.org/
- **API Docs**: https://developers.themoviedb.org/3
- **Rate Limit**: 1000 requests/day (free)
- **Data**: Movies, TV shows, cast, crew, ratings

### 2. Wikipedia
- **URL**: https://www.wikipedia.org/
- **API Docs**: https://www.mediawiki.org/wiki/API:Main_page
- **Rate Limit**: No strict limit (be reasonable)
- **Data**: Biography, career, awards, personal life

### 3. NewsAPI
- **URL**: https://newsapi.org/
- **Rate Limit**: 100 requests/day (free)
- **Data**: News articles, headlines

### 4. Twitter/X API
- **URL**: https://developer.twitter.com/
- **Rate Limit**: Varies by tier
- **Data**: Follower count, tweets

### 5. Instagram (Unofficial APIs)
- Various third-party APIs available
- **Data**: Follower count, post count

### 6. YouTube Data API
- **URL**: https://developers.google.com/youtube/v3
- **Rate Limit**: 10,000 quota units/day (free)
- **Data**: Channel stats, video count, subscriber count

### 7. IMDb (Web Scraping)
- **URL**: https://www.imdb.com/
- **Note**: No official API, requires web scraping
- **Data**: Ratings, awards, trivia

### 8. Spotify API
- **URL**: https://developer.spotify.com/
- **Rate Limit**: Generous free tier
- **Data**: Artist info, albums, popularity

---

## Security Considerations

### 1. API Keys Management
- Store all API keys in AWS Secrets Manager
- Never hardcode keys in Lambda code
- Rotate keys quarterly

### 2. API Gateway Security
- Enable API key authentication
- Implement rate limiting (100 requests/minute per IP)
- Enable AWS WAF for DDoS protection (optional)

### 3. DynamoDB Security
- Enable encryption at rest
- Use IAM roles for Lambda access
- Implement fine-grained access control

### 4. Frontend Security
- Use HTTPS only (via CloudFront)
- Implement CORS properly
- Sanitize all user inputs

---

## Scaling Plan

### From 100 to 1,000 Celebrities

**Changes Required**:
1. **Lambda Timeout**: Increase to 10-15 minutes
2. **Batch Processing**: Process celebrities in batches of 100
3. **DynamoDB**: No changes needed (On-Demand scales automatically)
4. **API Gateway**: May need to increase throttle limits
5. **Cost**: Estimate $15-20/month for 1,000 celebrities

**Implementation**:
```python
# Batch processing example
def lambda_handler(event, context):
    batch_size = 100
    celebrities = get_all_celebrities()
    
    for i in range(0, len(celebrities), batch_size):
        batch = celebrities[i:i+batch_size]
        process_batch(batch)
        
        # TEST: Log after each batch
        print(f"✓ Completed batch {i//batch_size + 1}")
```

---

## Troubleshooting Guide

### Common Issues

**Issue 1: Lambda Timeout**
- **Symptom**: Lambda stops at 5 minutes
- **Solution**: Increase timeout or implement batch processing

**Issue 2: API Rate Limit Exceeded**
- **Symptom**: 429 errors from external APIs
- **Solution**: Implement exponential backoff, reduce request frequency

**Issue 3: DynamoDB Throttling**
- **Symptom**: ProvisionedThroughputExceededException
- **Solution**: Verify On-Demand mode is enabled, or increase provisioned capacity

**Issue 4: Frontend Can't Reach API**
- **Symptom**: CORS errors in browser console
- **Solution**: Verify CORS configuration in API Gateway

**Issue 5: Stale Data**
- **Symptom**: Data not updating weekly
- **Solution**: Check EventBridge rule is enabled, review Lambda logs

**Issue 6: Weight/Sentiment Not Computed**
- **Symptom**: weight and sentiment fields are null
- **Solution**: Verify post-processor Lambda is triggered by DynamoDB Streams, check error logs

---

## Next Steps After Completion

### Enhancements (Future Phases)

1. **Advanced Analytics**
   - Trend analysis over time
   - Popularity predictions
   - Career trajectory visualization

2. **Data Enrichment**
   - Image scraping and storage (S3)
   - Video clip collection
   - Relationship mapping (co-stars, family)

3. **AI Features**
   - Natural language search
   - Automatic categorization
   - Enhanced sentiment analysis on news

4. **Collaboration Features**
   - Multi-user access
   - Role-based permissions
   - Data contribution workflow

5. **Mobile App**
   - React Native app
   - Offline mode
   - Push notifications for updates

---

## Project Timeline Summary

| Phase | Duration | Key Milestones |
|-------|----------|-----------------|
| Phase 1: Foundation | 2 weeks | DynamoDB setup, seed 100 celebrities |
| Phase 2: Scrapers | 4 weeks | 4-10 Lambda scrapers operational |
| Phase 3: Post-Processing | 1 week | Weight & sentiment computation working |
| Phase 4: Orchestration | 1 week | Weekly automation active |
| Phase 5: API Layer | 2 weeks | REST API functional |
| Phase 6: Frontend | 3 weeks | React dashboard deployed |
| Phase 7: Testing | 2 weeks | Full system validated |
| Phase 8: Monitoring | Ongoing | CloudWatch dashboards live |
| **Total** | **16 weeks** | **Fully operational system** |

---

## Success Criteria

✅ **System is successful when**:
1. All 100 celebrities have data from at least 4 sources
2. Each entry contains: id, name, raw_text, source, timestamp
3. Each entry has computed: weight (0-1), sentiment (positive/negative/neutral)
4. Data updates automatically every Sunday
5. Dashboard loads in < 3 seconds and displays all fields
6. Manual edits save successfully
7. Total monthly cost < $10
8. Zero data loss incidents
9. All scrapers run with >95% success rate
10. Frontend is mobile-responsive
11. API response time < 500ms
12. **System follows test-at-each-step protocol - no proceeding with bugs**

---

## Contact & Support

**Project Owner**: [Your Name]
**Started**: November 7, 2025
**Repository**: [GitHub URL]
**Documentation**: This file (project.md)

---

## Testing Protocol Reminder ⚠️

**CRITICAL**: As per Space instructions, at each phase:
1. ✅ Test with minimal data first (1-5 items)
2. ✅ Review all logs and outputs
3. ✅ **STOP immediately if bugs found**
4. ✅ **Report bugs clearly before proceeding**
5. ✅ Fix bugs completely
6. ✅ Re-test after fixes
7. ✅ Only proceed when step is confirmed working
8. ✅ Never skip ahead with known issues

**This ensures stability and prevents cascading failures!**

---

## Appendix

### A. Database Schema Quick Reference

```json
{
  "celebrity_id": "celeb_001",
  "source_type#timestamp": "tmdb#2025-11-07T17:20:00Z",
  "id": "scraper_entry_001_tmdb_2025_11_07",
  "name": "Leonardo DiCaprio",
  "raw_text": "{...full API response or HTML...}",
  "source": "https://api.themoviedb.org/3/person/search",
  "timestamp": "2025-11-07T17:20:00Z",
  "weight": 0.85,
  "sentiment": "neutral"
}
```

### B. Lambda Environment Variables Template
```bash
# TMDb Scraper
TMDB_API_KEY=your_api_key_here
DYNAMODB_TABLE=celebrity-database

# News Scraper
NEWSAPI_KEY=your_api_key_here

# Social Scraper
TWITTER_API_KEY=your_api_key_here
```

### C. DynamoDB GSI Configuration
```json
{
  "GlobalSecondaryIndexes": [
    {
      "IndexName": "name-index",
      "KeySchema": [
        {
          "AttributeName": "name",
          "KeyType": "HASH"
        }
      ],
      "Projection": {
        "ProjectionType": "ALL"
      }
    },
    {
      "IndexName": "source-index",
      "KeySchema": [
        {
          "AttributeName": "source",
          "KeyType": "HASH"
        },
        {
          "AttributeName": "timestamp",
          "KeyType": "RANGE"
        }
      ],
      "Projection": {
        "ProjectionType": "ALL"
      }
    }
  ]
}
```

---

**End of Project Plan**

*This document will be updated as the project progresses.*
*Last Updated: November 7, 2025*

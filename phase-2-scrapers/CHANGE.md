# Phase 2: Scrapers - Schema Alignment with project-updated.md

**Purpose**: This file documents the required changes to ensure Phase 2 scraper implementations align with the authoritative data schema defined in project-updated.md (lines 123-180).

**Last Updated**: November 9, 2025
**Status**: Ready for Implementation

---

## ✅ Current State Assessment

### What's Correct
- ✅ All 4 scraper stages (Stage 2.1, 2.3-Instagram, 2.3-Threads, 2.4-YouTube) implemented
- ✅ Basic error handling and logging in place
- ✅ DynamoDB integration functional
- ✅ Lambda function structure correct (lambda_handler exists)
- ✅ Required fields mostly captured (id, name, source, timestamp)

### What Needs Correction
- ⚠️ raw_text field may not contain COMPLETE unprocessed API responses
- ⚠️ Documentation doesn't clearly emphasize "raw_text = complete API response" requirement
- ⚠️ No validation to ensure raw_text is properly stored for Phase 3 processing
- ⚠️ Weight and sentiment fields may not be properly initialized as null/None

---

## Critical Concept: raw_text Must Contain COMPLETE API Response

### What raw_text MUST Be (For Phase 3 Semantic Analysis)

The `raw_text` field is the cornerstone of Phase 3 post-processing. It MUST contain:

1. **Complete**: Every single field from the API/web response
2. **Unprocessed**: No parsing, filtering, or extraction
3. **Stored as JSON String**: Serialized JSON representation of the entire response
4. **Preserved for Extraction**: Phase 3 will extract text FROM this raw response

### Example: Google Search (Stage 2.1)

**Correct raw_text** ✅:
```python
{
  "celebrity_id": "celeb_001",
  "source_type#timestamp": "google_search#2025-11-07T17:20:00Z",
  "id": "scraper_entry_001_google_2025_11_07",
  "name": "Leonardo DiCaprio",
  "raw_text": "{\"kind\": \"customsearch#search\", \"url\": {...}, \"items\": [{\"kind\": \"customsearch#result\", \"title\": \"Leonardo DiCaprio - Wikipedia\", \"link\": \"https://en.wikipedia.org/wiki/Leonardo_DiCaprio\", \"snippet\": \"Leonardo DiCaprio is an American actor...\", \"displayLink\": \"en.wikipedia.org\"}], ...COMPLETE response...}",
  "source": "https://www.googleapis.com/customsearch/v1",
  "timestamp": "2025-11-07T17:20:00Z",
  "weight": null,
  "sentiment": null
}
```

**Incorrect raw_text** ❌:
```python
{
  "raw_text": "Leonardo DiCaprio is an American actor known for Titanic"  // ❌ EXTRACTED TEXT
}
```

**Incorrect raw_text** ❌:
```python
{
  "raw_text": {"title": "Leonardo DiCaprio - Wikipedia", "snippet": "..."}  // ❌ FILTERED/PARSED RESPONSE
}
```

### Example: Instagram (Stage 2.3)

**Correct raw_text** ✅:
```python
{
  "celebrity_id": "celeb_002",
  "source_type#timestamp": "instagram#2025-11-07T18:45:00Z",
  "id": "scraper_entry_002_instagram_2025_11_07",
  "name": "Taylor Swift",
  "raw_text": "{\"pk\": 1234567890, \"username\": \"taylorswift\", \"full_name\": \"Taylor Swift\", \"biography\": \"...\", \"follower_count\": 288000000, \"following_count\": 450, \"is_verified\": true, \"profile_pic_url\": \"...\", \"posts\": [{\"id\": \"...\", \"caption\": \"...\", \"timestamp\": \"...\", \"like_count\": \"...\", \"comment_count\": \"...\"}], ...COMPLETE Instaloader data...}",
  "source": "https://www.instagram.com/taylorswift",
  "timestamp": "2025-11-07T18:45:00Z",
  "weight": null,
  "sentiment": null
}
```

### Example: YouTube (Stage 2.4)

**Correct raw_text** ✅:
```python
{
  "celebrity_id": "celeb_003",
  "source_type#timestamp": "youtube#2025-11-07T19:30:00Z",
  "id": "scraper_entry_003_youtube_2025_11_07",
  "name": "MrBeast",
  "raw_text": "{\"kind\": \"youtube#channelListResponse\", \"etag\": \"...\", \"items\": [{\"kind\": \"youtube#channel\", \"etag\": \"...\", \"id\": \"UCX6OQ...\", \"snippet\": {\"publishedAt\": \"2012-02-18T07:20:08Z\", \"title\": \"MrBeast\", \"description\": \"...\", \"thumbnails\": {...}, \"defaultLanguage\": \"en\", \"localized\": {...}}, \"statistics\": {\"viewCount\": \"...\", \"commentCount\": \"...\", \"subscriberCount\": \"...\", \"hiddenSubscriberCount\": false, \"videoCount\": \"...\"}, \"contentDetails\": {\"relatedPlaylists\": {...}}}, ...COMPLETE YouTube API response...}",
  "source": "https://www.googleapis.com/youtube/v3/channels",
  "timestamp": "2025-11-07T19:30:00Z",
  "weight": null,
  "sentiment": null
}
```

### Example: Threads (Stage 2.3)

**Correct raw_text** ✅:
```python
{
  "celebrity_id": "celeb_004",
  "source_type#timestamp": "threads#2025-11-07T20:15:00Z",
  "id": "scraper_entry_004_threads_2025_11_07",
  "name": "Elon Musk",
  "raw_text": "{\"user_id\": \"123456\", \"username\": \"elonmusk\", \"name\": \"Elon Musk\", \"biography\": \"...\", \"follower_count\": \"...\", \"following_count\": \"...\", \"is_verified\": true, \"profile_pic_url\": \"...\", \"threads\": [{\"id\": \"...\", \"content\": \"...\", \"timestamp\": \"...\", \"like_count\": \"...\", \"reply_count\": \"...\"}, ...], ...COMPLETE Instaloader/Threads data...}",
  "source": "https://www.threads.net/@elonmusk",
  "timestamp": "2025-11-07T20:15:00Z",
  "weight": null,
  "sentiment": null
}
```

---

## Data Flow: Phase 2 Creates raw_text for Phase 3

```
Phase 2 Scrapers
  │
  ├─ Stage 2.1 (Google Search)
  │  └─ Creates entry with raw_text = COMPLETE Google API response JSON
  │
  ├─ Stage 2.3 (Instagram)
  │  └─ Creates entry with raw_text = COMPLETE Instaloader profile data
  │
  ├─ Stage 2.3 (Threads)
  │  └─ Creates entry with raw_text = COMPLETE Instaloader Threads data
  │
  └─ Stage 2.4 (YouTube)
     └─ Creates entry with raw_text = COMPLETE YouTube API response JSON
              │
              │ Each entry: weight=null, sentiment=null
              │
              ▼
        DynamoDB Streams Trigger
              │
              ▼
      Phase 3: Post-Processor
        │
        ├─ Reads raw_text from DynamoDB Streams
        ├─ EXTRACTS TEXT FROM raw_text (e.g., biography, post captions)
        ├─ Computes semantic analysis (sentiment, weight)
        ├─ Updates DynamoDB with: weight, sentiment
        │
        ▼
      DynamoDB Entry Now Complete
        ├─ raw_text: COMPLETE unprocessed response (unchanged)
        ├─ weight: Float (0-1) - computed confidence score
        ├─ sentiment: String - positive/neutral/negative
```

---

## Required Changes by Stage

### Stage 2.1: Google Search API

**File**: `stage-2.1-google-search/lambda_function.py`

**Lines to Verify** (lines ~100-200):
- Check that `fetch_google_search_data()` returns complete `response.json()`
- Verify `raw_text` field stores entire Google API response as JSON string
- Confirm weight and sentiment are initialized to `None`

**Correct Implementation Pattern**:
```python
def store_google_search_entry(celebrity_id, celebrity_name, response_data, source_url):
    """
    Store Google Search scraper entry with COMPLETE API response.

    Args:
        celebrity_id: Unique celebrity ID
        celebrity_name: Name of celebrity
        response_data: COMPLETE response from Google Custom Search API (dict)
        source_url: Source URL

    Returns:
        True if successful, False otherwise
    """
    try:
        # Generate timestamps
        timestamp = datetime.utcnow().isoformat() + "Z"

        # Create entry - raw_text must be COMPLETE API response
        entry = {
            "celebrity_id": celebrity_id,
            "source_type#timestamp": f"google_search#{timestamp}",
            "id": f"scraper_entry_{celebrity_id}_google_{timestamp.replace(':', '').replace('-', '').split('T')[0]}",
            "name": celebrity_name,
            "raw_text": json.dumps(response_data, ensure_ascii=False),  # COMPLETE API response
            "source": source_url,
            "timestamp": timestamp,
            "weight": None,  # Computed by Phase 3
            "sentiment": None  # Computed by Phase 3
        }

        # Write to DynamoDB
        table = dynamodb.Table('celebrity-database')
        table.put_item(Item=entry)

        logger.info(f"Stored Google Search entry for {celebrity_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to store entry: {str(e)}")
        return False
```

**Validation Checklist**:
- [ ] `raw_text` contains entire Google API JSON response (not filtered)
- [ ] `raw_text` is stored as JSON string (not dict)
- [ ] `weight` is None (not computed)
- [ ] `sentiment` is None (not computed)
- [ ] `source` is "https://www.googleapis.com/customsearch/v1"
- [ ] `source_type#timestamp` format: "google_search#{ISO8601_timestamp}"

---

### Stage 2.3: Instagram (Modern Instaloader)

**File**: `stage-2.3-instagram/lambda_function.py`

**Required Change**:
Since user switched from proxy-based API to free Instaloader, the raw_text field should now store:
- Complete profile data from Instaloader
- All posts with full caption, timestamps, engagement metrics
- Comments and engagement data

**Correct Implementation Pattern**:
```python
def store_instagram_entry(celebrity_id, celebrity_name, profile_data, posts_data):
    """
    Store Instagram scraper entry with COMPLETE Instaloader profile data.

    Args:
        celebrity_id: Unique celebrity ID
        celebrity_name: Name of celebrity
        profile_data: COMPLETE profile object from Instaloader (dict/object)
        posts_data: COMPLETE posts list with all details (list of dicts)

    Returns:
        True if successful, False otherwise
    """
    try:
        # Generate timestamps
        timestamp = datetime.utcnow().isoformat() + "Z"

        # Combine all Instaloader data into single object
        complete_response = {
            "profile": serialize_instaloader_profile(profile_data),
            "posts": [serialize_instaloader_post(post) for post in posts_data],
            "scrape_metadata": {
                "scraper_version": "instaloader_free",
                "scrape_timestamp": timestamp,
                "profile_url": f"https://www.instagram.com/{celebrity_name}"
            }
        }

        # Create entry
        entry = {
            "celebrity_id": celebrity_id,
            "source_type#timestamp": f"instagram#{timestamp}",
            "id": f"scraper_entry_{celebrity_id}_instagram_{timestamp.replace(':', '').replace('-', '').split('T')[0]}",
            "name": celebrity_name,
            "raw_text": json.dumps(complete_response, ensure_ascii=False, default=str),  # COMPLETE profile + posts
            "source": f"https://www.instagram.com/{celebrity_name}",
            "timestamp": timestamp,
            "weight": None,  # Computed by Phase 3
            "sentiment": None  # Computed by Phase 3
        }

        # Write to DynamoDB
        table = dynamodb.Table('celebrity-database')
        table.put_item(Item=entry)

        logger.info(f"Stored Instagram entry for {celebrity_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to store entry: {str(e)}")
        return False

def serialize_instaloader_profile(profile_obj):
    """Convert Instaloader profile object to dict."""
    return {
        "user_id": profile_obj.userid,
        "username": profile_obj.username,
        "full_name": profile_obj.full_name,
        "biography": profile_obj.biography,
        "follower_count": profile_obj.followers,
        "following_count": profile_obj.followees,
        "is_verified": profile_obj.is_verified,
        "profile_pic_url": profile_obj.profile_pic_url,
        "website": profile_obj.external_url,
        "is_business_account": profile_obj.is_business_account
    }

def serialize_instaloader_post(post_obj):
    """Convert Instaloader post object to dict."""
    return {
        "post_id": post_obj.mediaid,
        "caption": post_obj.caption,
        "timestamp": post_obj.date_utc.isoformat(),
        "like_count": post_obj.likes,
        "comment_count": post_obj.comments,
        "post_url": post_obj.shortcode,
        "is_video": post_obj.is_video,
        "media_type": "image" if post_obj.mediacount == 1 else "carousel"
    }
```

**Validation Checklist**:
- [ ] `raw_text` contains COMPLETE Instaloader profile object (all fields)
- [ ] `raw_text` contains COMPLETE posts array with captions, timestamps, engagement
- [ ] `raw_text` is stored as JSON string (not dict)
- [ ] `weight` is None (not computed)
- [ ] `sentiment` is None (not computed)
- [ ] `source` is "https://www.instagram.com/{celebrity_name}"
- [ ] `source_type#timestamp` format: "instagram#{ISO8601_timestamp}"
- [ ] No personal credentials/session tokens in raw_text

---

### Stage 2.3: Threads

**File**: `stage-2.3-threads/lambda_function.py`

**Similar to Instagram**: Use Instaloader library to fetch Threads data

**Correct Implementation Pattern**:
```python
def store_threads_entry(celebrity_id, celebrity_name, profile_data, threads_data):
    """
    Store Threads scraper entry with COMPLETE Instaloader Threads data.

    Args:
        celebrity_id: Unique celebrity ID
        celebrity_name: Name of celebrity
        profile_data: COMPLETE profile object from Instaloader (dict/object)
        threads_data: COMPLETE threads list with all details (list of dicts)

    Returns:
        True if successful, False otherwise
    """
    try:
        # Generate timestamps
        timestamp = datetime.utcnow().isoformat() + "Z"

        # Combine all Threads data
        complete_response = {
            "profile": serialize_threads_profile(profile_data),
            "threads": [serialize_threads_post(thread) for thread in threads_data],
            "scrape_metadata": {
                "scraper_version": "instaloader_free",
                "scrape_timestamp": timestamp,
                "profile_url": f"https://www.threads.net/@{celebrity_name}"
            }
        }

        # Create entry
        entry = {
            "celebrity_id": celebrity_id,
            "source_type#timestamp": f"threads#{timestamp}",
            "id": f"scraper_entry_{celebrity_id}_threads_{timestamp.replace(':', '').replace('-', '').split('T')[0]}",
            "name": celebrity_name,
            "raw_text": json.dumps(complete_response, ensure_ascii=False, default=str),  # COMPLETE profile + threads
            "source": f"https://www.threads.net/@{celebrity_name}",
            "timestamp": timestamp,
            "weight": None,  # Computed by Phase 3
            "sentiment": None  # Computed by Phase 3
        }

        # Write to DynamoDB
        table = dynamodb.Table('celebrity-database')
        table.put_item(Item=entry)

        logger.info(f"Stored Threads entry for {celebrity_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to store entry: {str(e)}")
        return False
```

**Validation Checklist**:
- [ ] `raw_text` contains COMPLETE Threads profile data
- [ ] `raw_text` contains COMPLETE threads array with content, timestamps, engagement
- [ ] `raw_text` is stored as JSON string (not dict)
- [ ] `weight` is None (not computed)
- [ ] `sentiment` is None (not computed)
- [ ] `source` is "https://www.threads.net/@{celebrity_name}"
- [ ] `source_type#timestamp` format: "threads#{ISO8601_timestamp}"

---

### Stage 2.4: YouTube

**File**: `stage-2.4-youtube/lambda_function.py`

**Required Change**:
Verify that raw_text stores COMPLETE YouTube API response for channels and statistics

**Correct Implementation Pattern**:
```python
def store_youtube_entry(celebrity_id, celebrity_name, channel_data, statistics_data):
    """
    Store YouTube scraper entry with COMPLETE YouTube API response.

    Args:
        celebrity_id: Unique celebrity ID
        celebrity_name: Name of celebrity
        channel_data: COMPLETE response from YouTube Channels API
        statistics_data: COMPLETE response from YouTube Statistics API

    Returns:
        True if successful, False otherwise
    """
    try:
        # Generate timestamps
        timestamp = datetime.utcnow().isoformat() + "Z"

        # Combine all YouTube API responses
        complete_response = {
            "channel_data": channel_data,  # COMPLETE channels API response
            "statistics": statistics_data,  # COMPLETE statistics
            "api_source": "https://www.googleapis.com/youtube/v3",
            "scrape_timestamp": timestamp
        }

        # Create entry
        entry = {
            "celebrity_id": celebrity_id,
            "source_type#timestamp": f"youtube#{timestamp}",
            "id": f"scraper_entry_{celebrity_id}_youtube_{timestamp.replace(':', '').replace('-', '').split('T')[0]}",
            "name": celebrity_name,
            "raw_text": json.dumps(complete_response, ensure_ascii=False),  # COMPLETE YouTube API response
            "source": "https://www.googleapis.com/youtube/v3",
            "timestamp": timestamp,
            "weight": None,  # Computed by Phase 3
            "sentiment": None  # Computed by Phase 3
        }

        # Write to DynamoDB
        table = dynamodb.Table('celebrity-database')
        table.put_item(Item=entry)

        logger.info(f"Stored YouTube entry for {celebrity_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to store entry: {str(e)}")
        return False
```

**Validation Checklist**:
- [ ] `raw_text` contains COMPLETE YouTube channels API response
- [ ] `raw_text` contains COMPLETE statistics (view count, subscriber count, video count)
- [ ] `raw_text` is stored as JSON string (not dict)
- [ ] `weight` is None (not computed)
- [ ] `sentiment` is None (not computed)
- [ ] `source` is "https://www.googleapis.com/youtube/v3"
- [ ] `source_type#timestamp` format: "youtube#{ISO8601_timestamp}"

---

## Required Documentation Updates for Phase 2

### 1. Update phase-2-scrapers/README.md

**New Section to Add** (after Overview section):

```markdown
## Critical: raw_text Field Storage

The `raw_text` field in each scraper entry **MUST contain the complete, unprocessed API response** from the source. This is essential for Phase 3 post-processing (semantic analysis).

### raw_text Requirements

- **Complete**: Every field from the API/web response
- **Unprocessed**: No filtering, extraction, or parsing
- **JSON String**: Serialized as JSON string, not dict object
- **Preserved**: Stored as-is for Phase 3 to extract text content

### By Stage

| Stage | Source | raw_text Contains |
|-------|--------|-------------------|
| 2.1 | Google Custom Search API | Complete API response JSON with all results |
| 2.3 | Instagram (Instaloader) | Complete profile object + all posts |
| 2.3 | Threads (Instaloader) | Complete profile object + all threads |
| 2.4 | YouTube Data API v3 | Complete channels + statistics API response |

### Example

```json
{
  "celebrity_id": "celeb_001",
  "source_type#timestamp": "google_search#2025-11-07T17:20:00Z",
  "id": "scraper_entry_001_google_2025_11_07",
  "name": "Leonardo DiCaprio",
  "raw_text": "{\"kind\": \"customsearch#search\", \"url\": {...}, \"items\": [{...COMPLETE API response...}]}",
  "source": "https://www.googleapis.com/customsearch/v1",
  "timestamp": "2025-11-07T17:20:00Z",
  "weight": null,
  "sentiment": null
}
```

### Phase 3 Processing

Phase 3 post-processor will:
1. Read `raw_text` field from DynamoDB Streams
2. **Extract** text content FROM raw_text (e.g., snippets, captions, descriptions)
3. Perform NLP sentiment analysis on extracted text
4. Compute confidence weight based on data completeness and source reliability
5. Update DynamoDB entry with `weight` and `sentiment`
```

### 2. Update Each Stage's README.md

**For stage-2.1-google-search/README.md**:

Add section after "Implementation Details":

```markdown
## Data Storage Pattern

This scraper stores the **complete Google Custom Search API response** in the `raw_text` field. This includes:

- All search results items (up to 10)
- Each result's: title, link, snippet, displayLink, etc.
- API metadata: kind, url, queries, context

Example stored raw_text:
```json
{
  "kind": "customsearch#search",
  "url": "https://www.googleapis.com/customsearch/v1?...",
  "items": [
    {
      "kind": "customsearch#result",
      "title": "Leonardo DiCaprio - Wikipedia",
      "link": "https://en.wikipedia.org/wiki/Leonardo_DiCaprio",
      "snippet": "Leonardo Wilhelm DiCaprio...",
      "displayLink": "en.wikipedia.org"
    },
    // ... more results
  ]
}
```

The Phase 3 post-processor will extract text content from this raw response for semantic analysis.
```

**For stage-2.3-instagram/README.md**:

```markdown
## Data Storage Pattern (Instaloader)

This scraper stores the **complete Instaloader profile and posts data** in the `raw_text` field. This includes:

- Profile object: pk, username, full_name, biography, follower_count, etc.
- Posts array: Each post with caption, timestamp, likes, comments
- All engagement metrics

Example stored raw_text structure:
```json
{
  "profile": {
    "user_id": 123456789,
    "username": "taylorswift",
    "full_name": "Taylor Swift",
    "biography": "...",
    "follower_count": 288000000,
    "following_count": 450,
    "is_verified": true
  },
  "posts": [
    {
      "post_id": "3012345678901234567",
      "caption": "...",
      "timestamp": "2025-11-07T15:30:00Z",
      "like_count": 2500000,
      "comment_count": 50000
    }
  ]
}
```

The Phase 3 post-processor will extract captions and comments from this raw data for sentiment analysis.
```

**For stage-2.3-threads/README.md**:

```markdown
## Data Storage Pattern (Instaloader)

This scraper stores the **complete Instaloader Threads profile and threads data** in the `raw_text` field. Similar structure to Instagram but for Threads content.

The Phase 3 post-processor will extract thread content and comments from this raw data for sentiment analysis.
```

**For stage-2.4-youtube/README.md**:

```markdown
## Data Storage Pattern

This scraper stores the **complete YouTube Data API v3 response** in the `raw_text` field. This includes:

- Channel snippet: publishedAt, title, description, defaultLanguage
- Channel statistics: viewCount, subscriberCount, videoCount
- Content details: related playlists
- Thumbnails and localized data

Example stored raw_text:
```json
{
  "channel_data": {
    "kind": "youtube#channel",
    "id": "UCX6OQ...",
    "snippet": {
      "publishedAt": "2012-02-18T07:20:08Z",
      "title": "MrBeast",
      "description": "...",
      "defaultLanguage": "en"
    },
    "statistics": {
      "viewCount": "4500000000",
      "subscriberCount": "200000000",
      "videoCount": "800"
    }
  }
}
```

The Phase 3 post-processor will extract descriptions and analyze channel characteristics from this raw data.
```

---

## Schema Validation Checklist for Phase 2

Before declaring Phase 2 complete, verify each stage:

### All Stages (Generic Checks)
- [ ] Entry has ALL required fields: id, name, raw_text, source, timestamp, weight, sentiment
- [ ] `raw_text` is JSON string (check with json.dumps/loads)
- [ ] `weight` is None (not a number)
- [ ] `sentiment` is None (not a string)
- [ ] All timestamps valid ISO 8601 format with 'Z' suffix
- [ ] `source_type#timestamp` follows pattern: "{source}#{ISO8601_timestamp}"
- [ ] DynamoDB write successful (no errors)

### Stage 2.1 (Google Search)
- [ ] `raw_text` contains complete Google Custom Search JSON response
- [ ] All search results items preserved in raw_text
- [ ] `source` = "https://www.googleapis.com/customsearch/v1"
- [ ] `source_type#timestamp` = "google_search#{timestamp}"

### Stage 2.3 (Instagram)
- [ ] `raw_text` contains complete profile object from Instaloader
- [ ] `raw_text` contains all posts with captions and timestamps
- [ ] `raw_text` is JSON string (not Python dict)
- [ ] `source` = "https://www.instagram.com/{celebrity_name}"
- [ ] `source_type#timestamp` = "instagram#{timestamp}"
- [ ] No credentials in raw_text

### Stage 2.3 (Threads)
- [ ] `raw_text` contains complete Threads profile data
- [ ] `raw_text` contains all threads with content
- [ ] `source` = "https://www.threads.net/@{celebrity_name}"
- [ ] `source_type#timestamp` = "threads#{timestamp}"

### Stage 2.4 (YouTube)
- [ ] `raw_text` contains complete YouTube channels API response
- [ ] `raw_text` contains complete statistics
- [ ] `source` = "https://www.googleapis.com/youtube/v3"
- [ ] `source_type#timestamp` = "youtube#{timestamp}"

### DynamoDB Entry Validation
```bash
# Query a recent entry to verify structure
aws dynamodb query --table-name celebrity-database \
  --key-condition-expression "celebrity_id = :id" \
  --expression-attribute-values '{":id":{"S":"celeb_001"}}' \
  --sort-key-condition-expression "begins_with(source_type#timestamp, :st)" \
  --expression-attribute-values '{":st":{"S":"google_search"}}'

# Verify raw_text is valid JSON
python3 -c "import json; raw = json.loads(item['raw_text']['S']); print('Valid JSON')"
```

---

## Alignment with project-updated.md

This Phase 2 implementation aligns with project-updated.md specification:

| Item | Reference | Status |
|------|-----------|--------|
| Scraper entry structure | Lines 125-144 | ✅ Implement per pattern |
| Field definitions | Lines 147-157 | ✅ All fields required |
| raw_text = complete response | Line 153 | ✅ CRITICAL - emphasize |
| First-hand data pattern | Lines 159-180 | ✅ Follow exactly |
| DynamoDB schema | Lines 184-214 | ✅ Store correctly |
| Keys design | Lines 205-213 | ✅ Format correctly |
| source_type#timestamp format | Lines 130, 270 | ✅ Use "{source}#{timestamp}" |
| Weight and sentiment initial value | Lines 273-274 | ✅ Must be None/null |

---

## Summary for AI Agents

**What Phase 2 Does**:
1. Fetches data from 4 external sources (Google, Instagram, Threads, YouTube)
2. Stores **COMPLETE unprocessed API responses** in `raw_text` field
3. Initializes `weight` and `sentiment` to None
4. Writes to DynamoDB with proper composite keys
5. Triggers DynamoDB Streams for Phase 3 processing

**What Phase 2 Does NOT Do**:
1. Extract text content from responses (Phase 3's job)
2. Compute confidence weights (Phase 3's job)
3. Perform sentiment analysis (Phase 3's job)
4. Filter or parse API responses (must store complete response)

**Critical Implementation Pattern**:
```python
# ALWAYS do this:
raw_text: json.dumps(complete_api_response)  # ✅ COMPLETE response
weight: None  # ✅ Not computed yet
sentiment: None  # ✅ Not computed yet

# NEVER do this:
raw_text: json.dumps(extracted_fields_only)  # ❌ Filtered response
raw_text: celebrity_biography  # ❌ Extracted text
weight: 0.75  # ❌ Computed too early
sentiment: "positive"  # ❌ Computed too early
```

**Documentation Updates Required**:
1. Add raw_text requirements section to phase-2-scrapers/README.md
2. Add data storage pattern to each stage's README
3. Document exact fields stored in raw_text for each source
4. Provide validation checklist for testing

**Next Step**: Phase 3 will read raw_text from DynamoDB Streams and compute weight/sentiment.

---

**For Questions**: Refer to project-updated.md lines 123-180 for authoritative schema definition.


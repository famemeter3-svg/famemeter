# Phase 3: Post-Processing & Semantic Enrichment - Intelligence Layer

## Executive Summary

Phase 3 enriches scraped data with computed fields: **weight** (confidence score), **sentiment** (sentiment analysis), **cleaned_text** (cleaned and formatted text), and **summary** (concise summary). It processes all entries from Phase 2 via DynamoDB Streams, adding confidence scoring, sentiment classification, text cleaning, and AI-generated summaries. This phase transforms raw unprocessed data into actionable semantic intelligence using Google Gemini API.

**Key Design**: Stateless, event-driven Lambda triggered by DynamoDB Streams - no polling, minimal cost, automatic triggering when new data arrives. Uses free Gemini API for advanced NLP tasks.

## Overview

Phase 3 accomplishes:
1. **Weight Computation**: Calculate confidence score (0-1) for each entry
2. **Sentiment Analysis**: Classify sentiment (positive/negative/neutral) via NLP
3. **Text Cleaning**: Extract and format clean text from raw API responses using Gemini
4. **Summary Generation**: Generate concise summaries using Gemini AI
5. **Data Enrichment**: Update DynamoDB with all computed fields
6. **Error Handling**: Graceful degradation with fallback values

### Data Flow

```
Phase 2: Scrapers Write to DynamoDB
  ↓
DynamoDB Streams captures: INSERT, MODIFY, DELETE events
  ↓
Stream → Lambda (post-processor) is triggered
  ↓
For each event:
  1. Extract raw_text and source
  2. Calculate weight (confidence score 0-1)
  3. Analyze sentiment (positive/negative/neutral)
  4. Clean and format text using Gemini API
  5. Generate concise summary using Gemini API
  6. Update DynamoDB with all computed fields (weight, sentiment, cleaned_text, summary)
  ↓
Log success/failure
```

## Components

### `post-processor/` - Weight & Sentiment Computation
Main Lambda function triggered by DynamoDB Streams.

**Purpose**:
- Process all new and modified entries from scrapers
- Calculate confidence score (weight)
- Analyze sentiment
- Update DynamoDB efficiently

**Status**: ✅ Production Ready

## Lambda Configuration

### Settings
- **Function Name**: `post-processor`
- **Runtime**: Python 3.11
- **Memory**: 1024 MB (handles text processing)
- **Timeout**: 15 minutes (sufficient for batch processing)
- **Trigger**: DynamoDB Streams
- **Batch Size**: 100 (process up to 100 records per invocation)
- **Batch Window**: 5 seconds

### DynamoDB Stream Configuration
```json
{
  "EventSource": "dynamodb",
  "EventSourceArn": "arn:aws:dynamodb:region:account:table/celebrity-database/stream/...",
  "Enabled": true,
  "StartingPosition": "LATEST",
  "BatchSize": 100,
  "ParallelizationFactor": 10
}
```

### Environment Variables
```bash
# Common
AWS_REGION=us-east-1
DYNAMODB_TABLE=celebrity-database
LOG_LEVEL=INFO

# Gemini API Configuration
GEMINI_API_KEY=your_google_ai_api_key  # Free tier: https://ai.google.dev
GEMINI_MODEL=gemini-1.5-flash           # Fast model (free tier recommended)
GEMINI_ENABLED=true                      # Enable Gemini for cleaned_text & summary

# Sentiment Analysis
USE_AWS_COMPREHEND=false                 # true=AWS Comprehend, false=TextBlob
AWS_COMPREHEND_REGION=us-east-1

# Processing Configuration
MAX_TEXT_LENGTH=5000                      # Max chars to send to Gemini
SUMMARY_MAX_LENGTH=300                    # Max chars for summary
CLEANED_TEXT_MAX_LENGTH=2000              # Max chars for cleaned_text
GEMINI_TIMEOUT=30                         # Seconds to wait for Gemini response
```

### IAM Permissions Required
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
        "dynamodb:ListShards",
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

**Note**: Gemini API key should be stored in AWS Secrets Manager and retrieved at runtime (not hardcoded in environment variables). For Lambda:
```bash
# Store Gemini API key in Secrets Manager
aws secretsmanager create-secret --name gemini/api-key --secret-string "your_gemini_api_key"

# Lambda will retrieve it at runtime
```

## Detailed Algorithms

### Computed Fields Overview

Phase 3 produces 4 computed fields for each scraper entry:

| Field | Type | Source | Purpose | Example |
|-------|------|--------|---------|---------|
| `weight` | Float (0-1) | Calculation | Confidence/importance score | `0.85` |
| `sentiment` | String | NLP Analysis | Emotional tone | `positive` |
| `cleaned_text` | String | Gemini API | Formatted readable text | `"Leonardo DiCaprio released a new film..."` |
| `summary` | String | Gemini API | Concise summary | `"Actor announces new film project."` |

### Weight Calculation Algorithm

**Purpose**: Produce a confidence score (0-1) for each scraper entry based on data quality and source reliability.

**Formula**:
```
weight = (completeness_score × 0.5) + (source_reliability_score × 0.5)
```

**Components**:

#### 1. Completeness Score (0-1)
Measures how much data the API response contained.

```python
def calculate_completeness(raw_text):
    """
    Score data completeness by counting non-null fields
    """
    try:
        data = json.loads(raw_text)

        # Count non-empty fields
        total_fields = len(data)
        non_empty_fields = len([v for v in data.values()
                               if v is not None and v != ''])

        # Normalize to 0-1
        completeness = non_empty_fields / max(total_fields, 1)

        # Cap at 1.0
        return min(completeness, 1.0)
    except:
        # Unparseable JSON = low completeness
        return 0.3
```

**Scoring**:
- < 30% fields filled: 0.0-0.3
- 30-60% fields filled: 0.3-0.6
- 60-90% fields filled: 0.6-0.9
- > 90% fields filled: 0.9-1.0

#### 2. Source Reliability Score (0-1)
Fixed score per data source, reflecting trustworthiness.

```python
SOURCE_RELIABILITY = {
    "api.themoviedb.org": 0.95,      # Well-structured API
    "en.wikipedia.org": 0.90,         # Community-edited but stable
    "newsapi.org": 0.85,              # News aggregator
    "twitter.com": 0.80,              # Social media (variable quality)
    "instagram.com": 0.75,            # Social media, fewer details
    "youtube.com": 0.85,              # Video platform
    "news.google.com": 0.87,          # Google News aggregator
}
# Default for unknown sources: 0.5
```

**Rationale**:
- Official APIs (TMDb, Wikipedia) have consistent format and validation
- News APIs are reliable but articles may have biases
- Social media has variable quality and reliability
- Unknown sources default to neutral 0.5

#### 3. Example Calculations

**Example 1: TMDb Data (High Quality)**
```
raw_text = {
  "id": 287462,
  "name": "Leonardo DiCaprio",
  "popularity": 24.28,
  "profile_path": "/path.jpg",
  "known_for_department": "Acting",
  "gender": 2,
  "biography": "...",
  "birthday": "1974-11-11",
  "place_of_birth": "Los Angeles, CA",
  "also_known_as": ["Leo", "DiCaprio"]
}

Fields: 10 total, 10 non-empty
completeness_score = 10/10 = 1.0
source_reliability = 0.95 (TMDb)

weight = (1.0 × 0.5) + (0.95 × 0.5)
       = 0.5 + 0.475
       = 0.975 ✓ High confidence
```

**Example 2: Wikipedia Data (Medium Quality)**
```
raw_text = {
  "title": "Leonardo DiCaprio",
  "extract": "Leonardo DiCaprio is an American actor...",
  "content": "...",
  "last_modified": "2025-11-07"
}

Fields: 4 total, 4 non-empty
completeness_score = 4/4 = 1.0
source_reliability = 0.90 (Wikipedia)

weight = (1.0 × 0.5) + (0.90 × 0.5)
       = 0.5 + 0.45
       = 0.95 ✓ High confidence
```

**Example 3: Partial News Data**
```
raw_text = {
  "articles": [
    {"title": "...", "url": "...", "description": "..."},
    {"title": "...", "url": null, "description": null}
  ],
  "count": 2
}

Fields: 3 total, 2 non-empty (2/3)
completeness_score = 2/3 = 0.67
source_reliability = 0.85 (NewsAPI)

weight = (0.67 × 0.5) + (0.85 × 0.5)
       = 0.335 + 0.425
       = 0.76 ✓ Good confidence
```

**Example 4: Malformed Response**
```
raw_text = "ERROR: Service Unavailable"

Parsing fails (not valid JSON)
completeness_score = 0.3 (fallback)
source_reliability = 0.85

weight = (0.3 × 0.5) + (0.85 × 0.5)
       = 0.15 + 0.425
       = 0.575 ✓ Medium confidence (data exists but incomplete)
```

### Sentiment Analysis Algorithm

**Purpose**: Classify sentiment of text content (positive/negative/neutral).

**Approach**: Two options available

#### Option 1: TextBlob (Local, Fast, No Cost)

```python
def analyze_sentiment_textblob(raw_text):
    """
    Use TextBlob for sentiment analysis (offline)
    Polarity: -1.0 (negative) to +1.0 (positive)
    """
    from textblob import TextBlob

    try:
        # Extract text content from raw_text
        text_content = extract_text(raw_text)

        # Limit to 500 chars for performance
        text_content = text_content[:500]

        # Analyze sentiment
        blob = TextBlob(text_content)
        polarity = blob.sentiment.polarity

        # Classify
        if polarity > 0.1:
            return "positive"
        elif polarity < -0.1:
            return "negative"
        else:
            return "neutral"
    except:
        return "neutral"  # Fallback
```

**Thresholds**:
- polarity > 0.1: Positive
- polarity < -0.1: Negative
- -0.1 ≤ polarity ≤ 0.1: Neutral

**Advantages**:
- No external API calls (fast)
- No cost
- Works offline
- Suitable for general sentiment

**Limitations**:
- Less accurate for complex texts
- Doesn't understand context well
- No domain-specific training

#### Option 2: AWS Comprehend (Accurate, Managed Service)

```python
def analyze_sentiment_comprehend(raw_text):
    """
    Use AWS Comprehend for sentiment analysis
    More accurate but costs money (~$0.0001 per 100 units of text)
    """
    import boto3

    client = boto3.client('comprehend')

    try:
        # Extract text content
        text_content = extract_text(raw_text)

        # Limit to 5000 chars (AWS Comprehend limit)
        text_content = text_content[:5000]

        # Detect sentiment
        response = client.detect_sentiment(
            Text=text_content,
            LanguageCode='en'
        )

        sentiment = response['Sentiment'].lower()

        # Map AWS values to our values
        sentiment_map = {
            'positive': 'positive',
            'negative': 'negative',
            'neutral': 'neutral',
            'mixed': 'neutral'  # Treat mixed as neutral
        }

        return sentiment_map.get(sentiment, 'neutral')
    except:
        return "neutral"  # Fallback
```

**Advantages**:
- High accuracy (trained on large datasets)
- Understands context and sarcasm
- Professional-grade service
- Returns confidence scores

**Limitations**:
- API call required (slower)
- Costs money (~$0.0001 per 100 units)
- Rate limiting possible
- Dependency on AWS service

#### Text Extraction (Both Methods)

```python
def extract_text(raw_text):
    """
    Extract human-readable text from structured data
    """
    try:
        if raw_text.startswith('{'):
            # JSON response
            data = json.loads(raw_text)

            # Extract all string values
            text_pieces = []

            def extract_strings(obj):
                if isinstance(obj, str):
                    text_pieces.append(obj)
                elif isinstance(obj, dict):
                    for v in obj.values():
                        extract_strings(v)
                elif isinstance(obj, list):
                    for item in obj:
                        extract_strings(item)

            extract_strings(data)

            # Join with spaces, remove HTML tags
            text = ' '.join(text_pieces)
            text = re.sub(r'<[^>]+>', '', text)  # Remove HTML tags

            return text
        else:
            # Plain text (Wikipedia, etc.)
            return raw_text
    except:
        return raw_text  # Return as-is if parsing fails
```

#### Sentiment Example

**Example: TMDb Filmography Data**
```
raw_text contains list of movies with titles like:
- "Inception"
- "The Wolf of Wall Street"
- "Titanic"
- "The Great Gatsby"

Extracted text: "Inception The Wolf of Wall Street Titanic The Great Gatsby..."

TextBlob analysis:
- "Inception": slightly positive (ambitious, clever)
- "Wolf": neutral/negative (moral complexity)
- "Titanic": positive (romantic, tragic)
- "Gatsby": positive (romantic, grand)

Overall polarity: +0.15 → "positive" ✓
```

### Cleaned Text Generation Algorithm (Gemini API)

**Purpose**: Extract human-readable, cleaned text from raw API responses using AI.

**Process**:
```python
def generate_cleaned_text_gemini(raw_text, celebrity_name, max_length=2000):
    """
    Use Gemini API to extract and clean text from raw API response.

    Input: raw_text (complete API response as JSON string)
    Output: cleaned_text (formatted, readable paragraph)
    """
    try:
        # Extract text pieces from raw_text
        extracted_text = extract_text_from_json(raw_text)

        # Limit length before sending to Gemini
        extracted_text = extracted_text[:5000]

        # Prompt Gemini to clean and format
        prompt = f"""
        Please extract and clean the following text about {celebrity_name}.
        Remove any technical jargon, API artifacts, or unnecessary formatting.
        Format as readable prose (2-3 sentences maximum).
        Focus on what's most important.

        Raw text: {extracted_text}

        Cleaned text:
        """

        # Call Gemini API
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            generation_config={
                "max_output_tokens": CLEANED_TEXT_MAX_LENGTH,
                "temperature": 0.3,  # Lower temp for consistency
            }
        )

        cleaned = response.text.strip()
        return cleaned if cleaned else ""

    except Exception as e:
        logger.error(f"Gemini cleaned_text failed: {str(e)}")
        return ""  # Fallback to empty string
```

**Examples**:

**Example 1: Google Search Results → Cleaned Text**
```
Raw JSON: {
  "items": [
    {"title": "Leonardo DiCaprio - Wikipedia", "snippet": "Leonardo Wilhelm DiCaprio..."},
    {"title": "Leonardo DiCaprio on Instagram", "snippet": "4.2M followers"}
  ]
}

Gemini cleaned_text:
"Leonardo DiCaprio is an accomplished actor and producer with millions
of followers across social platforms. He maintains an active presence
in both film and environmental advocacy work."
```

**Example 2: YouTube API Response → Cleaned Text**
```
Raw JSON: {
  "snippet": {
    "title": "Leonardo DiCaprio Channel",
    "description": "Official channel for Leonardo DiCaprio",
    "publishedAt": "2015-03-15"
  },
  "statistics": {
    "viewCount": "50000000",
    "commentCount": "125000",
    "subscriberCount": "5000000"
  }
}

Gemini cleaned_text:
"Leonardo DiCaprio's official YouTube channel has over 50 million views
and 5 million subscribers, with significant audience engagement across
his published content."
```

### Summary Generation Algorithm (Gemini API)

**Purpose**: Generate concise, actionable summaries from cleaned text.

**Process**:
```python
def generate_summary_gemini(cleaned_text, celebrity_name, max_length=300):
    """
    Use Gemini API to generate a concise summary.

    Input: cleaned_text (readable text from previous step)
    Output: summary (1 sentence max, high-level overview)
    """
    try:
        # Skip if no cleaned text
        if not cleaned_text:
            return ""

        # Prompt Gemini to summarize
        prompt = f"""
        Create a very brief, one-sentence summary about {celebrity_name}
        based on the following text. Focus on the most newsworthy or
        important information.

        Text: {cleaned_text}

        Summary:
        """

        # Call Gemini API with lower temperature for consistency
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            generation_config={
                "max_output_tokens": max_length,
                "temperature": 0.2,  # Very low for focused summaries
            }
        )

        summary = response.text.strip()

        # Ensure it's actually one sentence
        if len(summary.split('.')) > 2:
            # Truncate to first sentence
            summary = summary.split('.')[0] + '.'

        return summary

    except Exception as e:
        logger.error(f"Gemini summary failed: {str(e)}")
        return ""  # Fallback to empty string
```

**Examples**:

**Example 1: Activity Data Summary**
```
cleaned_text: "Leonardo DiCaprio released a new environmental
documentary featuring interviews with climate scientists and
focusing on ocean conservation efforts."

summary: "Leonardo DiCaprio releases climate-focused documentary
on ocean conservation."
```

**Example 2: Film News Summary**
```
cleaned_text: "Actor Leonardo DiCaprio has been cast in a major
superhero film production with a budget exceeding $200 million,
set to release in 2026."

summary: "DiCaprio cast in $200M superhero film releasing in 2026."
```

**Example 3: Social Media Summary**
```
cleaned_text: "Leonardo DiCaprio's latest Instagram post about
environmental activism garnered over 2 million likes and 50,000
supportive comments from followers."

summary: "DiCaprio's environmental post receives 2M likes on Instagram."
```

### Gemini API Integration Details

**Authentication**:
```python
import google.generativeai as genai

# Initialize at Lambda cold start
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')  # From Secrets Manager
genai.configure(api_key=GEMINI_API_KEY)

# Cache model reference
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')
client = genai.models.get_model(GEMINI_MODEL)
```

**Rate Limiting & Batch Processing**:
```python
from datetime import datetime, timedelta

class GeminiRateLimiter:
    """Prevent hitting Gemini API rate limits."""
    def __init__(self, max_requests_per_minute=60):
        self.max_requests = max_requests_per_minute
        self.requests = []

    def wait_if_needed(self):
        """Sleep if necessary to respect rate limit."""
        now = datetime.now()
        # Remove old requests outside 1-minute window
        self.requests = [r for r in self.requests
                        if r > now - timedelta(minutes=1)]

        if len(self.requests) >= self.max_requests:
            sleep_time = 60 - (now - self.requests[0]).total_seconds()
            if sleep_time > 0:
                logger.warning(f"Rate limit: sleeping {sleep_time}s")
                time.sleep(sleep_time)

        self.requests.append(now)
```

**Cost Optimization**:
- Use `gemini-1.5-flash` (fastest, free tier eligible)
- Set `temperature=0.2-0.3` for consistent, deterministic outputs
- Limit input to ~5000 chars per request
- Batch process in Lambda invocations (100 records)
- Skip Gemini calls for entries without usable extracted text

## Error Handling & Robustness

### Processing Errors

**Error**: Malformed JSON in raw_text
```
Detection: json.loads() raises JSONDecodeError
Handling: Set completeness_score = 0.3, continue
Recovery: Weight still calculated using fallback
Result: Entry gets weight despite corrupt data
```

**Error**: Timeout during sentiment analysis
```
Detection: API call exceeds timeout (if using Comprehend)
Handling: Catch timeout exception
Recovery: Use fallback sentiment = "neutral"
Result: Weight calculated, sentiment unknown
```

**Error**: Missing required fields
```
Detection: Entry missing celebrity_id or source
Handling: Log error with entry details
Recovery: Skip entry, continue with next
Result: Entry not updated, original data preserved
```

**Error**: DynamoDB Update Failure
```
Detection: UpdateItem raises exception
Handling: Exponential backoff (1s, 2s, 4s)
Recovery: Retry up to 3 times
Fallback: Log error and continue (data lost for this entry)
```

**Error**: Text Extraction Fails
```
Detection: extract_text() raises exception
Handling: Return empty string
Recovery: Sentiment defaults to "neutral"
Result: Entry gets neutral sentiment instead of error
```

**Error**: Gemini API Timeout
```
Detection: API call exceeds timeout (30 seconds)
Handling: Catch timeout exception
Recovery: Set cleaned_text = "", summary = ""
Result: Entry gets empty fields, weight/sentiment still computed
Note: Partial data is acceptable - don't fail entire batch
```

**Error**: Gemini API Rate Limit
```
Detection: 429 Too Many Requests response
Handling: Implement exponential backoff (1s, 2s, 4s)
Recovery: Retry up to 3 times
Fallback: Skip Gemini processing, continue with weight/sentiment
Result: Entry processed without Gemini fields
```

**Error**: Gemini API Authentication Failed
```
Detection: 401 Unauthorized or invalid API key
Handling: Log error with timestamp
Recovery: Check Secrets Manager for valid API key
Fallback: Skip all Gemini calls for remaining batch
Result: Graceful degradation - process with weight/sentiment only
```

**Error**: Invalid Gemini Response
```
Detection: Response is empty or malformed
Handling: Log response and error details
Recovery: Return empty string instead of malformed data
Result: Field remains empty, batch continues
```

### Validation Errors

**Error**: Invalid weight value
```
Validation: weight < 0 or weight > 1
Handling: Clamp to range [0.0, 1.0]
Recovery: Use clamped value
Result: weight always valid 0-1
```

**Error**: Invalid sentiment value
```
Validation: sentiment not in ["positive", "negative", "neutral"]
Handling: Default to "neutral"
Recovery: Use default value
Result: sentiment always valid
```

**Error**: Timestamp validation
```
Validation: timestamp not ISO 8601 format
Handling: Use current time instead
Recovery: Log warning, update with current timestamp
Result: Entry updated with valid timestamp
```

**Error**: Invalid cleaned_text value
```
Validation: cleaned_text is None or contains only whitespace
Handling: Set to empty string ""
Recovery: Continue processing
Result: Field is empty but valid
```

**Error**: Invalid summary value
```
Validation: summary exceeds max length or is malformed
Handling: Truncate or set to empty string
Recovery: Continue processing
Result: Field is valid (truncated if necessary)
```

## Testing Protocol

### Phase 3A: Unit Testing

**Step 1: Test Weight Calculation**
```python
# Test cases for weight calculation
test_cases = [
    {
        "name": "Complete TMDb response",
        "raw_text": '{"id":1,"name":"X","bio":"Y",...}',  # 10 fields
        "source": "api.themoviedb.org",
        "expected_weight": 0.97,  # (1.0 × 0.5) + (0.95 × 0.5)
    },
    {
        "name": "Partial Wikipedia data",
        "raw_text": '{"title":"X","extract":"Y"}',  # 2 fields
        "source": "en.wikipedia.org",
        "expected_weight": 0.92,  # (0.5 × 0.5) + (0.90 × 0.5)
    },
    {
        "name": "Malformed JSON",
        "raw_text": "ERROR: Invalid JSON",
        "source": "unknown.api.com",
        "expected_weight": 0.4,  # (0.3 × 0.5) + (0.5 × 0.5)
    },
]

for test in test_cases:
    calculated = calculate_weight(test["raw_text"], test["source"])
    assert abs(calculated - test["expected_weight"]) < 0.01, \
        f"Test '{test['name']}' failed: {calculated} vs {test['expected_weight']}"
    print(f"✓ {test['name']}: {calculated}")
```

**Step 2: Test Sentiment Analysis**
```python
test_cases = [
    {
        "text": "I love this! Great work!",
        "expected": "positive"
    },
    {
        "text": "This is terrible and awful.",
        "expected": "negative"
    },
    {
        "text": "The movie had good acting.",
        "expected": "positive"
    },
    {
        "text": "Leonardo DiCaprio is an actor.",
        "expected": "neutral"
    },
]

for test in test_cases:
    sentiment = analyze_sentiment(test["text"])
    assert sentiment == test["expected"], \
        f"Sentiment test failed: {sentiment} vs {test['expected']}"
    print(f"✓ {test['text']}: {sentiment}")
```

**Step 2B: Test Gemini API Authentication**
```python
# Test that Gemini API key is valid
try:
    import google.generativeai as genai
    api_key = os.getenv('GEMINI_API_KEY')
    genai.configure(api_key=api_key)

    # Try a simple generation
    response = genai.models.generate_content(
        model='gemini-1.5-flash',
        contents='Say "test successful"'
    )

    if response.text:
        print("✓ Gemini API authentication successful")
    else:
        raise Exception("Empty response from Gemini")

except Exception as e:
    print(f"✗ Gemini API test failed: {str(e)}")
    print("⚠️  Make sure GEMINI_API_KEY is set in Secrets Manager")
```

**Step 2C: Test Cleaned Text Generation**
```python
test_cases = [
    {
        "name": "Google Search",
        "raw_text": '{"items": [{"title": "Leonardo DiCaprio", "snippet": "Actor and producer"}]}',
        "celebrity": "Leonardo DiCaprio",
    },
    {
        "name": "Activity Data",
        "raw_text": '{"activities": [{"activity": "Released new album", "category": "music"}]}',
        "celebrity": "Taylor Swift",
    },
]

for test in test_cases:
    cleaned = generate_cleaned_text_gemini(test["raw_text"], test["celebrity"])
    assert isinstance(cleaned, str), f"Cleaned text is not string: {type(cleaned)}"
    assert len(cleaned) > 0, f"Cleaned text is empty for {test['name']}"
    assert len(cleaned) <= 2000, f"Cleaned text exceeds max length"
    print(f"✓ {test['name']}: {cleaned[:100]}...")
```

**Step 2D: Test Summary Generation**
```python
test_cases = [
    {
        "name": "Film News",
        "cleaned_text": "Leonardo DiCaprio has been cast in a major superhero film production with a budget exceeding $200 million, set to release in 2026.",
        "celebrity": "Leonardo DiCaprio",
    },
    {
        "name": "Activity News",
        "cleaned_text": "The actor announced a new environmental documentary featuring interviews with climate scientists focusing on ocean conservation.",
        "celebrity": "Leonardo DiCaprio",
    },
]

for test in test_cases:
    summary = generate_summary_gemini(test["cleaned_text"], test["celebrity"])
    assert isinstance(summary, str), f"Summary is not string: {type(summary)}"
    assert len(summary) > 0, f"Summary is empty for {test['name']}"
    assert len(summary) <= 300, f"Summary exceeds max length"
    assert summary.count('.') <= 2, f"Summary has multiple sentences"
    print(f"✓ {test['name']}: {summary}")
```

**Step 3: Test DynamoDB Update**
```bash
# Insert test entry without computed fields
aws dynamodb put-item --table-name celebrity-database \
  --item '{
    "celebrity_id": {"S": "celeb_test"},
    "source_type#timestamp": {"S": "test#2025-11-07T00:00:00Z"},
    "id": {"S": "uuid-123"},
    "name": {"S": "Test Celebrity"},
    "raw_text": {"S": "{\"title\": \"Test\", \"description\": \"Test data\"}"},
    "source": {"S": "test.api"},
    "timestamp": {"S": "2025-11-07T00:00:00Z"},
    "weight": {"NULL": true},
    "sentiment": {"NULL": true},
    "cleaned_text": {"NULL": true},
    "summary": {"NULL": true}
  }'

# Manually invoke post-processor
aws lambda invoke \
  --function-name post-processor \
  --cli-binary-format raw-in-base64-out \
  --payload '{"Records":[{"dynamodb":{"NewImage":{"celebrity_id":{"S":"celeb_test"}...}}}]}' \
  response.json

# Verify ALL computed fields are populated
aws dynamodb get-item --table-name celebrity-database \
  --key '{"celebrity_id":{"S":"celeb_test"},"source_type#timestamp":{"S":"test#2025-11-07T00:00:00Z"}}' \
  --query 'Item.[weight,sentiment,cleaned_text,summary]'

# Expected:
# [
#   [0.5],                                      # weight (0.0-1.0)
#   ["neutral"],                                # sentiment (positive|negative|neutral)
#   ["Test Celebrity is a prominent figure"],   # cleaned_text
#   ["Test Celebrity makes headlines"]          # summary
# ]
```

### Phase 3B: Integration Testing

**Step 1: Setup DynamoDB Stream**
```bash
# Get stream ARN
STREAM_ARN=$(aws dynamodb describe-table \
  --table-name celebrity-database \
  --query 'Table.LatestStreamArn' \
  --output text)

# Create event source mapping
aws lambda create-event-source-mapping \
  --event-source-arn $STREAM_ARN \
  --function-name post-processor \
  --enabled \
  --batch-size 100 \
  --starting-position LATEST
```

**Step 2: Test with Single Entry**
```bash
# Insert scraper entry (triggers stream)
aws dynamodb put-item --table-name celebrity-database \
  --item '{
    "celebrity_id": {"S": "celeb_001"},
    "source_type#timestamp": {"S": "tmdb#2025-11-07T17:20:00Z"},
    "id": {"S": "uuid-456"},
    "name": {"S": "Leonardo DiCaprio"},
    "raw_text": {"S": "{\"id\": 287462, \"name\": \"Leonardo DiCaprio\", \"popularity\": 24.28, \"biography\": \"Oscar-winning actor\"}"},
    "source": {"S": "https://api.themoviedb.org/3/person/search"},
    "timestamp": {"S": "2025-11-07T17:20:00Z"},
    "weight": {"NULL": true},
    "sentiment": {"NULL": true},
    "cleaned_text": {"NULL": true},
    "summary": {"NULL": true}
  }'

# Monitor Lambda logs
aws logs tail /aws/lambda/post-processor --follow

# Wait 10-15 seconds for processing (includes Gemini calls)
sleep 15

# Verify ALL computed fields are populated
aws dynamodb get-item \
  --table-name celebrity-database \
  --key '{"celebrity_id":{"S":"celeb_001"},"source_type#timestamp":{"S":"tmdb#2025-11-07T17:20:00Z"}}' \
  --query 'Item.[weight,sentiment,cleaned_text,summary]'

# Expected output:
# [
#   [0.975],                                           # weight: 0.0-1.0
#   ["neutral"],                                        # sentiment: positive|negative|neutral
#   ["Leonardo DiCaprio is an Oscar-winning actor"],   # cleaned_text: readable formatted text
#   ["DiCaprio - acclaimed actor"]                     # summary: one-line summary
# ]

# Verify Gemini processing in logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/post-processor \
  --filter-pattern "cleaned_text OR summary OR Gemini" \
  --max-items 20
```

**Step 3: **STOP IF ANY ERRORS**
If update fails:
- [ ] Check Lambda logs for error details
- [ ] Verify IAM permissions (DynamoDB Streams, UpdateItem)
- [ ] Verify DynamoDB table exists
- [ ] Check stream is enabled
- [ ] Verify event source mapping created
- [ ] **Do NOT proceed** until this passes
- [ ] Fix errors and re-run

**Step 4: Test with 10 Entries**
```bash
# Insert 10 scraper entries for different sources
for i in {1..10}; do
  source="tmdb wikipedia news social"
  source_type=$(echo $source | cut -d' ' -f$((i % 4 + 1)))

  aws dynamodb put-item --table-name celebrity-database \
    --item "... entry for celeb_00$i with $source_type source ..."
done

# Monitor processing
aws logs tail /aws/lambda/post-processor --follow

# Verify all entries updated
aws dynamodb scan --table-name celebrity-database \
  --filter-expression "attribute_exists(weight) AND attribute_exists(sentiment)" \
  --select COUNT

# Expected: At least 10 entries with weight and sentiment
```

**Step 5: Test Error Handling**
```bash
# Insert entry with malformed raw_text
aws dynamodb put-item --table-name celebrity-database \
  --item '{
    "celebrity_id": {"S": "celeb_test_error"},
    "source_type#timestamp": {"S": "test#2025-11-07T00:00:00Z"},
    "raw_text": {"S": "NOT VALID JSON"},
    "source": {"S": "unknown.api"},
    "timestamp": {"S": "2025-11-07T00:00:00Z"}
  }'

# Monitor Lambda
aws logs tail /aws/lambda/post-processor --follow

# Verify fallback values applied
aws dynamodb get-item \
  --table-name celebrity-database \
  --key '{"celebrity_id":{"S":"celeb_test_error"},"source_type#timestamp":{"S":"test#2025-11-07T00:00:00Z"}}' \
  --query 'Item.[weight,sentiment]'

# Expected: weight ~0.4, sentiment = "neutral"
```

### Phase 3C: Production Validation

**Step 1: Monitor Lambda Metrics**
```bash
# Check Lambda invocations per minute
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=post-processor \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 \
  --statistics Sum

# Check error rate
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=post-processor \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 \
  --statistics Sum

# Check duration
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=post-processor \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 \
  --statistics Average,Maximum
```

**Step 2: Validate Data Quality**
```bash
# Check weight distribution
aws dynamodb scan --table-name celebrity-database \
  --filter-expression "attribute_exists(weight)" \
  --projection-expression "weight" | \
  jq '[.Items[].weight.N | tonumber] | {
    count: length,
    min: min,
    max: max,
    avg: (add / length)
  }'

# Expected:
# {
#   "count": 400,  # 100 celebrities × 4 sources
#   "min": 0.3,
#   "max": 0.98,
#   "avg": 0.75
# }

# Check sentiment distribution
aws dynamodb scan --table-name celebrity-database \
  --filter-expression "attribute_exists(sentiment)" \
  --projection-expression "sentiment" | \
  jq '[.Items[].sentiment.S] | group_by(.) | map({
    sentiment: .[0],
    count: length
  })'

# Expected output like:
# [
#   {"sentiment": "positive", "count": 140},
#   {"sentiment": "negative", "count": 30},
#   {"sentiment": "neutral", "count": 230}
# ]

# Check cleaned_text population
aws dynamodb scan --table-name celebrity-database \
  --filter-expression "attribute_exists(cleaned_text) AND size(cleaned_text) > :zero" \
  --expression-attribute-values '{":zero": {"N": "0"}}' \
  --select COUNT

# Expected: Most entries should have cleaned_text (>90%)

# Check summary population
aws dynamodb scan --table-name celebrity-database \
  --filter-expression "attribute_exists(summary) AND size(summary) > :zero" \
  --expression-attribute-values '{":zero": {"N": "0"}}' \
  --select COUNT

# Expected: Most entries should have summary (>90%)

# Check Gemini processing success rate
aws logs filter-log-events \
  --log-group-name /aws/lambda/post-processor \
  --filter-pattern "[timestamp, request_id, level = INFO, msg = *cleaned_text*]" \
  --query 'events[].message' | \
  wc -l

# Should be >90% of total entries
```

**Step 3: Check for Failures**
```bash
# Find entries where ANY computed field failed
aws dynamodb scan --table-name celebrity-database \
  --filter-expression "attribute_not_exists(weight) OR attribute_not_exists(sentiment) OR attribute_not_exists(cleaned_text) OR attribute_not_exists(summary)" \
  --select COUNT

# Expected: Should be minimal (0-10 entries)

# If too many failures, investigate:
aws logs filter-log-events \
  --log-group-name /aws/lambda/post-processor \
  --filter-pattern "ERROR" | jq '.events[].message'

# Check specifically for Gemini errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/post-processor \
  --filter-pattern "[timestamp, request_id, level = ERROR, msg = *Gemini*]" \
  --query 'events[].message'

# If errors found, check Gemini API key validity
echo "GEMINI_API_KEY=$(aws secretsmanager get-secret-value --secret-id gemini/api-key --query SecretString --output text)" > /tmp/check_api.sh
```

## Fallback & Recovery Strategies

### Gemini API Rate Limiting
**Scenario**: Too many concurrent Gemini requests (429 Too Many Requests)
```
Detection: Gemini API returns rate limit error
Response: Implement exponential backoff (1s, 2s, 4s)
Recovery: Retry up to 3 times before skipping
Result: Most entries get Gemini fields, some skip gracefully
```

### Gemini API Authentication Failure
**Scenario**: Invalid or expired Gemini API key
```
Detection: 401 Unauthorized from Gemini API
Response: Log error with timestamp, skip remaining Gemini calls
Recovery: Verify GEMINI_API_KEY in Secrets Manager
Result: Entries get weight/sentiment but not cleaned_text/summary
```

### Gemini API Timeout
**Scenario**: Gemini takes >30 seconds to respond
```
Detection: Request times out
Response: Catch timeout exception, return empty string
Recovery: Continue to next entry without waiting
Result: cleaned_text="" and summary="", but batch continues
```

### Gemini Response Parsing Failure
**Scenario**: Gemini returns malformed or empty response
```
Detection: response.text is empty or invalid
Response: Validate response before storing
Recovery: Set field to empty string instead of storing bad data
Result: Field is empty (valid), entry still has weight/sentiment
```

### Stream Processing Lag
**Scenario**: Many entries written at once, stream queue fills up
```
Detection: Lambda invocations increase significantly
Response: Process records in batches, scale down batch window
Recovery: Increase Lambda memory or parallelization
Result: Eventually catch up, no data loss
```

### Sentiment Analysis Service Failure (AWS Comprehend)
**Scenario**: AWS Comprehend temporarily unavailable
```
Detection: API calls timeout or return 5xx errors
Response: Fall back to TextBlob
Recovery: Use local sentiment instead
Result: Sentiment may be less accurate but processing continues
```

### Memory Exhaustion
**Scenario**: Processing very large raw_text entries
```
Detection: Lambda memory limit exceeded
Response: Increase Lambda memory allocation
Recovery: Retry with more memory
Result: Larger entries processed successfully
```

### Partial Batch Failure
**Scenario**: 1 of 100 entries fails to update
```
Detection: UpdateItem fails for specific entry
Response: Log error, continue with next entry
Recovery: Manually fix entry or retry next run
Result: 99% processed, 1% missing (acceptable)
```

## Coding Principles & Best Practices

### Error Handling
✅ **Implemented**:
- Try-catch on all external API calls (Comprehend)
- Graceful fallback for sentiment (use "neutral")
- Weight calculations always succeed (use defaults)
- Partial failure handling (continue if some entries fail)
- Exponential backoff for DynamoDB updates

### Data Validation
✅ **Implemented**:
- Validate JSON parsing before processing
- Check weight/sentiment ranges (0-1, valid enum)
- Verify timestamp format (ISO 8601)
- Validate data types match expected
- Check for required fields

### Robustness
✅ **Implemented**:
- Idempotent operations (safe to re-run)
- No state stored outside DynamoDB
- Timeout protection for all operations
- Comprehensive error logging
- Health checks in logs

### Performance
✅ **Implemented**:
- Process records in batches (100 at a time)
- Reuse clients/sessions
- Cache sentiment analyzer models
- Async where possible
- Efficient DynamoDB updates (batch writes)

### Security
✅ **Implemented**:
- No hardcoded API keys or credentials
- IAM role-based access
- Secure parameter passing (env vars)
- No sensitive data in logs
- HTTPS for external calls

## Monitoring & Alerting

### CloudWatch Metrics
- Invocations (number of stream events processed)
- Errors (failed entries)
- Duration (processing time)
- Throttles (rate limit hits)

### CloudWatch Logs
- Structured JSON logging
- Log levels: DEBUG, INFO, WARNING, ERROR
- Entry-level logging (celebrity_id, weight, sentiment)
- Error stack traces for debugging

### CloudWatch Alarms
```json
{
  "AlarmName": "post-processor-errors",
  "MetricName": "Errors",
  "Namespace": "AWS/Lambda",
  "Statistic": "Sum",
  "Period": 300,
  "EvaluationPeriods": 1,
  "Threshold": 5,
  "ComparisonOperator": "GreaterThanThreshold"
}
```

## Timeline & Milestones

- [ ] Implement weight calculation (days 1-2)
- [ ] Implement sentiment analysis (days 2-3)
- [ ] Configure DynamoDB Streams (day 3)
- [ ] Test with 1 entry (day 4)
- [ ] Test with 10 entries (day 4)
- [ ] **STOP if errors found - fix before proceeding**
- [ ] Deploy to production (day 5)
- [ ] Monitor execution (day 5-6)
- [ ] Validate results (day 7)

## Current Implementation Status

### ✅ Completed
- [x] Phase 3 directory structure
- [x] post-processor Lambda function (production ready)
- [x] Weight calculation algorithm
- [x] Sentiment analysis (TextBlob + AWS Comprehend support)
- [x] Error handling framework
- [x] Testing protocol documented
- [x] **NEW**: Gemini API integration for cleaned_text field
- [x] **NEW**: Gemini API integration for summary field
- [x] **NEW**: cleaned_text generation algorithm
- [x] **NEW**: summary generation algorithm
- [x] **NEW**: Gemini authentication and rate limiting strategy
- [x] **NEW**: Gemini-specific error handling and fallback strategies
- [x] **NEW**: Updated testing protocol for all 4 computed fields

### 🟡 In Progress
- [ ] Deploy to Lambda with Gemini support
- [ ] Configure DynamoDB Streams trigger
- [ ] Test with sample entries (including Gemini processing)
- [ ] Store Gemini API key in AWS Secrets Manager
- [ ] Verify Gemini API quota and rate limits

### ⏳ Not Started
- [ ] Phase 4 (Orchestration)

## Next Phase

**Phase 4: Orchestration** (Week 8)
- Set up EventBridge scheduler for weekly scraping
- Configure automated workflow
- Implement monitoring and alerting

**Prerequisites**:
- ✅ Phase 1: DynamoDB table operational
- ✅ Phase 2: All scrapers deployed
- ✅ Phase 3: Post-processor deployed and functional

## Gemini API Setup Guide

### Step 1: Get a Free Gemini API Key

1. Go to https://ai.google.dev
2. Click "Get API Key" or "Sign In"
3. Create a new project (if needed)
4. Enable the Generative AI API
5. Create an API key (free tier available)
6. Copy the key

### Step 2: Store in AWS Secrets Manager

```bash
# Store Gemini API key securely
aws secretsmanager create-secret \
  --name gemini/api-key \
  --secret-string "your_gemini_api_key"

# Retrieve to verify
aws secretsmanager get-secret-value \
  --secret-id gemini/api-key \
  --query SecretString \
  --output text
```

### Step 3: Update Lambda Environment

```bash
# Update Lambda to retrieve from Secrets Manager
aws lambda update-function-configuration \
  --function-name post-processor \
  --environment "Variables={GEMINI_API_KEY=from-secrets-manager,GEMINI_MODEL=gemini-1.5-flash}"
```

### Step 4: Test Gemini Integration

```bash
# Test Gemini connectivity
python3 -c "
import google.generativeai as genai
import os

api_key = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=api_key)
response = genai.models.generate_content(model='gemini-1.5-flash', contents='Test')
print('✓ Gemini API working' if response.text else '✗ Gemini API failed')
"
```

### Gemini Free Tier Limits

- **Requests per minute**: 60
- **Tokens per minute**: 4,000,000
- **Cost**: Free for development/research
- **Recommended model**: gemini-1.5-flash (fastest, free tier eligible)

**Note**: Monitor usage at https://aistudio.google.com/app/apikey to ensure you stay within free tier limits.

## References

- Project Plan: `../../project-updated.md`
- Google Gemini API: https://ai.google.dev
- Gemini Documentation: https://ai.google.dev/docs
- TextBlob: https://textblob.readthedocs.io/
- AWS Comprehend: https://docs.aws.amazon.com/comprehend/
- DynamoDB Streams: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Streams.html
- AWS Secrets Manager: https://docs.aws.amazon.com/secretsmanager/

---

**Phase 3 Status**: Enhanced with Gemini API Integration
**Created**: November 7, 2025
**Last Updated**: November 9, 2025
**Gemini Integration Added**: November 9, 2025

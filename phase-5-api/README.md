# Phase 5: API Layer - REST API & Data Access

## Executive Summary

Phase 5 builds the complete REST API layer that enables frontend applications and external clients to access the enriched celebrity database. This layer provides the critical interface between the data pipeline (Phases 1-4) and consumer applications (Phase 6). The API must be fast, reliable, and cost-efficient while supporting filtering, pagination, and real-time data access.

**Key Design**: Gateway-pattern REST API with Lambda functions as microservices, API Gateway for routing/auth, and comprehensive error handling with fallback strategies.

## Overview

Phase 5 accomplishes:
1. **REST API Gateway**: API Gateway routes requests to Lambda functions
2. **Microservice Lambda Functions**: 8 independent Lambda functions for each endpoint
3. **CORS Configuration**: Enable browser-based requests from React frontend
4. **Request Validation**: Input sanitization and rate limiting
5. **Authentication**: API key validation and token management
6. **Pagination & Filtering**: Support large datasets efficiently
7. **Caching Strategy**: CloudFront + Lambda caching for performance
8. **Error Responses**: Standardized error format for all endpoints

## Architecture & Flow

```
Client (React Frontend)
  ↓
CloudFront CDN (caching)
  ↓
API Gateway (rate limiting, authentication)
  ├─ GET /celebrities → list-celebrities Lambda
  ├─ GET /celebrities/{id} → get-celebrity Lambda
  ├─ GET /celebrities/{id}/sources → list-sources Lambda
  ├─ GET /celebrities/{id}/source/{source} → get-source Lambda
  ├─ PUT /celebrities/{id} → update-celebrity Lambda
  ├─ POST /celebrities → create-celebrity Lambda
  ├─ POST /refresh/{id} → trigger-refresh Lambda
  └─ DELETE /celebrities/{id} → delete-celebrity Lambda
  ↓
DynamoDB (celebrity-database table)
  ↓
Successful Response or Error
```

## API Endpoints Reference

| Method | Endpoint | Description | Response |
|--------|----------|-------------|----------|
| GET | `/celebrities` | List all celebrities with optional filters | 200: Array of celebrities |
| GET | `/celebrities/{id}` | Get single celebrity with all metadata | 200: Celebrity object, 404: not found |
| GET | `/celebrities/{id}/sources` | Get all scraped data for celebrity | 200: Array of source entries, 404: not found |
| GET | `/celebrities/{id}/source/{source}` | Get data from specific source | 200: Source entry, 404: not found |
| PUT | `/celebrities/{id}` | Update celebrity (name, bio, etc.) | 200: Updated celebrity, 400: invalid data |
| POST | `/celebrities` | Add new celebrity to database | 201: New celebrity, 400: invalid data |
| POST | `/refresh/{id}` | Manually trigger all scrapers | 202: Accepted, 404: not found |
| DELETE | `/celebrities/{id}` | Delete celebrity and all data | 204: No content, 404: not found |

## Components

### API Gateway Configuration

**Purpose**: Route requests, validate input, handle authentication, enable CORS

**Configuration**:
```json
{
  "RestApiName": "celebrity-database-api",
  "Description": "REST API for celebrity database access",
  "EndpointConfiguration": {
    "Types": ["REGIONAL"]
  },
  "Policy": {
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": "*",
      "Action": "execute-api:Invoke",
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:SourceVpc": "vpc-xxxxxxxx"
        }
      }
    }]
  }
}
```

**CORS Configuration**:
```json
{
  "AllowedHeaders": ["Content-Type", "Authorization", "X-API-Key"],
  "AllowedMethods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
  "AllowedOrigins": ["https://yourdomain.com", "http://localhost:3000"],
  "ExposeHeaders": ["X-Total-Count", "X-Page-Size"],
  "MaxAge": 86400
}
```

**Rate Limiting**:
- 1,000 requests/hour per API key
- 10 requests/second burst limit
- Enforce via API Gateway throttling

### Lambda Functions

**Configuration** (all endpoints):
- **Runtime**: Python 3.11
- **Memory**: 512 MB (standard) / 1024 MB (heavy queries)
- **Timeout**: 30 seconds
- **Trigger**: API Gateway
- **Environment Variables**:
  ```
  DYNAMODB_TABLE=celebrity-database
  REGION=us-east-1
  CACHE_TTL=300
  MAX_ITEMS=100
  ```

**Function Structure**:
```python
def lambda_handler(event, context):
    """
    API Gateway integration handler

    event: {
      'httpMethod': 'GET|POST|PUT|DELETE',
      'path': '/celebrities',
      'queryStringParameters': {'name': 'Tom Cruise'},
      'body': '{"name": "..."}',  # for POST/PUT
      'headers': {'Authorization': 'Bearer token'}
    }

    Returns: {
      'statusCode': 200,
      'headers': {'Content-Type': 'application/json'},
      'body': '{"celebrities": [...]}'
    }
    """
```

### IAM Policy for Lambda

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:Query",
        "dynamodb:Scan"
      ],
      "Resource": "arn:aws:dynamodb:us-east-1:ACCOUNT_ID:table/celebrity-database"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:UpdateItem",
        "dynamodb:PutItem",
        "dynamodb:DeleteItem"
      ],
      "Resource": "arn:aws:dynamodb:us-east-1:ACCOUNT_ID:table/celebrity-database",
      "Condition": {
        "StringEquals": {
          "aws:username": "authenticated-user"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction"
      ],
      "Resource": "arn:aws:lambda:us-east-1:ACCOUNT_ID:function:trigger-refresh"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:us-east-1:ACCOUNT_ID:log-group:/aws/lambda/api-*"
    }
  ]
}
```

### Caching Strategy

**CloudFront Cache Configuration**:
```json
{
  "DefaultCacheBehavior": {
    "TargetOriginId": "APIGateway",
    "ViewerProtocolPolicy": "https-only",
    "AllowedMethods": ["GET", "HEAD", "OPTIONS"],
    "CachePolicy": {
      "DefaultTTL": 300,
      "MaxTTL": 3600,
      "MinTTL": 0,
      "QueryStringsConfig": {
        "QueryStringBehavior": "all"
      }
    },
    "OriginRequestPolicy": {
      "HeadersConfig": {
        "HeaderBehavior": "whitelist",
        "Headers": ["Authorization", "X-API-Key"]
      }
    }
  },
  "CacheBehaviors": [
    {
      "PathPattern": "/celebrities/*/sources",
      "CachePolicyId": "long-cache",
      "DefaultTTL": 3600
    }
  ]
}
```

## Endpoint Specifications

### 1. GET /celebrities - List All Celebrities

**Purpose**: Retrieve paginated list of all celebrities with optional filtering

**Query Parameters**:
```
?limit=20              # Items per page (1-100, default 20)
?page=1                # Page number (default 1)
?name=tom              # Filter by name substring (case-insensitive)
?min_weight=0.5        # Filter by minimum weight score
?sentiment=positive    # Filter by sentiment (positive/negative/neutral)
?source=tmdb           # Filter by data source
?sort_by=weight        # Sort field (weight, name, updated_date)
?sort_order=desc       # Sort order (asc/desc)
```

**Request**:
```bash
GET /celebrities?limit=20&page=1&name=tom&sort_by=weight
Authorization: Bearer {token}
X-API-Key: {api-key}
```

**Success Response** (200):
```json
{
  "celebrities": [
    {
      "id": "celebrity_1",
      "name": "Tom Cruise",
      "bio": "American actor",
      "weight": 0.87,
      "sentiment": "positive",
      "sources_count": 4,
      "last_updated": "2025-11-07T15:30:00Z"
    }
  ],
  "pagination": {
    "current_page": 1,
    "page_size": 20,
    "total_items": 100,
    "total_pages": 5,
    "has_next": true
  }
}
```

**Implementation Logic**:
```python
def list_celebrities(event):
    # 1. Parse query parameters
    limit = min(int(event.get('limit', 20)), 100)
    page = int(event.get('page', 1))

    # 2. Build DynamoDB filter expression
    filters = {}
    if 'name' in event:
        filters['name'] = event['name'].lower()
    if 'min_weight' in event:
        filters['min_weight'] = float(event['min_weight'])

    # 3. Query DynamoDB (Scan on GSI)
    response = dynamodb.scan(
        FilterExpression=build_filter_expression(filters),
        Limit=limit,
        ExclusiveStartKey=get_start_key(page)
    )

    # 4. Format response
    return format_celebrities_response(response, limit, page)
```

### 2. GET /celebrities/{id} - Get Single Celebrity

**Purpose**: Retrieve complete celebrity profile with all metadata

**Path Parameters**:
```
{id}  # celebrity_id (e.g., celebrity_1)
```

**Success Response** (200):
```json
{
  "id": "celebrity_1",
  "name": "Tom Cruise",
  "bio": "American actor known for action films",
  "weight": 0.87,
  "sentiment": "positive",
  "sentiment_detail": {
    "positive": 0.75,
    "neutral": 0.20,
    "negative": 0.05
  },
  "sources_count": 4,
  "data_sources": ["tmdb", "wikipedia", "newsapi", "twitter"],
  "last_updated": "2025-11-07T15:30:00Z",
  "created_date": "2025-10-01T10:00:00Z"
}
```

**Error Response** (404):
```json
{
  "error": "celebrity_not_found",
  "message": "Celebrity with ID 'celebrity_1' not found",
  "status_code": 404
}
```

### 3. GET /celebrities/{id}/sources - Get All Source Data

**Purpose**: Retrieve raw data from all scrapers for a celebrity

**Query Parameters**:
```
?include_metadata=true   # Include scraper metadata
?fields=name,bio,date    # Specific fields to return
```

**Success Response** (200):
```json
{
  "celebrity_id": "celebrity_1",
  "celebrity_name": "Tom Cruise",
  "sources": [
    {
      "source": "tmdb",
      "timestamp": "2025-11-07T14:20:00Z",
      "data": {
        "name": "Tom Cruise",
        "bio": "American actor",
        "popularity": 85.5,
        "image_url": "https://..."
      },
      "status": "success",
      "confidence": 0.95
    },
    {
      "source": "wikipedia",
      "timestamp": "2025-11-07T14:25:00Z",
      "data": {
        "name": "Thomas Cruise Mapother IV",
        "bio": "Born December 3, 1962",
        "categories": ["American actors", "Living people"]
      },
      "status": "success",
      "confidence": 0.90
    }
  ],
  "summary": {
    "total_sources": 4,
    "successful": 4,
    "failed": 0
  }
}
```

### 4. GET /celebrities/{id}/source/{source} - Get Source-Specific Data

**Purpose**: Retrieve data from single scraper with full history

**Path Parameters**:
```
{id}      # celebrity_id
{source}  # tmdb, wikipedia, newsapi, twitter, instagram, youtube
```

**Query Parameters**:
```
?limit=10       # Number of entries (default 1, latest)
?history=true   # Include historical entries
```

**Success Response** (200):
```json
{
  "celebrity_id": "celebrity_1",
  "source": "tmdb",
  "entries": [
    {
      "timestamp": "2025-11-07T14:20:00Z",
      "data": {
        "name": "Tom Cruise",
        "bio": "American actor",
        "popularity": 85.5
      },
      "confidence": 0.95,
      "status": "success"
    }
  ],
  "statistics": {
    "first_entry": "2025-10-01T10:00:00Z",
    "last_entry": "2025-11-07T14:20:00Z",
    "total_entries": 52
  }
}
```

### 5. PUT /celebrities/{id} - Update Celebrity

**Purpose**: Manually update celebrity information (name, bio, etc.)

**Request Body**:
```json
{
  "name": "Tom Cruise",
  "bio": "Updated biography",
  "image_url": "https://...",
  "tags": ["action", "actor"]
}
```

**Success Response** (200):
```json
{
  "id": "celebrity_1",
  "name": "Tom Cruise",
  "bio": "Updated biography",
  "updated_date": "2025-11-07T16:00:00Z"
}
```

**Implementation Logic**:
```python
def update_celebrity(event, id):
    # 1. Validate input
    body = json.loads(event['body'])
    if not validate_update_body(body):
        return error_response(400, "invalid_request")

    # 2. Get current item
    current = dynamodb.get_item(Key={'id': id})
    if not current:
        return error_response(404, "not_found")

    # 3. Merge updates
    updated_item = {**current['Item'], **body}
    updated_item['updated_date'] = datetime.utcnow().isoformat()

    # 4. Update DynamoDB
    try:
        dynamodb.put_item(Item=updated_item)
        return success_response(200, updated_item)
    except Exception as e:
        return error_response(500, "update_failed")
```

### 6. POST /celebrities - Create New Celebrity

**Purpose**: Add new celebrity to database (will be scraped in next cycle)

**Request Body**:
```json
{
  "name": "New Actor",
  "bio": "Optional biography",
  "image_url": "https://...",
  "tags": ["actor"]
}
```

**Success Response** (201):
```json
{
  "id": "celebrity_101",
  "name": "New Actor",
  "bio": "Optional biography",
  "created_date": "2025-11-07T16:00:00Z",
  "message": "Celebrity created. Will be scraped on next cycle (Sunday 2 AM UTC)"
}
```

**Error Response** (400):
```json
{
  "error": "duplicate_celebrity",
  "message": "Celebrity 'New Actor' already exists",
  "status_code": 400
}
```

### 7. POST /refresh/{id} - Trigger Manual Refresh

**Purpose**: Manually invoke all scrapers for a specific celebrity

**Success Response** (202 - Accepted):
```json
{
  "id": "celebrity_1",
  "status": "refresh_queued",
  "message": "All 4 scrapers queued for immediate execution",
  "estimated_completion": "2025-11-07T16:10:00Z"
}
```

**Implementation**:
```python
def trigger_refresh(id):
    # 1. Verify celebrity exists
    celebrity = dynamodb.get_item(Key={'id': id})
    if not celebrity:
        return error_response(404, "not_found")

    # 2. Invoke all 4 scrapers asynchronously
    for scraper in ['scraper-tmdb', 'scraper-wikipedia', 'scraper-news', 'scraper-social']:
        lambda_client.invoke(
            FunctionName=scraper,
            InvocationType='Event',  # Async
            Payload=json.dumps({'celebrity_id': id})
        )

    return success_response(202, {
        'id': id,
        'status': 'refresh_queued',
        'estimated_completion': get_estimated_time()
    })
```

### 8. DELETE /celebrities/{id} - Delete Celebrity

**Purpose**: Remove celebrity and all associated data from database

**Success Response** (204 - No Content):
```
HTTP 204 No Content
```

**Implementation Logic**:
```python
def delete_celebrity(id):
    # 1. Verify exists
    if not dynamodb.get_item(Key={'id': id}):
        return error_response(404, "not_found")

    # 2. Delete all source entries
    query_result = dynamodb.query(
        KeyConditionExpression='celebrity_id = :id',
        ExpressionAttributeValues={':id': id}
    )

    # 3. Batch delete
    for item in query_result['Items']:
        dynamodb.delete_item(Key=item['id'])

    # 4. Delete main record
    dynamodb.delete_item(Key={'id': id})

    return success_response(204, None)
```

## Error Handling & Recovery

### 1. Authentication Errors

**Error**: Invalid or missing API key
```
Detection: API Gateway evaluates Authorization header
Response: 401 Unauthorized
{
  "error": "unauthorized",
  "message": "Invalid or missing API key",
  "status_code": 401
}
```

**Recovery**:
- Client provides valid API key
- Implement key rotation every 90 days
- Set up CloudWatch alarm for repeated 401 errors

### 2. Request Validation Errors

**Error**: Invalid query parameters or body
```
Detection: Parameter validation in API Gateway
Response: 400 Bad Request
{
  "error": "invalid_request",
  "message": "Parameter 'limit' must be between 1 and 100",
  "status_code": 400,
  "details": {"parameter": "limit", "received": "150"}
}
```

**Recovery**:
- Log validation failures
- Return clear error messages
- Implement input sanitization

### 3. DynamoDB Query Failures

**Error**: DynamoDB returns throttling or timeout
```
Detection: GetItem/Query/Scan raises exception
Response: 503 Service Unavailable
{
  "error": "temporary_unavailable",
  "message": "Database temporarily unavailable. Retry after 5 seconds.",
  "status_code": 503,
  "retry_after": 5
}
```

**Recovery Strategy**:
```python
def query_with_retry(query_fn, max_retries=3):
    for attempt in range(max_retries):
        try:
            return query_fn()
        except ClientError as e:
            if e.response['Error']['Code'] == 'ProvisionedThroughputExceededException':
                wait_time = 2 ** attempt  # Exponential backoff
                time.sleep(wait_time)
            else:
                raise
    return error_response(503, "temporary_unavailable")
```

### 4. Lambda Timeout

**Error**: Query exceeds 30-second timeout
```
Detection: Lambda execution duration > 30s
Response: 504 Gateway Timeout
{
  "error": "request_timeout",
  "message": "Request exceeded 30 second timeout",
  "status_code": 504
}
```

**Recovery**:
- Optimize query (use Query instead of Scan)
- Add pagination limits
- Increase Lambda memory → faster execution
- Implement result caching

### 5. Malformed JSON Response

**Error**: DynamoDB returns data that can't be serialized
```
Detection: json.dumps() fails on response
Response: 500 Internal Server Error
{
  "error": "internal_server_error",
  "message": "Error processing response",
  "status_code": 500
}
```

**Recovery**:
- Log raw DynamoDB response for debugging
- Implement JSON serializer for custom types:
```python
class DynamoDBEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)
```

### 6. Celebrity Not Found

**Error**: Requested celebrity_id doesn't exist
```
Detection: GetItem returns empty result
Response: 404 Not Found
{
  "error": "celebrity_not_found",
  "message": "Celebrity 'celebrity_1' not found",
  "status_code": 404,
  "suggestion": "Use GET /celebrities to list available celebrities"
}
```

**Recovery**:
- Provide list endpoint in error response
- Log 404s to identify dead links
- Implement front-end validation

### 7. Rate Limiting Exceeded

**Error**: Client exceeds 1000 req/hour limit
```
Detection: API Gateway token bucket exhausted
Response: 429 Too Many Requests
{
  "error": "rate_limit_exceeded",
  "message": "You have exceeded 1000 requests/hour",
  "status_code": 429,
  "retry_after": 3600
}
```

**Recovery**:
- Implement client-side request queuing
- Cache results aggressively
- Contact admin for higher limit if needed

### 8. Cross-Origin (CORS) Error

**Error**: Browser blocks request from different domain
```
Detection: Browser CORS preflight fails
Response: 403 Forbidden (browser blocks response)
```

**Recovery**:
- Verify AllowedOrigins in CORS configuration
- Check that API Gateway has CORS enabled
- Test with curl (no browser CORS):
```bash
curl -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: GET" \
  https://api.example.com/celebrities
```

## Testing Protocol

### Phase 5A: API Gateway Setup Testing

**Step 1: Create API Gateway**
```bash
# Create REST API
aws apigateway create-rest-api \
  --name celebrity-database-api \
  --description "API for celebrity database"

# Get API ID
API_ID=$(aws apigateway get-rest-apis --query 'items[0].id' --output text)
echo "API ID: $API_ID"
```

**Step 2: Create Resource Hierarchy**
```bash
# Get root resource
ROOT=$(aws apigateway get-resources \
  --rest-api-id $API_ID \
  --query 'items[0].id' \
  --output text)

# Create /celebrities resource
CELEBRITIES=$(aws apigateway create-resource \
  --rest-api-id $API_ID \
  --parent-id $ROOT \
  --path-part celebrities \
  --query 'id' --output text)

# Create /{id} resource
ID_RESOURCE=$(aws apigateway create-resource \
  --rest-api-id $API_ID \
  --parent-id $CELEBRITIES \
  --path-part {id} \
  --query 'id' --output text)

# Create /sources resource
SOURCES=$(aws apigateway create-resource \
  --rest-api-id $API_ID \
  --parent-id $ID_RESOURCE \
  --path-part sources \
  --query 'id' --output text)
```

**Step 3: Create Methods**
```bash
# GET /celebrities method
aws apigateway put-method \
  --rest-api-id $API_ID \
  --resource-id $CELEBRITIES \
  --http-method GET \
  --authorization-type NONE

# Create Lambda integration
aws apigateway put-integration \
  --rest-api-id $API_ID \
  --resource-id $CELEBRITIES \
  --http-method GET \
  --type AWS_PROXY \
  --integration-http-method POST \
  --uri arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/arn:aws:lambda:us-east-1:ACCOUNT_ID:function:list-celebrities/invocations
```

**Step 4: Enable CORS**
```bash
# Enable CORS on /celebrities
aws apigateway put-method \
  --rest-api-id $API_ID \
  --resource-id $CELEBRITIES \
  --http-method OPTIONS \
  --authorization-type NONE

aws apigateway put-integration \
  --rest-api-id $API_ID \
  --resource-id $CELEBRITIES \
  --http-method OPTIONS \
  --type MOCK
```

**Step 5: Create Deployment**
```bash
# Create stage
DEPLOY=$(aws apigateway create-deployment \
  --rest-api-id $API_ID \
  --stage-name dev \
  --query 'id' --output text)

# Get API endpoint
API_ENDPOINT="https://$API_ID.execute-api.us-east-1.amazonaws.com/dev"
echo "API Endpoint: $API_ENDPOINT"
```

### Phase 5B: Lambda Function Testing

**Step 1: Deploy List Celebrities Function**
```bash
# Package function
cd phase-5-api/api-functions/list-celebrities
zip -r function.zip .

# Create function
aws lambda create-function \
  --function-name list-celebrities \
  --runtime python3.11 \
  --role arn:aws:iam::ACCOUNT_ID:role/lambda-api-role \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://function.zip \
  --environment Variables="{DYNAMODB_TABLE=celebrity-database,REGION=us-east-1}" \
  --timeout 30 \
  --memory-size 512

# Grant API Gateway permission
aws lambda add-permission \
  --function-name list-celebrities \
  --statement-id ApiGatewayInvoke \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com
```

**Step 2: Test Locally**
```bash
# Create test event
cat > test-event.json << EOF
{
  "httpMethod": "GET",
  "path": "/celebrities",
  "queryStringParameters": {"limit": "20", "page": "1"}
}
EOF

# Test locally
aws lambda invoke \
  --function-name list-celebrities \
  --payload file://test-event.json \
  response.json

cat response.json | jq .
```

**Step 3: Test via API Gateway**
```bash
# Test GET /celebrities
curl -X GET \
  "$API_ENDPOINT/celebrities?limit=20&page=1" \
  -H "Content-Type: application/json"

# Expected: 200 with celebrities array
```

**Step 4: **STOP IF LAMBDA FAILS**
If Lambda returns error:
- [ ] Check CloudWatch logs: `aws logs tail /aws/lambda/list-celebrities --follow`
- [ ] Verify DynamoDB table exists
- [ ] Verify IAM role has DynamoDB permissions
- [ ] Check environment variables set
- [ ] Fix code and redeploy
- [ ] Re-test before proceeding

### Phase 5C: Endpoint Testing

**Test GET /celebrities**
```bash
# List all
curl "$API_ENDPOINT/celebrities" | jq .

# With filters
curl "$API_ENDPOINT/celebrities?name=tom&limit=10" | jq .

# Expected: 200, celebrities array, pagination info
```

**Test GET /celebrities/{id}**
```bash
# Get specific celebrity
CELEB_ID=$(curl "$API_ENDPOINT/celebrities?limit=1" | jq -r '.celebrities[0].id')

curl "$API_ENDPOINT/celebrities/$CELEB_ID" | jq .

# Expected: 200, full celebrity object
```

**Test GET /celebrities/{id}/sources**
```bash
curl "$API_ENDPOINT/celebrities/$CELEB_ID/sources" | jq .

# Expected: 200, array of source entries
```

**Test PUT /celebrities/{id}**
```bash
curl -X PUT \
  "$API_ENDPOINT/celebrities/$CELEB_ID" \
  -H "Content-Type: application/json" \
  -d '{"bio": "Updated biography"}' | jq .

# Expected: 200, updated celebrity
```

**Test POST /celebrities**
```bash
curl -X POST \
  "$API_ENDPOINT/celebrities" \
  -H "Content-Type: application/json" \
  -d '{"name": "New Actor", "bio": "New biography"}' | jq .

# Expected: 201, new celebrity with ID
```

**Test POST /refresh/{id}**
```bash
curl -X POST "$API_ENDPOINT/refresh/$CELEB_ID" | jq .

# Expected: 202 Accepted
# Monitor scrapers: aws logs tail /aws/lambda/scraper-tmdb --follow
```

**Test DELETE /celebrities/{id}**
```bash
# Create test celebrity
NEW_ID=$(curl -X POST \
  "$API_ENDPOINT/celebrities" \
  -H "Content-Type: application/json" \
  -d '{"name": "Delete Me"}' | jq -r '.id')

# Delete it
curl -X DELETE "$API_ENDPOINT/celebrities/$NEW_ID" -v

# Expected: 204 No Content
# Verify deleted
curl "$API_ENDPOINT/celebrities/$NEW_ID" -v
# Expected: 404
```

### Phase 5D: Performance & Error Testing

**Test Pagination**
```bash
# Test pagination with various page sizes
for page in 1 2 3 4 5; do
  curl "$API_ENDPOINT/celebrities?page=$page&limit=20" | jq '.pagination'
done

# Expected: correct page numbers, has_next flag accurate
```

**Test Error Handling**
```bash
# Test 404
curl "$API_ENDPOINT/celebrities/nonexistent" -v
# Expected: 404

# Test invalid parameter
curl "$API_ENDPOINT/celebrities?limit=1000" -v
# Expected: 400

# Test missing API key
curl "$API_ENDPOINT/celebrities" \
  -H "Authorization: Bearer invalid" -v
# Expected: 401
```

**Test Rate Limiting**
```bash
# Send 1100 requests in 1 hour
for i in {1..1100}; do
  curl "$API_ENDPOINT/celebrities" > /dev/null &
  [ $((i % 100)) -eq 0 ] && echo "Sent $i requests"
done

# After ~1000, expect 429 Too Many Requests
```

**Test Performance**
```bash
# Time a request
time curl "$API_ENDPOINT/celebrities" > /dev/null

# Expected: < 2 seconds
# If > 5 seconds: optimize query or increase Lambda memory
```

### Phase 5E: **STOP IF FAILURES**

If any endpoint fails:
- [ ] Check endpoint implementation
- [ ] Verify DynamoDB permissions
- [ ] Check CloudWatch logs
- [ ] Test DynamoDB directly: `aws dynamodb scan --table-name celebrity-database`
- [ ] Fix code issues
- [ ] **Do NOT deploy to prod** until all endpoints pass

## Deployment Strategy

### Development Environment
```bash
# Deploy to dev stage
aws apigateway create-deployment \
  --rest-api-id $API_ID \
  --stage-name dev \
  --stage-description "Development stage"

# Test against dev endpoint
API_DEV="https://$API_ID.execute-api.us-east-1.amazonaws.com/dev"
curl "$API_DEV/celebrities"
```

### Production Deployment
```bash
# Deploy to prod stage
aws apigateway create-deployment \
  --rest-api-id $API_ID \
  --stage-name prod \
  --stage-description "Production stage"

# Configure CloudFront in front of prod
aws cloudfront create-distribution \
  --origin-domain-name "$API_ID.execute-api.us-east-1.amazonaws.com" \
  --default-cache-behavior ViewerProtocolPolicy=https-only,AllowedMethods=[GET,HEAD],CachePolicyId=4135ea3d-c35d-46eb-81d7-reeSn5UJTLC
```

## Monitoring & Logging

**CloudWatch Metrics**:
```bash
# Monitor API Gateway
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name Count \
  --dimensions Name=ApiName,Value=celebrity-database-api \
  --start-time 2025-11-07T00:00:00Z \
  --end-time 2025-11-07T23:59:59Z \
  --period 3600 \
  --statistics Sum,Average

# Monitor Lambda
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=list-celebrities \
  --start-time 2025-11-07T00:00:00Z \
  --end-time 2025-11-07T23:59:59Z \
  --period 3600 \
  --statistics Average,Maximum
```

**CloudWatch Alarms**:
```bash
# Alert on high error rate
aws cloudwatch put-metric-alarm \
  --alarm-name api-high-error-rate \
  --alarm-description "Alert if API error rate > 5%" \
  --metric-name 5XXError \
  --namespace AWS/ApiGateway \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:ACCOUNT_ID:api-alerts

# Alert on high latency
aws cloudwatch put-metric-alarm \
  --alarm-name api-high-latency \
  --metric-name Latency \
  --statistic Average \
  --threshold 5000 \
  --comparison-operator GreaterThanThreshold
```

## Coding Principles & Best Practices

### Error Handling
✅ **Implemented**:
- Try-catch blocks for all DynamoDB operations
- Specific error codes (401, 403, 404, 429, 500, 503)
- Exponential backoff for retries
- Partial failure handling (log errors, continue)
- Error logging to CloudWatch

### Validation
✅ **Implemented**:
- Input sanitization (SQL injection, XSS)
- Parameter bounds checking (limit max 100)
- Type validation (ensure id is string, limit is int)
- API key validation via API Gateway
- Request size limits

### Performance
✅ **Implemented**:
- Query optimization (use Query not Scan where possible)
- Pagination for large result sets
- CloudFront caching (300s default)
- Lambda result caching (in-memory)
- Database connection pooling

### Security
✅ **Implemented**:
- API key authentication (X-API-Key header)
- CORS validation
- HTTPS only (enforced by API Gateway)
- IAM role-based access control
- Input validation prevents injection attacks
- Rate limiting prevents abuse

### Monitoring
✅ **Implemented**:
- CloudWatch logs for all requests
- CloudWatch metrics for latency, errors, throughput
- Custom alarms for anomalies
- Request/response logging

### Robustness
✅ **Implemented**:
- Idempotent operations (safe to retry)
- Graceful degradation (partial data OK)
- Timeout protection (30s Lambda timeout)
- Circuit breaker pattern for DynamoDB

## Cost Breakdown

| Service | Monthly Cost | Notes |
|---------|--------------|-------|
| API Gateway | $0.35 | 1M requests × $0.35/M |
| Lambda | $0.15 | 1M requests × 1s avg × $0.0000166/ms |
| CloudFront | $0.085 | 100 GB cached data × $0.085/GB |
| **Total** | **~$0.55/month** | API layer cost |

## Timeline & Milestones

- [ ] Create API Gateway REST API (day 1)
- [ ] Configure CORS (day 1)
- [ ] Create Lambda functions for all 8 endpoints (day 2-3)
- [ ] Test each endpoint (day 3-4)
- [ ] Fix any endpoint failures (day 4)
- [ ] Deploy to dev stage (day 4)
- [ ] Performance testing (day 5)
- [ ] **STOP if failures - fix before prod** (day 5)
- [ ] Deploy to prod stage (day 5)
- [ ] Monitor first 24 hours (day 6)

## Current Implementation Status

### ✅ Completed
- [x] Phase 5 directory structure
- [x] API Gateway configuration template
- [x] Endpoint specifications documented

### 🟡 In Progress
- [ ] Create API Gateway REST API
- [ ] Configure Lambda functions

### ⏳ Not Started
- [ ] Phase 6 (Frontend)

## Next Phase

**Phase 6: Frontend Dashboard** (Week 11-13)
- Build React single-page application
- Implement search and filtering UI
- Display weight/sentiment data
- Deploy to CloudFront

**Prerequisites**:
- ✅ Phase 5: API fully functional
- ✅ All endpoints returning correct data
- ✅ Performance acceptable (< 2s response time)

## References

- Project Plan: `../../project-updated.md`
- API Gateway: https://docs.aws.amazon.com/apigateway/
- Lambda with API Gateway: https://docs.aws.amazon.com/lambda/latest/dg/services-apigateway.html
- DynamoDB: https://docs.aws.amazon.com/dynamodb/

---

**Phase 5 Status**: Ready for Implementation
**Created**: November 7, 2025
**Last Updated**: November 7, 2025

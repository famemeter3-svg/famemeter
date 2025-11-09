# Local UI Tool - Architecture & Design

## Overview

The Local UI Tool is a lightweight web application designed to verify and validate your DynamoDB database schema and data entries. It provides real-time insights into data quality, completeness, and correctness.

## System Architecture

```
┌─────────────────────────────────────────────────────┐
│              Web Browser (Client)                    │
│  ┌───────────────────────────────────────────────┐  │
│  │  HTML (index.html)                            │  │
│  │  CSS Styling (style.css)                      │  │
│  │  JavaScript Logic (app.js)                    │  │
│  └───────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────┘
                       │ HTTP/JSON
                       ▼
┌─────────────────────────────────────────────────────┐
│        Flask Web Server (app.py)                     │
│  ┌───────────────────────────────────────────────┐  │
│  │  /              - Serve HTML                  │  │
│  │  /api/health    - Check connection            │  │
│  │  /api/stats     - Database statistics         │  │
│  │  /api/celebrities           - List all        │  │
│  │  /api/celebrity/<id>        - Get details     │  │
│  │  /api/schema                - Table schema    │  │
│  │  /api/validate/celebrity    - Validate one   │  │
│  │  /api/validate/all          - Validate all   │  │
│  │  /api/raw/<id>/<source>     - Raw data       │  │
│  └───────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────┘
                       │ boto3 SDK
                       ▼
┌─────────────────────────────────────────────────────┐
│          AWS DynamoDB (celebrity-database)          │
│  ┌───────────────────────────────────────────────┐  │
│  │  Table: celebrity-database                    │  │
│  │  ├─ Metadata Records (seed data)              │  │
│  │  └─ Scraper Entries (Phase 2+)                │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

## Components

### Frontend (Client-Side)

**index.html**
- Structure with 4 tabs (Overview, Celebrities, Validation, Schema)
- Modal popup for detailed celebrity view
- Tables, forms, and status displays

**style.css**
- Modern, responsive design
- Light/dark-friendly color scheme
- Mobile-responsive grid layouts
- Status indicators and badges

**app.js**
- Handles all user interactions
- Makes API calls to backend
- Renders data dynamically
- Manages tab switching and modals
- Client-side filtering and search

### Backend (Server-Side)

**app.py (Flask)**
- 8 main API endpoints
- Connection management to DynamoDB
- Data aggregation and formatting
- Validation logic
- Error handling with graceful fallbacks

**Key Endpoints:**

| Endpoint | Purpose | Returns |
|----------|---------|---------|
| `GET /` | Serve HTML | index.html |
| `GET /api/health` | Connection status | {status, table, message} |
| `GET /api/celebrities` | List all with metadata | {total, celebrities[]} |
| `GET /api/celebrity/<id>` | Details for one | {metadata, data_sources[]} |
| `GET /api/stats` | Database statistics | {total_items, sources, counts} |
| `GET /api/schema` | Table schema info | {keys, gsi, billing_mode} |
| `GET /api/validate/celebrity/<id>` | Validate one | {valid, errors[], warnings[]} |
| `GET /api/validate/all` | Validate all | {results[], summary} |
| `GET /api/raw/<id>/<source>` | Raw JSON/text data | {data, is_json} |

## Data Flow

### Loading Celebrities

```
Browser (load page)
    ↓
app.js calls GET /api/celebrities
    ↓
app.py:
  1. Query DynamoDB table
  2. Filter for metadata records (sort_key.startswith('metadata#'))
  3. Aggregate data sources
  4. Sort by celebrity_id
    ↓
Return JSON response
    ↓
app.js renders table
```

### Viewing Celebrity Details

```
Browser (click View button)
    ↓
app.js calls GET /api/celebrity/<id>
    ↓
app.py:
  1. Query DynamoDB by celebrity_id
  2. Separate metadata from scraper entries
  3. Extract first-hand fields (raw_text, source, timestamp)
  4. Format for display
    ↓
Modal displays:
  - Metadata fields (name, birth_date, etc.)
  - Data sources list
  - Raw text preview
```

### Validation Flow

```
Browser (click Validate All)
    ↓
app.js calls GET /api/validate/all
    ↓
app.py:
  1. Scan entire DynamoDB table
  2. Group items by celebrity_id
  3. For each celebrity:
    - Check for metadata record
    - Check required fields
    - Check scraper entries
    - Report errors and warnings
  4. Aggregate results
    ↓
Return summary and per-celebrity results
    ↓
app.js displays:
  - Summary stats (passed, failed, warnings)
  - List of failures (with errors)
  - List of warnings
```

## Data Validation Rules

The validator checks for:

### Metadata Records (sort_key starts with 'metadata#')
- ✓ **Required**: celebrity_id, name
- ⚠️ **Recommended**: birth_date, nationality, occupation

### Scraper Entries (other sort_keys)
- ✓ **Required**: id, raw_text, source, timestamp
- ⚠️ **Recommended**: weight (after Phase 3), sentiment (after Phase 3)

### Overall Database
- ✓ At least 1 metadata record per celebrity
- ⚠️ At least 1 scraper entry per celebrity (optional at this stage)

## Error Handling

### Connection Errors
```python
try:
    table = dynamodb.Table(table_name)
except Exception as e:
    # Show "Not Connected" in UI
    return error_response("DynamoDB not found")
```

### Query Errors
```python
try:
    response = table.query(...)
except ClientError as e:
    logger.error(f"Query failed: {e}")
    return error_response(str(e))
```

### Missing Data
```python
if not response.get('Items'):
    return error_response("Celebrity not found", 404)
```

## Performance Considerations

### Query Optimization

**Efficient**:
- Query by celebrity_id (partition key) - very fast
- Scan with filters - slower but acceptable for 100 items

**Inefficient** (not used):
- Full table scan with no filters

### Caching Strategy
- No server-side caching (data changes in real-time)
- Client caches celebrities list until refresh
- Each detail view makes fresh API call

### Response Sizes
- Single celebrity detail: ~5-50 KB (depends on raw_text size)
- All celebrities list: ~10-20 KB
- Validation results: ~5-10 KB

## Security Considerations

### AWS Credentials
- Uses IAM role/credentials from environment
- No credentials hardcoded in code
- No API keys sent over HTTP

### Input Validation
- URL parameters (celebrity_id) used in queries
- No SQL injection risk (DynamoDB query API)
- No XSS risk (data escaped in HTML)

### Data Privacy
- Raw text data is readable in UI (for debugging)
- Should only be used in local development
- Not suitable for production deployment without authentication

## Extensibility

### Adding New Endpoints

1. Add route in app.py:
```python
@app.route('/api/new-endpoint')
def new_endpoint():
    # Implementation
    return jsonify(result)
```

2. Call from app.js:
```javascript
const data = await fetchAPI('/new-endpoint');
```

3. Display in template

### Adding New Fields

If you add fields to scraper entries, they're automatically handled:
- app.py reads all fields from DynamoDB
- app.js displays them in detail view
- Validation can be updated if needed

### Custom Validation Rules

Edit `validate_celebrity()` and `validate_all()` in app.py to add checks for:
- Specific field formats
- Data completeness
- Cross-field validation

## Deployment Notes

### Local Development Only
- No authentication
- Debug mode enabled (auto-reload)
- CORS enabled (allow all origins)

### For Production Deployment

Would need:
- Authentication (API keys, OAuth)
- HTTPS only
- Rate limiting
- Input validation
- Logging and monitoring

## Testing

### Manual Testing Checklist

- [ ] Connection test: Header shows "Connected ✓"
- [ ] Statistics load: Overview tab shows numbers
- [ ] Celebrity list: Can see all 100 celebrities
- [ ] Search works: Filter by name narrows results
- [ ] Detail view: Modal shows complete celebrity info
- [ ] Validation passes: No celebrities show errors
- [ ] Schema displays: Correctly shows table structure
- [ ] Raw data: Can view scraped data JSON

### Automated Testing

Could add:
- Unit tests for API endpoints
- Integration tests with mock DynamoDB
- Frontend e2e tests with Selenium

## Development Tips

### Debugging

**Flask Debug Mode**
- Prints SQL-like query info
- Auto-reloads on code changes
- Error stack traces in browser

**Browser Console**
- View API responses: Network tab
- Check JavaScript errors: Console tab
- Monitor requests: Network tab

**CloudWatch Logs**
```bash
# View all DynamoDB operations
aws logs tail /aws/lambda/your-function --follow
```

### Adding Console Logging

In app.py:
```python
logger.info(f"Loading celebrity: {celebrity_id}")
logger.error(f"Error: {e}")
```

In app.js:
```javascript
console.log("Data loaded:", data);
console.error("Error:", error);
```

### Hot Reload

While running with debug=True:
1. Edit Python files → auto-reloads on save
2. Edit HTML/CSS/JS → refresh browser to see changes

## Next Steps for Enhancement

1. **Add Export** - Download validation results as CSV
2. **Add Charts** - Visualize source distribution
3. **Add Filters** - Filter by source, date range
4. **Add Edit UI** - Manually edit/add records
5. **Add Pagination** - Handle 1000+ celebrities
6. **Add Authentication** - Restrict access in shared environments

---

**Created**: November 9, 2025
**Purpose**: Technical documentation for developers extending the tool

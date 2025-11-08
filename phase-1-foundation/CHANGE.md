# Phase 1: Foundation - Schema Alignment with project-updated.md

**Purpose**: This file documents the required changes to ensure Phase 1 implementation aligns with the authoritative data schema defined in project-updated.md (lines 123-180).

**Last Updated**: November 9, 2025
**Status**: Ready for Implementation

---

## ✅ Current State Assessment

### What's Correct
- ✅ DynamoDB table structure (table-definition.json) - CORRECT
- ✅ Table keys: celebrity_id (partition), source_type#timestamp (sort)
- ✅ Global Secondary Indexes (name-index, source-index) - CORRECT
- ✅ DynamoDB Streams enabled with NEW_AND_OLD_IMAGES - CORRECT
- ✅ On-Demand billing mode - CORRECT
- ✅ Celebrity seed data structure - CORRECT for master records

### What Needs Clarification
- ⚠️ Phase 1 README conflates master records with scraper entries
- ⚠️ Documentation doesn't clearly distinguish master records vs scraper entries

---

## Critical Concept: Phase 1 Creates MASTER RECORDS, Not Scraper Entries

### Master Record (Phase 1 Responsibility)
Created during initial seeding (celebrities.json):
```json
{
  "celebrity_id": "celeb_001",
  "source_type#timestamp": "metadata#2025-01-01T00:00:00Z",  // Fixed timestamp
  "name": "Leonardo DiCaprio",
  "birth_date": "1974-11-11",
  "nationality": "American",
  "occupation": ["Actor", "Producer"],
  "created_at": "2025-11-07T00:00:00Z",
  "updated_at": "2025-11-07T00:00:00Z",
  "is_active": true
}
```

**Key Points**:
- Master records have FIXED `source_type#timestamp` = `metadata#2025-01-01T00:00:00Z`
- Master records do NOT have `raw_text` field (that's Phase 2)
- Master records contain only basic celebrity information
- Master records are METADATA entries, not scraper entries

### Scraper Entry (Phase 2 Responsibility)
Created by scrapers (different entries for each data source):
```json
{
  "celebrity_id": "celeb_001",
  "source_type#timestamp": "google_search#2025-11-07T17:20:00Z",  // Dynamic timestamp
  "id": "scraper_entry_001_google_2025_11_07",
  "name": "Leonardo DiCaprio",
  "raw_text": "{...COMPLETE unprocessed API response...}",  // Full response
  "source": "https://www.google.com/search",
  "timestamp": "2025-11-07T17:20:00Z",
  "weight": null,  // Computed by Phase 3
  "sentiment": null  // Computed by Phase 3
}
```

**Key Points**:
- Scraper entries have DYNAMIC `source_type#timestamp` = `{source}#{ISO8601_timestamp}`
- Scraper entries MUST have `raw_text` containing complete unprocessed response
- Scraper entries include: id, name, raw_text, source, timestamp (first-hand data)
- Scraper entries will be processed by Phase 3 (weight & sentiment computed)

---

## Data Flow Architecture

```
Phase 1: SEEDS master records
  │
  ├─ Creates: 100 master records with celebrity metadata
  ├─ Each has: celebrity_id, name, birth_date, nationality, occupation
  ├─ Each has: source_type#timestamp = "metadata#2025-01-01T00:00:00Z"
  └─ NO raw_text field (that's Phase 2's responsibility)

  ↓
DynamoDB Table Ready (celebrity-database)
  │
  ├─ Contains: 100 master records
  ├─ Each celebrity can have 1 master record + multiple scraper entries
  └─ Indexes ready for both lookup patterns

  ↓
Phase 2: CREATES scraper entries
  │
  ├─ For each celebrity: creates entries from each data source
  ├─ Stage 2.1: Creates google_search#{timestamp} entries with full search response
  ├─ Stage 2.3: Creates instagram#{timestamp} entries with full Instaloader data
  ├─ Stage 2.3: Creates threads#{timestamp} entries with full Instaloader data
  ├─ Stage 2.4: Creates youtube#{timestamp} entries with full YouTube API response
  ├─ Each scraper entry: has complete raw_text field
  └─ No post-processing yet (weight=null, sentiment=null)

  ↓
DynamoDB Streams Trigger
  └─ For each new scraper entry created

  ↓
Phase 3: POST-PROCESSES scraper entries
  │
  ├─ Reads scraper entries from DynamoDB Streams
  ├─ Extracts text content FROM raw_text field
  ├─ Computes weight (based on data completeness & source reliability)
  ├─ Computes sentiment (via NLP analysis)
  └─ Updates DynamoDB entry with weight & sentiment

  ↓
Phase 5 & 6: API & Frontend
  └─ Displays complete data: master record + all scraper entries with weight/sentiment
```

---

## Required Documentation Updates for Phase 1

### 1. Update phase-1-foundation/README.md

**Section to Update**: "Complete Data Structure" (lines 99-204)

**Change Required**:
Split the single "Scraper Entry" example into TWO clear sections:

**NEW Section A: Master Record (Phase 1 Creates This)**
```markdown
### Master Record (Seed Data - Phase 1 ONLY)

This is the initial celebrity record created during Phase 1 seeding:

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

**Characteristics**:
- Created once per celebrity during Phase 1 seeding
- Fixed source_type#timestamp = "metadata#2025-01-01T00:00:00Z"
- Contains basic celebrity metadata only
- NO raw_text field (that's Phase 2's responsibility)
```

**NEW Section B: Scraper Entry (Phase 2 Creates This)**
```markdown
### Scraper Entry (Created by Phase 2 Scrapers)

This is created by each scraper in Phase 2 for each data source:

```json
{
  "celebrity_id": "celeb_001",
  "source_type#timestamp": "google_search#2025-11-07T17:20:00Z",
  "id": "scraper_entry_001_google_2025_11_07",
  "name": "Leonardo DiCaprio",
  "raw_text": "{...COMPLETE unprocessed API response...}",
  "source": "https://www.google.com/search",
  "timestamp": "2025-11-07T17:20:00Z",
  "weight": null,
  "sentiment": null
}
```

**Characteristics**:
- Created by Phase 2 scrapers for each data source
- Dynamic source_type#timestamp = "{source}#{ISO8601_timestamp}"
- Contains COMPLETE unprocessed API/HTML response in raw_text
- First-hand data fields: id, name, raw_text, source, timestamp
- weight and sentiment are null (computed by Phase 3)
```

### 2. Update phase-1-foundation/README.md Data Flow Pattern (lines 138-185)

**Current Text**: Shows single flow for scraper entries

**Required Change**: Replace with diagram showing master records specifically:

```markdown
### Data Flow Pattern - Phase 1 (Master Records)

```
┌─────────────────────────────────────────┐
│  Phase 1: MASTER RECORDS ONLY           │
├─────────────────────────────────────────┤
│ ✓ celebrity_id                          │
│ ✓ name                                  │
│ ✓ birth_date                            │
│ ✓ nationality                           │
│ ✓ occupation                            │
│ ✓ is_active                             │
│ ✗ NO raw_text (Phase 2 adds this)       │
│ ✗ NO weight (Phase 3 computes this)     │
│ ✗ NO sentiment (Phase 3 computes this)  │
└─────────────────────────────────────────┘
         │
         │ Phase 1: Seed-database.py writes to DynamoDB
         │ Each master record: source_type#timestamp = "metadata#2025-01-01T00:00:00Z"
         │
         ▼
┌─────────────────────────────────────────┐
│ Stored in DynamoDB (Waiting for Phase 2)│
├─────────────────────────────────────────┤
│ ✓ Master records ready for lookup       │
│ ✓ Indexes ready for queries             │
│ ✓ Streams ready to receive Phase 2 data │
└─────────────────────────────────────────┘
         │
         │ Phase 2: Scrapers create entries with raw_text
         │ Each scraper entry: source_type#timestamp = "{source}#{timestamp}"
         │
         ▼
┌─────────────────────────────────────────┐
│   Phase 2: SCRAPER ENTRIES ADDED        │
├─────────────────────────────────────────┤
│ ✓ All master fields: id, name, source   │
│ ✓ raw_text (complete API response)      │
│ ✓ timestamp (when scraped)              │
│ ✗ weight = null (waiting for Phase 3)   │
│ ✗ sentiment = null (waiting for Phase 3)│
└─────────────────────────────────────────┘
```

### 3. Update CLAUDE.md (phase-1-foundation/)

**Add Section**: "Master Records vs Scraper Entries"

```markdown
## Understanding Master Records vs Scraper Entries

**Master Record (Phase 1)**:
- One per celebrity, created during seed phase
- Contains: celebrity_id, name, birth_date, nationality, occupation
- source_type#timestamp = "metadata#2025-01-01T00:00:00Z" (fixed)
- Created by: seed-database.py
- NO raw_text field

**Scraper Entry (Phase 2)**:
- Multiple per celebrity (one per data source)
- Contains: id, name, raw_text, source, timestamp
- source_type#timestamp = "{source}#{ISO8601_timestamp}" (dynamic)
- Created by: Phase 2 scrapers (Google, Instagram, Threads, YouTube)
- Contains COMPLETE unprocessed API response in raw_text

**In DynamoDB Query**:
```sql
-- Get master record for celeb_001
SELECT * FROM celebrity-database
WHERE celebrity_id = 'celeb_001'
AND source_type#timestamp = 'metadata#2025-01-01T00:00:00Z'

-- Get all scraper entries for celeb_001
SELECT * FROM celebrity-database
WHERE celebrity_id = 'celeb_001'
AND source_type#timestamp > 'metadata'  -- Gets all non-metadata entries
```
```

---

## Schema Validation Checklist for Phase 1

Before declaring Phase 1 complete, verify:

### Master Record Validation
- [ ] Master records have exactly one per celebrity (celebrity_id)
- [ ] source_type#timestamp = "metadata#2025-01-01T00:00:00Z" (all fixed)
- [ ] All required fields present: celebrity_id, name, birth_date, nationality, occupation
- [ ] No raw_text field in master records (correct - Phase 2's job)
- [ ] All timestamps valid ISO 8601 format
- [ ] is_active = true for all celebrities

### DynamoDB Table Validation
- [ ] Table named: celebrity-database
- [ ] Partition Key: celebrity_id
- [ ] Sort Key: source_type#timestamp
- [ ] Billing Mode: PAY_PER_REQUEST
- [ ] Streams enabled: NEW_AND_OLD_IMAGES view
- [ ] GSI name-index exists and functional
- [ ] GSI source-index exists (will be used by Phase 2)
- [ ] PITR enabled for recovery

### Readiness for Phase 2
- [ ] All 100 master records inserted successfully
- [ ] No duplicate celebrity_ids
- [ ] Table ready to accept scraper entries from Phase 2
- [ ] Streams ready to trigger Phase 3 post-processor

---

## Alignment with project-updated.md

This Phase 1 implementation aligns with project-updated.md specification:

| Item | Reference | Status |
|------|-----------|--------|
| Master record fields | Lines 190-201 | ✅ Correct |
| Scraper entry fields | Lines 131-144 | ✅ Phase 2 will add |
| raw_text definition | Lines 153 | ✅ Phase 2 responsibility |
| DynamoDB schema | Lines 184-214 | ✅ Implemented correctly |
| Keys design | Lines 205-213 | ✅ Correct |
| data_type#timestamp format | Lines 74-80 | ✅ Master uses "metadata#..." |

---

## Summary for AI Agents

**What Phase 1 Does**:
1. Creates DynamoDB table with optimized schema
2. Seeds 100 master celebrity records with basic metadata
3. Does NOT create raw_text fields (Phase 2's job)
4. Prepares table for Phase 2 scraper data

**What Phase 1 Does NOT Do**:
1. Store unprocessed API responses (raw_text) - that's Phase 2
2. Compute weight or sentiment - that's Phase 3
3. Scrape data from any source - that's Phase 2

**Documentation Updates Required**:
1. Clarify master record vs scraper entry in README.md
2. Show Phase 1 specific data flow (no raw_text, no computed fields)
3. Update CLAUDE.md with clear explanation
4. Keep DynamoDB schema and table definition as-is (already correct)

**Next Step**: Phase 2 will create scraper entries with raw_text for each source.

---

**For Questions**: Refer to project-updated.md lines 123-180 for authoritative schema definition.

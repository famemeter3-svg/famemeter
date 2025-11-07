# GitHub Issues to Create

These issues should be created manually on GitHub to track problems and solutions for the FameMeter project.

---

## Issue #1: Database Integration Documentation

**Title**: docs: Database integration guide needed for Phase 2 scrapers

**Labels**: `documentation`, `phase-2`, `database`

**Body**:

```markdown
## Problem

Phase 2 scrapers need comprehensive documentation about how to interact with the DynamoDB database set up in Phase 1. Currently, there's no clear guidance on:
- How to read celebrity metadata
- How to write scraper entries
- What the data structures look like
- Required IAM permissions
- Query patterns for each stage

## Solution

Created DATABASE_INTEGRATION.md with:
- Phase 1 DynamoDB table reference
- Celebrity metadata schema
- Scraper entry structure
- 6 DynamoDB operation patterns
- Query patterns specific to each stage
- Lambda IAM permissions
- Data flow diagram (Phase 1→2→3)
- Monitoring & verification commands
- Troubleshooting section
- Cost analysis for Phase 2

## Deliverables

✅ DATABASE_INTEGRATION.md (623 lines)
- Covers all query patterns
- Includes Boto3 code examples
- Documents Phase 3 integration
- References Phase 1 schema

## Status

RESOLVED ✅
```

---

## Issue #2: Stage 2.1 Implementation Guide

**Title**: docs: Stage 2.1 - Google Search API scraper implementation guide

**Labels**: `documentation`, `phase-2`, `stage-2.1`, `google-api`

**Body**:

```markdown
## Problem

Need comprehensive guide for implementing Stage 2.1 (Google Search API scraper):
- API setup and configuration
- Raw text cleaning methodology
- DynamoDB integration
- Error handling strategies
- Testing protocols

## Solution

Created stage-2.1-google-search/README.md with:
- Google Custom Search API setup (15 min setup)
- Lambda configuration (512MB, 5 min timeout)
- Raw text cleaning implementation
- Complete lambda_function.py code
- 5 error handling scenarios
- 6-phase testing protocol
- CLI verification commands
- Cost analysis ($0-2/month)

## Testing Protocol

Phase 2.1A: API Key Setup
Phase 2.1B: Single Celebrity Test
Phase 2.1C: Data Verification
Phase 2.1D: Batch Testing (5 celebrities)
Phase 2.1E: Full Deployment (100 celebrities)
Phase 2.1F: Integration

## Status

RESOLVED ✅
```

---

## Issue #3: Stage 2.2 Anti-Detection Implementation

**Title**: docs: Stage 2.2 - Instagram scraper with proxy rotation and anti-detection

**Labels**: `documentation`, `phase-2`, `stage-2.2`, `instagram`, `anti-detection`

**Body**:

```markdown
## Problem

Instagram actively blocks scrapers. Stage 2.2 needs:
- Proxy rotation to avoid IP-based detection
- Account credential management
- User-Agent rotation for diversity
- Request timing to mimic human behavior
- Graceful handling of detection blocks (403/429)
- Scaling with multiple accounts

## Solution

Created stage-2.2-instagram/README.md with:
- ProxyManager class for rotation
- InstagramScraper class implementation
- Credential management (AWS Secrets Manager)
- 4 anti-detection strategies:
  1. Proxy rotation with 2-5s delays
  2. User-Agent rotation (4+ variations)
  3. Request timing (1-4 seconds)
  4. Circuit breaker on detection
- Error handling (403/429/timeout/lock)
- Scaling with multiple accounts
- 5-phase testing protocol
- Cost analysis ($10-20/month)

## Anti-Detection Features

✅ Proxy rotation with randomized delays
✅ User-Agent rotation from browser list
✅ Request timing for human-like behavior
✅ Session management with varied headers
✅ Exponential backoff (5-15s) on blocks
✅ Account rotation to distribute load

## Status

RESOLVED ✅
```

---

## Issue #4: Stage 2.3 Threads Integration

**Title**: docs: Stage 2.3 - Threads scraper leveraging Instagram infrastructure

**Labels**: `documentation`, `phase-2`, `stage-2.3`, `threads`, `meta-platforms`

**Body**:

```markdown
## Problem

Stage 2.3 (Threads) scraper needs:
- Similar methodology to Instagram (same Meta account)
- Account credential reuse
- Proxy infrastructure reuse
- Threads-specific endpoint handling
- Simpler anti-bot measures (newer platform)

## Solution

Created stage-2.3-threads/README.md with:
- ThreadsScraper class (same pattern as Instagram)
- Reuse of instagram-accounts secret
- Reuse of proxy-list infrastructure
- Threads URL pattern: threads.net/@{handle}
- Error handling (429/403/timeout)
- 4-phase testing protocol
- Cost analysis ($5-10/month, shared with Instagram)

## Key Differences from Instagram

- Simpler API structure (newer platform)
- Fewer anti-bot measures (but growing)
- More lenient rate limits initially
- Same Meta account infrastructure
- Can run concurrently without conflict

## Status

RESOLVED ✅
```

---

## Issue #5: Stage 2.4 YouTube API Integration

**Title**: docs: Stage 2.4 - YouTube Data API v3 integration

**Labels**: `documentation`, `phase-2`, `stage-2.4`, `youtube`, `official-api`

**Body**:

```markdown
## Problem

Stage 2.4 needs YouTube integration:
- Official YouTube Data API v3 setup
- Channel search and statistics
- Quota management (10k units/day)
- No detection risk (official API)
- Cost optimization

## Solution

Created stage-2.4-youtube/README.md with:
- YouTube Data API v3 setup
- Lambda configuration (512MB, 5 min timeout)
- search_youtube_channel() function
- fetch_channel_data() function
- Complete lambda_function.py code
- Quota management (10k units/day)
- Error handling (not found/quota/invalid key)
- 6-phase testing protocol
- Cost analysis (Free)

## Quota Analysis

- 100 celebrities × 2 API calls = 200 units/week
- Free tier: 10,000 units/day
- Remaining capacity: 9,800 units for retries
- Resets daily at 00:00 PT

## Status

RESOLVED ✅
```

---

## Issue #6: Phase 2 Modular Documentation Structure

**Title**: docs: Phase 2 restructured with modular four-stage documentation

**Labels**: `documentation`, `phase-2`, `architecture`, `structure`

**Body**:

```markdown
## Problem

Phase 2 documentation was monolithic. Needed:
- Clear separation of each stage
- Standalone stage folders
- Consistent documentation structure
- Easy navigation and reference

## Solution

Restructured Phase 2 with:
- 4 stage-specific folders (2.1-2.4)
- Individual README per stage
- Master OVERVIEW.md (architecture)
- Quick reference INDEX.md
- DATABASE_INTEGRATION.md (critical reference)
- Shared resources folder

## Documentation Structure

phase-2-scrapers/
├── INDEX.md (Quick navigation)
├── OVERVIEW.md (Master overview)
├── README.md (Full specification)
├── DATABASE_INTEGRATION.md (Database guide)
├── stage-2.1-google-search/README.md
├── stage-2.2-instagram/README.md
├── stage-2.3-threads/README.md
├── stage-2.4-youtube/README.md
└── shared-resources/

## Statistics

- 8 main documentation files
- 3,200+ lines of documentation
- 72 KB total
- 60+ code examples
- 15+ reference tables

## Status

RESOLVED ✅
```

---

## Issue #7: Phase 1 Foundation Complete

**Title**: docs: Phase 1 Foundation - DynamoDB setup and celebrity seeding

**Labels**: `documentation`, `phase-1`, `database`, `completed`

**Body**:

```markdown
## Completed Tasks

✅ DynamoDB Table Creation
- Table name: celebrity-database
- Region: us-east-1
- Billing: On-Demand
- Partition key: celebrity_id
- Sort key: source_type#timestamp
- Global Secondary Indexes: 2
- Streams: Enabled for Phase 2/3

✅ Celebrity Seeding
- 100 Taiwan entertainment celebrities
- Traditional Chinese names
- Metadata fields: name, birth_date, nationality, occupation
- Zero data quality issues
- All records validated

✅ Testing & Validation
- 12-point infrastructure test (12/12 passed)
- 100-point data validation (100/100 passed)
- Zero duplicates, zero errors
- Comprehensive validation report

## Deliverables

✅ phase-1-foundation/README.md (comprehensive setup guide)
✅ phase-1-foundation/PHASE_1_SUCCESS.md (success documentation)
✅ phase-1-foundation/dynamodb-setup/ (setup scripts)
✅ phase-1-foundation/celebrity-seed/ (seed scripts)
✅ Validation and test reports

## Status

RESOLVED ✅
```

---

## Issue #8: Testing Protocols and Quality Gates

**Title**: feature: Implement 20 testing phases with STOP gates for error handling

**Labels**: `testing`, `phase-2`, `quality-assurance`

**Body**:

```markdown
## Problem

Each stage needs clear testing progression:
- Setup phase (check prerequisites)
- Single test phase (verify functionality)
- Batch test phase (verify scaling)
- Full deployment phase (production ready)
- Integration phase (Phase 1→2→3 flow)
- STOP gates at each phase if errors

## Solution

Implemented testing protocols for all stages:

### Testing Phases

**Phase XA: Setup**
- Verify prerequisites (API keys, accounts, proxies)
- Check IAM permissions
- Validate environment variables

**Phase XB: Single Test**
- Test with one celebrity
- Verify API calls work
- Check error handling

**Phase XC: Data Verification**
- Query DynamoDB for result
- Verify fields are present
- Check raw_text is populated

**Phase XD: Batch Test**
- Run with 5 celebrities
- Monitor for failures
- Check success rate (threshold varies)

**Phase XE: Full Deployment**
- Deploy to all 100 celebrities
- Verify count in DynamoDB
- Monitor costs

**Phase XF: Integration** (if applicable)
- Verify DynamoDB Streams working
- Check Phase 3 post-processor triggering

### STOP Gates

🛑 STOP IF ANY ERRORS:
- CloudWatch logs show errors
- Success rate below threshold
- Permissions not working
- Data validation fails

Fix errors and re-run before proceeding.

## Coverage

- Stage 2.1: 6 phases (API→Deploy)
- Stage 2.2: 5 phases (Setup→Deploy)
- Stage 2.3: 4 phases (Setup→Deploy)
- Stage 2.4: 6 phases (Setup→Deploy)
- Total: 21 testing gates

## Status

RESOLVED ✅
```

---

## Creating Issues on GitHub

To create these issues on GitHub, use:

```bash
gh issue create --title "TITLE" --body "BODY" --label "LABELS"
```

Or visit: https://github.com/famemeter3-svg/famemeter/issues/new

---

## Summary

| Issue # | Title | Status | Link |
|---------|-------|--------|------|
| 1 | Database Integration Guide | ✅ Resolved | [DATABASE_INTEGRATION.md](../phase-2-scrapers/DATABASE_INTEGRATION.md) |
| 2 | Stage 2.1 Implementation Guide | ✅ Resolved | [stage-2.1/README.md](../phase-2-scrapers/stage-2.1-google-search/README.md) |
| 3 | Stage 2.2 Anti-Detection | ✅ Resolved | [stage-2.2/README.md](../phase-2-scrapers/stage-2.2-instagram/README.md) |
| 4 | Stage 2.3 Threads Integration | ✅ Resolved | [stage-2.3/README.md](../phase-2-scrapers/stage-2.3-threads/README.md) |
| 5 | Stage 2.4 YouTube API | ✅ Resolved | [stage-2.4/README.md](../phase-2-scrapers/stage-2.4-youtube/README.md) |
| 6 | Phase 2 Modular Structure | ✅ Resolved | [phase-2-scrapers/](../phase-2-scrapers/) |
| 7 | Phase 1 Foundation Complete | ✅ Resolved | [phase-1-foundation/](../phase-1-foundation/) |
| 8 | Testing Protocols | ✅ Resolved | All stage READMEs |

---

**Generated**: November 7, 2025
**Total Issues**: 8
**All Resolved**: ✅

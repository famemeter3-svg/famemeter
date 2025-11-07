# Phase 2 Scrapers - Quick Navigation Index

## 🚀 Start Here

**New to Phase 2?** Start with [OVERVIEW.md](./OVERVIEW.md) for a complete guide.

## 📁 Stage Folders

Each stage has its own folder with complete documentation and implementation guides:

### Stage 2.1: Google Search API
- **Folder**: `stage-2.1-google-search/`
- **Documentation**: [README.md](./stage-2.1-google-search/README.md)
- **Difficulty**: ⭐ Easy (Official API)
- **Cost**: $0-2/month
- **Status**: ✅ Production Ready
- **Use When**: You need general search results and basic information

### Stage 2.2: Instagram
- **Folder**: `stage-2.2-instagram/`
- **Documentation**: [README.md](./stage-2.2-instagram/README.md)
- **Difficulty**: ⭐⭐⭐ Hard (Anti-Detection Required)
- **Cost**: $10-20/month (proxy service)
- **Status**: ⚠️ Anti-Bot Measures
- **Use When**: You need real-time follower counts and engagement metrics

### Stage 2.3: Threads
- **Folder**: `stage-2.3-threads/`
- **Documentation**: [README.md](./stage-2.3-threads/README.md)
- **Difficulty**: ⭐⭐ Medium (Simpler than Instagram)
- **Cost**: $5-10/month (shared proxy)
- **Status**: ⚠️ Anti-Bot Measures (Growing)
- **Use When**: You need Threads profile data for celebrities

### Stage 2.4: YouTube
- **Folder**: `stage-2.4-youtube/`
- **Documentation**: [README.md](./stage-2.4-youtube/README.md)
- **Difficulty**: ⭐ Easy (Official API)
- **Cost**: Free
- **Status**: ✅ Production Ready
- **Use When**: You need channel stats and video information

## 📊 Comparison Table

| Feature | 2.1 Google | 2.2 Insta | 2.3 Threads | 2.4 YouTube |
|---------|-----------|----------|------------|------------|
| Method | Official API | Account+Proxy | Account+Proxy | Official API |
| Data Type | Web Search | Social Profile | Social Profile | Video Stats |
| Auth Required | API Key | Username/Pass | Username/Pass | API Key |
| Rate Limits | 100/day | Dynamic | Dynamic | 10k quota/day |
| Detection Risk | None | High | Medium | None |
| Cost/Month | $0-2 | $10-20 | $5-10 | Free |
| Setup Time | 15 min | 2 hours | 2 hours | 15 min |
| Implementation | 200 lines | 300+ lines | 250 lines | 200 lines |

## 🎯 Recommended Order

1. **Start with Stage 2.1** (Google Search)
   - No accounts or proxies needed
   - Simplest testing
   - Builds confidence
   - Verifies DynamoDB setup

2. **Then Stage 2.4** (YouTube)
   - Official API only
   - Most data sources have YouTube
   - No anti-detection needed
   - Free tier sufficient

3. **Then Stage 2.2** (Instagram)
   - Requires proxy service setup
   - Most challenging
   - Most valuable data
   - Build on earlier experience

4. **Finally Stage 2.3** (Threads)
   - Uses same infrastructure as Instagram
   - Simpler implementation
   - Growing platform
   - Complete the pipeline

## 📋 Implementation Checklist

### Before You Start
- [ ] Read OVERVIEW.md
- [ ] Understand first-hand data concept
- [ ] Review project-updated.md
- [ ] Set up AWS credentials

### Stage 2.1 (Google Search)
- [ ] Create Google Cloud project
- [ ] Enable Custom Search API
- [ ] Obtain API key
- [ ] Read stage-2.1-google-search/README.md
- [ ] Follow Phase 2.1A-F testing protocol
- [ ] Verify data in DynamoDB

### Stage 2.2 (Instagram)
- [ ] Create dedicated Instagram accounts (2-3)
- [ ] Set up proxy service (BrightData, Oxylabs, etc.)
- [ ] Store credentials in AWS Secrets Manager
- [ ] Store proxies in AWS Secrets Manager
- [ ] Read stage-2.2-instagram/README.md
- [ ] Follow Phase 2.2A-E testing protocol
- [ ] Monitor for detection blocks

### Stage 2.3 (Threads)
- [ ] Verify Instagram accounts work
- [ ] Verify proxies are working
- [ ] Read stage-2.3-threads/README.md
- [ ] Follow Phase 2.3A-D testing protocol

### Stage 2.4 (YouTube)
- [ ] Create Google Cloud project (or reuse)
- [ ] Enable YouTube Data API v3
- [ ] Obtain API key
- [ ] Read stage-2.4-youtube/README.md
- [ ] Follow Phase 2.4A-F testing protocol
- [ ] Monitor quota usage

## 📚 Documentation Overview

### DATABASE_INTEGRATION.md (Critical Reference)
- Phase 1 DynamoDB table structure
- Celebrity metadata schema
- Scraper entry write requirements
- Query patterns for each stage
- Lambda IAM permissions
- DynamoDB operations (read, write, query, update)
- Cost implications
- Troubleshooting & monitoring

### OVERVIEW.md (Master Guide)
- Architecture overview
- Complete directory structure
- Implementation timeline
- Key principles & best practices
- Cost summary
- Integration testing
- Monitoring setup

### Individual Stage READMEs
Each stage README includes:
- Purpose & data source
- Lambda configuration
- Data collection flow
- Complete implementation code
- Error handling strategies
- Testing protocol (Phase XA through XE)
- Dependencies & costs
- Timeline & milestones

## 🔧 Setup Prerequisites

### For All Stages
- AWS Account with:
  - DynamoDB access
  - Lambda access
  - Secrets Manager access
  - CloudWatch logs access
- Python 3.11+
- AWS CLI configured

### For Stage 2.1 (Google Search)
- Google Cloud project
- Custom Search API enabled
- API key obtained

### For Stage 2.2 & 2.3 (Instagram & Threads)
- 2-3 dedicated Instagram accounts
- Proxy service subscription
  - Option 1: BrightData ($10-20/month)
  - Option 2: Oxylabs ($10-20/month)
  - Option 3: ScraperAPI ($5-10/month)
  - Option 4: Self-hosted proxy servers

### For Stage 2.4 (YouTube)
- Google Cloud project
- YouTube Data API v3 enabled
- API key obtained

## 🚨 Important Notes

### First-Hand Data is Critical
All stages must capture the **complete raw response** in the `raw_text` field:
- No parsing or extraction
- Complete, unmodified response
- Store as JSON string
- Will be processed in Phase 3

### Testing Protocol is Non-Negotiable
Every stage requires 5-phase testing:
- Phase A: Setup
- Phase B: Single celebrity
- Phase C: Data verification
- Phase D: Batch testing (5)
- Phase E: Full deployment (100)

**STOP and fix any errors before proceeding to next phase**

### Low-Key Operations Required
For Stages 2.2 & 2.3:
- Implement proxy rotation
- Use random delays (1-4 seconds)
- Rotate User-Agents
- Monitor for detection blocks
- Keep accounts in good standing

## 📞 Troubleshooting Quick Links

**Stage 2.1 Issues?**
→ See Error Handling in [stage-2.1-google-search/README.md](./stage-2.1-google-search/README.md)

**Stage 2.2 Detection?**
→ See Anti-Detection Strategies in [stage-2.2-instagram/README.md](./stage-2.2-instagram/README.md)

**Stage 2.3 Problems?**
→ See Error Handling in [stage-2.3-threads/README.md](./stage-2.3-threads/README.md)

**Stage 2.4 Quota Issues?**
→ See Quota Management in [stage-2.4-youtube/README.md](./stage-2.4-youtube/README.md)

## 📈 Progress Tracking

| Stage | Status | Started | Completed | Notes |
|-------|--------|---------|-----------|-------|
| 2.1 Google | ⏳ Ready | --- | --- | Start here |
| 2.2 Instagram | ⏳ Ready | --- | --- | High priority |
| 2.3 Threads | ⏳ Ready | --- | --- | After 2.2 |
| 2.4 YouTube | ⏳ Ready | --- | --- | Early wins |

## 💡 Pro Tips

1. **Deploy in order**: 2.1 → 2.4 → 2.2 → 2.3
2. **Proxy setup early**: Before starting Stage 2.2
3. **Monitor logs religiously**: Especially for 2.2 & 2.3
4. **Test locally first**: Before deploying to Lambda
5. **Keep raw_text intact**: No parsing, complete responses only
6. **Document your journey**: Note any issues for Phase 3

## 📖 More Information

- **Full Architecture**: See [OVERVIEW.md](./OVERVIEW.md)
- **Project Plan**: See `../project-updated.md`
- **Phase 1 (Foundation)**: See `../phase-1-foundation/README.md`
- **Phase 3 (Post-Processing)**: See `../phase-3-post-processing/README.md`

---

**Last Updated**: November 7, 2025
**Version**: 1.0
**Status**: Ready for Implementation

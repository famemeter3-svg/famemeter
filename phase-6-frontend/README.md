# Phase 6: Frontend Dashboard - React User Interface

## Executive Summary

Phase 6 builds the complete React-based user interface for the celebrity database system. This single-page application (SPA) provides an intuitive dashboard for browsing, searching, and managing celebrity data from all 4 sources. The frontend is deployed to CloudFront for global content delivery with automatic caching and minimal latency.

**Key Design**: React 18 SPA with component-based architecture, server-side rendering considerations, responsive design for mobile/tablet/desktop, real-time data refresh, and comprehensive error handling.

## Overview

Phase 6 accomplishes:
1. **Responsive Dashboard**: Works on desktop, tablet, and mobile
2. **Celebrity Browser**: Paginated list with search/filter capabilities
3. **Detail View**: Complete celebrity profile with source tabs
4. **CRUD Operations**: Create, read, update, and delete celebrities
5. **Weight & Sentiment Display**: Visual representation of data quality
6. **Real-time Refresh**: Manually trigger scraper runs
7. **Error Recovery**: Graceful error handling with user feedback
8. **Performance**: Optimized with lazy loading and caching

## Architecture & Flow

```
Browser
  ↓
CloudFront CDN (cached static assets)
  ↓
React SPA (routing, state, components)
  ├─ HomePage: Celebrity grid
  ├─ DetailPage: Celebrity profile
  ├─ EditPage: Update celebrity
  └─ AddPage: Create new celebrity
  ↓
API Service Layer (Axios)
  ↓
API Gateway / Lambda (Phase 5)
  ↓
DynamoDB (celebrity-database)
```

## Tech Stack

**Frontend Libraries**:
- **React 18**: UI framework with hooks
- **React Router v6**: Client-side routing
- **Axios**: HTTP client for API calls
- **React Query v4**: Server state management & caching
- **Tailwind CSS v3**: Utility-first CSS
- **Heroicons**: Consistent icon library
- **Recharts**: Data visualization for weight/sentiment

**Dev Tools**:
- **Vite**: Fast build tool (replaces Create React App)
- **ESLint**: Code linting
- **Prettier**: Code formatting
- **Vitest**: Unit testing
- **Playwright**: End-to-end testing

**Deployment**:
- **AWS S3**: Static asset storage
- **AWS CloudFront**: CDN & caching
- **AWS CloudWatch**: Performance monitoring

## Directory Structure

```
phase-6-frontend/
├── react-app/
│   ├── src/
│   │   ├── components/
│   │   │   ├── CelebrityCard.jsx         (Card component for grid)
│   │   │   ├── CelebrityList.jsx         (List container)
│   │   │   ├── CelebrityDetail.jsx       (Full profile)
│   │   │   ├── DataSourceTabs.jsx        (Source tabs)
│   │   │   ├── SourceEntry.jsx           (Individual source data)
│   │   │   ├── EditForm.jsx              (Edit modal form)
│   │   │   ├── AddForm.jsx               (Create new celebrity)
│   │   │   ├── SearchFilter.jsx          (Search & filter UI)
│   │   │   ├── Header.jsx                (Navigation header)
│   │   │   ├── Footer.jsx                (Footer)
│   │   │   └── ErrorBoundary.jsx         (Error handling)
│   │   ├── pages/
│   │   │   ├── HomePage.jsx              (List page)
│   │   │   ├── DetailPage.jsx            (Detail page)
│   │   │   ├── EditPage.jsx              (Edit modal)
│   │   │   ├── AddPage.jsx               (Create page)
│   │   │   ├── NotFoundPage.jsx          (404 page)
│   │   │   └── ErrorPage.jsx             (Error page)
│   │   ├── hooks/
│   │   │   ├── useCelebrities.js         (Query hook)
│   │   │   ├── useCelebrity.js           (Detail query)
│   │   │   ├── useUpdateCelebrity.js     (Mutation hook)
│   │   │   └── useDebounce.js            (Search debounce)
│   │   ├── services/
│   │   │   ├── api.js                    (API client)
│   │   │   ├── apiConfig.js              (Configuration)
│   │   │   └── errorHandler.js           (Error utilities)
│   │   ├── utils/
│   │   │   ├── formatting.js             (Date/number formatting)
│   │   │   ├── validation.js             (Form validation)
│   │   │   └── constants.js              (App constants)
│   │   ├── styles/
│   │   │   └── tailwind.css              (Global styles)
│   │   ├── App.jsx                       (Root component)
│   │   ├── index.jsx                     (Entry point)
│   │   └── queryClient.js                (React Query setup)
│   ├── public/
│   │   ├── index.html                    (HTML template)
│   │   ├── favicon.ico
│   │   └── manifest.json
│   ├── tests/
│   │   ├── components/                   (Component tests)
│   │   ├── pages/                        (Page tests)
│   │   └── e2e/                          (End-to-end tests)
│   ├── package.json
│   ├── vite.config.js
│   └── tailwind.config.js
└── deployment/
    ├── s3-config.json                    (S3 bucket config)
    ├── cloudfront-config.json            (CloudFront distribution)
    └── deploy.sh                         (Deployment script)
```

## Component Specifications

### 1. CelebrityCard Component

**Purpose**: Display single celebrity in grid format

**Props**:
```javascript
{
  id: string,              // celebrity_1
  name: string,            // Tom Cruise
  bio: string,             // Short biography
  weight: number,          // 0.87
  sentiment: string,       // positive/negative/neutral
  sources_count: number,   // 4
  image_url?: string,      // Optional image
  onClick: function        // Navigate to detail
}
```

**Features**:
- Weight score visualization (0.0-1.0, color-coded)
- Sentiment badge (green/yellow/red)
- Hover effects
- Click to navigate to detail page
- Responsive sizing

**Example**:
```jsx
<CelebrityCard
  id="celebrity_1"
  name="Tom Cruise"
  bio="American actor"
  weight={0.87}
  sentiment="positive"
  sources_count={4}
  onClick={() => navigate(`/celebrity/${id}`)}
/>
```

### 2. SearchFilter Component

**Purpose**: Search and filter celebrities

**Features**:
- Text search (debounced, 300ms)
- Filter by minimum weight (0.0-1.0 slider)
- Filter by sentiment (dropdown)
- Filter by data source (multi-select)
- Sort options (name, weight, date)
- Clear filters button

**Implementation**:
```jsx
const [searchTerm, setSearchTerm] = useState('');
const [minWeight, setMinWeight] = useState(0);
const [sentiment, setSentiment] = useState('all');

const debouncedSearch = useDebounce(searchTerm, 300);

const query = useCelebrities({
  name: debouncedSearch,
  min_weight: minWeight,
  sentiment: sentiment !== 'all' ? sentiment : undefined,
  sort_by: 'weight'
});
```

### 3. CelebrityList Component

**Purpose**: Display paginated list of celebrities

**Features**:
- Infinite scroll or pagination
- Load more button
- Empty state handling
- Loading spinner
- Error state with retry
- Responsive grid (1-4 columns based on screen)

**Grid Configuration**:
```javascript
// Mobile: 1 column (< 640px)
// Tablet: 2 columns (640px - 1024px)
// Desktop: 3 columns (1024px - 1536px)
// Wide: 4 columns (> 1536px)
className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4"
```

### 4. CelebrityDetail Component

**Purpose**: Display complete celebrity profile

**Layout**:
```
Header with:
  - Celebrity name
  - Bio
  - Weight score (visual bar)
  - Overall sentiment
  - Last updated time
  - Action buttons (Edit, Delete, Refresh)

Data Tabs:
  - TMDb tab: movies, popularity, images
  - Wikipedia tab: biography, categories, links
  - News tab: recent articles, headlines
  - Social tab: followers, engagement, posts

Metadata:
  - Total sources: 4
  - Data freshness
  - Confidence scores per source
```

### 5. DataSourceTabs Component

**Purpose**: Display data from different sources in tabs

**Features**:
- Tab navigation (TMDb, Wikipedia, News, Social)
- Source confidence score (per tab)
- Last update timestamp (per source)
- Data-specific rendering (movies for TMDb, articles for News)
- Expandable sections

**Tab Structure**:
```jsx
const sources = [
  { id: 'tmdb', label: 'TMDb', icon: 'film' },
  { id: 'wikipedia', label: 'Wikipedia', icon: 'book' },
  { id: 'newsapi', label: 'News', icon: 'newspaper' },
  { id: 'twitter', label: 'Social', icon: 'share2' }
];
```

### 6. EditForm Component

**Purpose**: Modal form for updating celebrity

**Fields**:
- name: text input, required
- bio: textarea, optional
- image_url: URL input, optional
- tags: multi-select, optional

**Validation**:
```javascript
{
  name: { required: 'Name is required', minLength: 2, maxLength: 100 },
  bio: { maxLength: 500 },
  image_url: { pattern: '^https?://' }
}
```

**Features**:
- Form validation with error messages
- Submit button disabled until valid
- Loading state during submission
- Success notification
- Error handling with user feedback
- Cancel button to close

### 7. AddForm Component

**Purpose**: Modal form for creating new celebrity

**Fields**:
- name: required, unique
- bio: optional
- image_url: optional

**Post-creation**:
- Redirect to detail page
- Show success toast
- Celebrity scheduled for scraping on next cycle

## API Integration

### API Service (api.js)

```javascript
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://api.example.com';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': import.meta.env.VITE_API_KEY
  }
});

// Request interceptor
apiClient.interceptors.request.use(
  config => {
    console.log(`[API] ${config.method.toUpperCase()} ${config.url}`);
    return config;
  },
  error => Promise.reject(error)
);

// Response interceptor
apiClient.interceptors.response.use(
  response => response.data,
  error => {
    console.error('[API Error]', error.response?.status, error.message);
    return Promise.reject(error);
  }
);

export const fetchCelebrities = (params) =>
  apiClient.get('/celebrities', { params });

export const fetchCelebrity = (id) =>
  apiClient.get(`/celebrities/${id}`);

export const updateCelebrity = (id, data) =>
  apiClient.put(`/celebrities/${id}`, data);

export const createCelebrity = (data) =>
  apiClient.post('/celebrities', data);

export const deleteCelebrity = (id) =>
  apiClient.delete(`/celebrities/${id}`);

export const triggerRefresh = (id) =>
  apiClient.post(`/refresh/${id}`);
```

### React Query Hooks

**useCelebrities Hook**:
```javascript
import { useQuery } from '@tanstack/react-query';
import { fetchCelebrities } from '../services/api';

export const useCelebrities = (filters = {}) => {
  return useQuery({
    queryKey: ['celebrities', filters],
    queryFn: () => fetchCelebrities(filters),
    staleTime: 5 * 60 * 1000,  // 5 minutes
    cacheTime: 10 * 60 * 1000, // 10 minutes
    keepPreviousData: true,
    retry: 2,
    onError: (error) => {
      console.error('Failed to fetch celebrities:', error);
    }
  });
};
```

**useUpdateCelebrity Hook**:
```javascript
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { updateCelebrity } from '../services/api';

export const useUpdateCelebrity = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }) => updateCelebrity(id, data),
    onSuccess: (data, variables) => {
      // Invalidate and refetch
      queryClient.invalidateQueries(['celebrities']);
      queryClient.setQueryData(['celebrity', variables.id], data);
    },
    onError: (error) => {
      console.error('Update failed:', error);
    }
  });
};
```

## Error Handling & Recovery

### 1. Network Errors

**Error**: Cannot connect to API
```
Detection: Axios returns error with no response
Response: Error message: "Unable to connect to server"
```

**Recovery**:
```jsx
{error && (
  <div className="error-banner">
    <p>Unable to connect to server. Please check your connection.</p>
    <button onClick={() => refetch()}>Retry</button>
  </div>
)}
```

### 2. API Request Failures

**Error**: API returns 5xx error
```
Detection: response.status >= 500
Response: "Server error. Please try again later."
```

**Recovery**:
- Automatically retry with exponential backoff (via React Query)
- Show retry count to user
- Implement circuit breaker for repeated failures

### 3. 404 Not Found

**Error**: Requested celebrity doesn't exist
```
Detection: response.status === 404
Response: Custom NotFoundPage
```

**Recovery**:
- Redirect to home page
- Show "Celebrity not found" message
- Suggest searching for similar names

### 4. Validation Errors

**Error**: User submits invalid form data
```
Detection: Form validation before submission
Response: Error message under each field
```

**Recovery**:
```javascript
const errors = validate(formData);
// { name: 'Name is required' }
// Display error under name field
```

### 5. Timeout Error

**Error**: Request takes > 30 seconds
```
Detection: Axios timeout reached
Response: "Request timed out. Please try again."
```

**Recovery**:
- Cancel request
- Show timeout message
- Offer retry button
- Increase timeout if user confirms

### 6. CORS Error

**Error**: Browser blocks cross-origin request
```
Detection: Browser console shows CORS error
Response: No response received
```

**Recovery**:
- Verify API endpoint is correct in .env
- Check CloudFront distribution headers
- Implement proxy if needed

### 7. State Synchronization Errors

**Error**: Frontend and backend data out of sync
```
Detection: User sees stale data after update
Response: Manual refresh required
```

**Recovery**:
- Implement optimistic updates
- Fallback to refetch on failure
- Add timestamp validation
- Conflict resolution strategy

### 8. Form Submission Failures

**Error**: Update/Create fails after validation passes
```
Detection: API returns error after form submitted
Response: Modal stays open with error message
```

**Recovery**:
- Show specific error from API
- Keep form data intact
- Offer retry or cancel

## Testing Protocol

### Phase 6A: Component Setup Testing

**Step 1: Initialize React Project**
```bash
cd phase-6-frontend/react-app

# Create project with Vite
npm create vite@latest . -- --template react

# Install dependencies
npm install
npm install react-router-dom axios @tanstack/react-query tailwindcss postcss autoprefixer

# Setup Tailwind
npx tailwindcss init -p
```

**Step 2: Configure API Endpoint**
```bash
# Create .env.local
cat > .env.local << EOF
VITE_API_URL=https://api.example.com
VITE_API_KEY=your-api-key
EOF
```

**Step 3: Test Local Development**
```bash
# Start dev server
npm run dev

# Browser: http://localhost:5173
# Expected: Vite welcome page loads
```

### Phase 6B: Component Testing

**Test 1: CelebrityCard Component**
```bash
# Unit test
npm run test -- CelebrityCard.test.jsx

# Expected:
# ✓ Renders card with name
# ✓ Shows weight score
# ✓ Displays sentiment badge
# ✓ Click navigates to detail
```

**Test 2: SearchFilter Component**
```bash
# Test search functionality
# Type in search box
# Expected: Search is debounced (wait 300ms)

# Test weight filter
# Adjust slider to 0.7
# Expected: Only celebrities with weight >= 0.7 shown

# Test sentiment filter
# Select "positive"
# Expected: Only positive sentiment shown

# Test clear filters
# Click "Clear All"
# Expected: All filters reset, full list shown
```

**Test 3: CelebrityList Component**
```bash
# Test list rendering
# Expected: Grid of cards displayed

# Test pagination
# Click "Load More" or navigate to page 2
# Expected: More celebrities loaded

# Test empty state
# Search for non-existent name
# Expected: "No celebrities found" message with search suggestion

# Test loading state
# Expected: Loading skeleton while fetching
```

### Phase 6C: Integration Testing

**Test 1: Full Page Workflow**
```bash
# 1. Navigate to HomePage
#    Expected: List of celebrities displayed

# 2. Search for "Tom"
#    Expected: List filtered to Tom celebrities

# 3. Click on celebrity card
#    Expected: Navigate to DetailPage

# 4. Click "Edit" button
#    Expected: EditForm modal opens

# 5. Change biography
#    Expected: Form field updates

# 6. Click "Save"
#    Expected: API call made, modal closes, list updated

# 7. Click "Delete" (on new test celebrity)
#    Expected: Confirmation dialog, then deletion, then back to list
```

**Test 2: Error Handling**
```bash
# 1. Disconnect network (use DevTools)
#    Expected: Error message displayed

# 2. Click "Retry"
#    Expected: Automatic retry when network reconnects

# 3. Create invalid form data
#    Expected: Validation error shown

# 4. Try to access non-existent celebrity ID (edit URL)
#    Expected: 404 page shown
```

**Test 3: Data Display**
```bash
# 1. View celebrity detail page
#    Expected: All data displayed correctly

# 2. Check DataSourceTabs
#    Expected: Data from each source shown correctly

# 3. Verify weight score bar
#    Expected: Length proportional to weight (0.0-1.0)

# 4. Check sentiment colors
#    Expected: Green=positive, Yellow=neutral, Red=negative

# 5. Verify last updated time
#    Expected: Recent timestamps displayed in human-readable format
```

### Phase 6D: Browser & Responsive Testing

**Desktop (1920x1080)**
```
Expected:
- Grid: 4 columns
- All content visible without scrolling (per page)
- Buttons easily clickable
```

**Tablet (768x1024)**
```
Expected:
- Grid: 2 columns
- Touch-friendly buttons (min 44px)
- Navigation works on touch
```

**Mobile (375x667)**
```
Expected:
- Grid: 1 column
- Hamburger menu (if navigation exists)
- All text readable
- Forms scrollable
- Buttons easily tappable (min 44px height)
```

**Test Commands**:
```bash
# Chrome DevTools
# Ctrl+Shift+M to toggle device toolbar
# Test iPhone 12, iPad, and desktop sizes

# Or use responsive testing tool
npm install -D @testing-library/react @testing-library/jest-dom
npm run test -- --coverage
```

### Phase 6E: Performance Testing

**Test 1: Page Load Time**
```bash
# Lighthouse audit
# Open DevTools > Lighthouse
# Run audit for Performance
# Expected: Score > 85

# Expected metrics:
# - First Contentful Paint (FCP): < 1.5s
# - Largest Contentful Paint (LCP): < 2.5s
# - Cumulative Layout Shift (CLS): < 0.1
```

**Test 2: Bundle Size**
```bash
npm run build

# Expected output:
# dist/index.html                  0.5 kB │ gzip:  0.3 kB
# dist/assets/main.js            150.0 kB │ gzip: 45.0 kB
# dist/assets/style.css           50.0 kB │ gzip: 10.0 kB
# Total: ~200 kB gzip

# If > 300 kB: analyze and optimize
npm install -D rollup-plugin-visualizer
```

**Test 3: API Response Time**
```bash
# Monitor network tab in DevTools
# GET /celebrities
# Expected: < 1.5 seconds for 100 celebrities
# GET /celebrities/{id}
# Expected: < 0.5 seconds
# GET /celebrities/{id}/sources
# Expected: < 1.0 second
```

### Phase 6F: **STOP IF FAILURES**

If any test fails:
- [ ] Check console for JavaScript errors
- [ ] Verify API endpoint in .env.local
- [ ] Check network requests in DevTools
- [ ] Verify API response format matches component expectations
- [ ] Review console errors for specific failures
- [ ] Fix code issues
- [ ] Re-test before proceeding

## Deployment Strategy

### Build for Production

```bash
# Build optimized bundle
npm run build

# Output: dist/ directory
ls -la dist/
# Expected: index.html, assets/main.*.js, assets/style.*.css
```

### Deploy to S3

```bash
# Create S3 bucket
aws s3 mb s3://celebrity-database-frontend

# Enable static website hosting
aws s3 website s3://celebrity-database-frontend \
  --index-document index.html \
  --error-document index.html

# Set bucket policy for public read
aws s3api put-bucket-policy \
  --bucket celebrity-database-frontend \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [{
      "Sid": "PublicRead",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::celebrity-database-frontend/*"
    }]
  }'

# Deploy build
aws s3 sync dist/ s3://celebrity-database-frontend

# Verify
curl https://s3-website-us-east-1.amazonaws.com/celebrity-database-frontend
```

### Configure CloudFront

```bash
# Create CloudFront distribution
aws cloudfront create-distribution --distribution-config file://cloudfront-config.json

# Expected response: Distribution ID
# Wait 5-10 minutes for distribution to be active

# Get CloudFront URL
aws cloudfront list-distributions \
  --query 'DistributionList.Items[0].DomainName' \
  --output text

# Expected: d123abc.cloudfront.net
```

### Setup Custom Domain (Optional)

```bash
# Create Route53 hosted zone (if not exists)
aws route53 create-hosted-zone \
  --name yourdomain.com \
  --caller-reference unique-id

# Create alias record to CloudFront
aws route53 change-resource-record-sets \
  --hosted-zone-id ZXXXXX \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "yourdomain.com",
        "Type": "A",
        "AliasTarget": {
          "HostedZoneId": "Z2FDTNDATAQYW2",
          "DNSName": "d123abc.cloudfront.net",
          "EvaluateTargetHealth": false
        }
      }
    }]
  }'
```

## Monitoring & Logging

**CloudWatch Metrics**:
```bash
# Monitor CloudFront
aws cloudwatch get-metric-statistics \
  --namespace AWS/CloudFront \
  --metric-name Requests \
  --start-time 2025-11-07T00:00:00Z \
  --end-time 2025-11-07T23:59:59Z \
  --period 3600 \
  --statistics Sum

# Monitor S3
aws cloudwatch get-metric-statistics \
  --namespace AWS/S3 \
  --metric-name NumberOfObjects \
  --dimensions Name=BucketName,Value=celebrity-database-frontend
```

**Browser Monitoring** (via Google Analytics):
```javascript
// Add to index.jsx
import ReactGA from 'react-ga4';

ReactGA.initialize('G-XXXXXXXXXXXXX');

const sendPageview = () => {
  ReactGA.send({ hitType: 'pageview', page: window.location.pathname });
};

// Track on route change
```

## Coding Principles & Best Practices

### Component Design
✅ **Implemented**:
- Functional components with hooks
- Clear prop types (PropTypes or TypeScript)
- Single responsibility principle
- Reusable, composable components
- Proper error boundaries

### State Management
✅ **Implemented**:
- React Query for server state
- useState for UI state only
- Avoid prop drilling with Context API
- Optimistic updates for better UX
- Cache invalidation on mutations

### Performance
✅ **Implemented**:
- Lazy loading of routes
- Memoization (React.memo, useMemo, useCallback)
- Code splitting per route
- Image optimization
- Virtual scrolling for large lists
- Debounced search (300ms)

### Error Handling
✅ **Implemented**:
- Error boundaries for components
- Try-catch in async functions
- User-friendly error messages
- Automatic retry with exponential backoff
- Network error recovery

### Accessibility
✅ **Implemented**:
- Semantic HTML (button, form, input)
- ARIA labels for icons
- Keyboard navigation (Tab, Enter)
- Focus management
- Color contrast (WCAG AA standard)
- Alt text for images

### Security
✅ **Implemented**:
- XSS prevention (React's built-in escaping)
- CSRF protection (API key in headers)
- Content Security Policy headers
- HTTPS only (enforced by CloudFront)
- Input validation before submission

## Cost Breakdown

| Service | Monthly Cost | Notes |
|---------|--------------|-------|
| S3 | $0.50 | ~1 GB storage |
| CloudFront | $0.50 | ~10 GB transferred |
| CloudWatch | $0.10 | Logs and metrics |
| Route53 | $0.50 | Hosted zone + queries |
| **Total** | **~$1.60/month** | Frontend hosting |

## Timeline & Milestones

- [ ] Initialize React project with Vite (day 1)
- [ ] Create all components (day 2-3)
- [ ] Implement API integration (day 3)
- [ ] Add routing and navigation (day 3)
- [ ] Test all pages and components (day 4)
- [ ] Fix any component failures (day 4)
- [ ] Responsive design adjustments (day 5)
- [ ] Build production bundle (day 5)
- [ ] Deploy to S3 + CloudFront (day 5)
- [ ] **STOP if deployment fails** (day 5)
- [ ] Final testing via CloudFront URL (day 6)
- [ ] Monitor performance metrics (day 6-7)

## Current Implementation Status

### ✅ Completed
- [x] Phase 6 directory structure
- [x] Component specifications documented
- [x] API integration patterns documented

### 🟡 In Progress
- [ ] Create React components
- [ ] Implement routing

### ⏳ Not Started
- [ ] Phase 7 (Testing)
- [ ] Phase 8 (Monitoring)

## Next Phase

**Phase 7: Testing & Optimization** (Week 14-15)
- End-to-end testing of entire system
- Performance optimization
- Cost analysis and optimization
- Security audit

**Prerequisites**:
- ✅ Phase 6: Frontend deployed and accessible
- ✅ All pages loading correctly
- ✅ API integration working
- ✅ No console errors

## References

- Project Plan: `../../project-updated.md`
- React: https://react.dev/
- React Router: https://reactrouter.com/
- React Query: https://tanstack.com/query/
- Tailwind CSS: https://tailwindcss.com/
- AWS S3: https://docs.aws.amazon.com/s3/
- AWS CloudFront: https://docs.aws.amazon.com/cloudfront/

---

**Phase 6 Status**: Ready for Implementation
**Created**: November 7, 2025
**Last Updated**: November 7, 2025

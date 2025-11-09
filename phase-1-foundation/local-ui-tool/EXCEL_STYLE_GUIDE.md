# Excel-Style UI - User Guide

## What Changed

The Local UI Tool has been redesigned to mimic **Microsoft Excel** spreadsheet interface, making it familiar and intuitive for users accustomed to spreadsheet applications.

## Key Features

### 1. **Ribbon Interface** (Top Bar)
- Clean title bar showing "Celebrity Database"
- Connection status indicator (green/red dot)
- Excel-like header layout

### 2. **Sheet Tabs** (Like Excel Worksheets)
Instead of traditional tabs, the interface now uses spreadsheet-style sheets:
- 📊 **Dashboard** - Overview with KPI cards
- 📋 **Data** - Main spreadsheet grid
- ✓ **Validation** - Data validation results
- ⚙️ **Schema** - Table configuration

### 3. **Dashboard Sheet** (KPI Cards)
Displays key metrics in Excel-style cards:
```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Total        │  │ Celebrities  │  │ Metadata     │  │ Scraper      │
│ Records      │  │              │  │ Records      │  │ Data         │
│   325        │  │     100      │  │     100      │  │     225      │
└──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘

Data Sources Summary Table:
┌────────────────┬────────┬──────────┐
│ Source         │ Count  │ Percent  │
├────────────────┼────────┼──────────┤
│ google_search  │  100   │  44.4%   │
│ instagram      │   75   │  33.3%   │
│ youtube        │   50   │  22.2%   │
└────────────────┴────────┴──────────┘
```

### 4. **Data Sheet** (Spreadsheet Grid)
Full spreadsheet-like table with:
- **Header bar** with toolbar buttons
- **Search box** (🔍 Search by name, ID...)
- **Control buttons**:
  - ⚙️ Filter
  - ↕️ Sort
  - ↻ Refresh
  - ⬇ Export (to CSV)
- **Data grid** with alternating row colors
- **Pagination** at bottom (like Excel navigation)

**Column Layout:**
```
┌────┬──────────────┬───────────────┬────────────┬──────────┬────────┐
│ ID │ Name         │ Nationality   │ Birth Date │ Sources  │ Action │
├────┼──────────────┼───────────────┼────────────┼──────────┼────────┤
│ 001│ Taylor Swift │ United States │ 1989-12-13 │ 3 Sources│ View   │
├────┼──────────────┼───────────────┼────────────┼──────────┼────────┤
│ 002│ Ariana Grande│ United States │ 1993-06-26 │ 2 Sources│ View   │
└────┴──────────────┴───────────────┴────────────┴──────────┴────────┘
```

### 5. **Validation Sheet**
Validation results in grid format:
```
┌────┬──────────────┬────────┬──────────┬────────┬─────────┐
│ ID │ Name         │ Status │ Entries  │ Issues │ Details │
├────┼──────────────┼────────┼──────────┼────────┼─────────┤
│ 001│ Taylor Swift │  ✓ PASS│    3     │   0    │ All good│
├────┼──────────────┼────────┼──────────┼────────┼─────────┤
│ 002│ John Doe     │ ✗ FAIL │    1     │   2    │ Issues  │
└────┴──────────────┴────────┴──────────┴────────┴─────────┘
```

### 6. **Schema Sheet**
Table configuration in organized grid cells

---

## Color Scheme (Excel-Inspired)

### Header Colors
- **Primary Blue**: `#0066cc` - Active selections, important data
- **Header Background**: `#4472c4` - Column headers (like Excel)
- **Header Text**: White

### Status Colors
- **Green**: `#00b050` - Success, PASS
- **Red**: `#c00000` - Error, FAIL
- **Orange**: `#ff8c00` - Warning, Caution
- **Gray**: `#595959` - Neutral text

### UI Colors
- **Light Gray**: `#f2f2f2` - Alternating rows, backgrounds
- **Border Gray**: `#d9d9d9` - Cell borders
- **Hover Blue**: `#d9e1f2` - Row hover effect

---

## Excel-Like Features

### 1. **Alternating Row Colors**
Even rows have light gray background for readability (like Excel)

### 2. **Sticky Header**
Column headers stay visible when scrolling down (like Excel)

### 3. **Status Badges**
Color-coded status indicators:
- ✓ **PASS** - Green badge
- ✗ **FAIL** - Red badge
- ⚠️ **WARNING** - Orange badge

### 4. **Keyboard-Friendly**
- Tab navigation between fields
- Click cells to view details
- Search box with real-time filtering

### 5. **Data Export**
Click "⬇ Export" button to download as CSV file:
- Formatted with proper headers
- Quoted fields with special characters
- Timestamped filename: `celebrities_YYYY-MM-DD.csv`

### 6. **Pagination**
- Shows "Page 1 of 5" (for future expansion)
- Navigation buttons (< Next)
- Record count display

---

## Toolbar Buttons

### Main Controls

| Button | Icon | Function |
|--------|------|----------|
| Refresh | ↻ | Reload data from DynamoDB |
| Export | ⬇ | Download data as CSV |
| Filter | ⚙️ | Open filter options |
| Sort | ↕️ | Sort by column |
| Validate | ✓ | Run validation check |

---

## User Workflows

### Workflow 1: Browse Data
1. Open browser → URL appears with Excel-like interface
2. Dashboard shows KPI cards (like Excel summary)
3. Click "📋 Data" sheet tab
4. View celebrities in grid (like Excel spreadsheet)
5. Search for name using search box
6. Click "View" to see details

### Workflow 2: Export Data
1. Go to "📋 Data" sheet
2. Click "⬇ Export" button
3. File downloads as `celebrities_2025-11-09.csv`
4. Open in Excel or Google Sheets

### Workflow 3: Validate Database
1. Click "✓ Validation" sheet tab
2. Click "✓ Validate All Data" button
3. Grid shows validation results
4. Red rows = FAIL, Green rows = PASS
5. Click details to see specific issues

### Workflow 4: Monitor Status
1. Click "📊 Dashboard" sheet
2. KPI cards show current statistics
3. Data Sources table shows breakdown
4. Database Status section shows connection

---

## Color-Coded Status Indicators

### Validation Status
```
✓ PASS   - Green background    → All data checks passed
✗ FAIL   - Red background      → Data integrity issues
⚠️ WARN  - Orange background   → Optional field missing
```

### Connection Status
```
🟢 Connected     → DynamoDB connection active
🔴 Disconnected  → Check AWS credentials
```

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+F / Cmd+F | Focus search box |
| Tab | Navigate between controls |
| Enter | Execute search |
| Escape | Close modal/detail view |

---

## Print-Friendly Design

The interface is optimized for printing:
- Toolbar buttons hidden in print view
- Grid displays with full borders
- Colors preserved for status indicators
- Fit to page width

**To Print:**
1. Right-click → Print
2. Or press Ctrl+P / Cmd+P
3. Select "Save as PDF" or printer

---

## Mobile Responsiveness

The Excel-style interface adapts to mobile:
- Stacked controls on small screens
- Scrollable grid (horizontal + vertical)
- Touch-friendly buttons (24px minimum)
- KPI cards display as 2-column grid on mobile

**Tested On:**
- Desktop (1920x1080 and larger)
- Tablet (768px width)
- Mobile (375px width)

---

## File Format: CSV Export

When you export data, you get a standard CSV file:

```csv
ID,Name,Nationality,Birth Date,Data Sources,Active
celeb_001,Taylor Swift,United States,12/13/1989,google_search; instagram; youtube,Yes
celeb_002,Ariana Grande,United States,6/26/1993,google_search; instagram,Yes
celeb_003,Leonardo DiCaprio,American,11/11/1974,google_search,Yes
```

**Features:**
- Proper escaping for special characters
- Date formatting: M/D/YYYY
- Multiple sources separated by "; "
- Yes/No for boolean fields
- UTF-8 encoding (supports international names)

---

## Comparison: Old vs New

| Feature | Old UI | New (Excel-Style) |
|---------|--------|-------------------|
| Layout | Card-based | Spreadsheet-based |
| Tabs | Top navigation | Sheet tabs (like Excel) |
| Data View | Responsive cards | Grid table |
| Headers | Color backgrounds | Excel blue headers |
| Alternating Rows | None | Yes (light gray) |
| Export | Via API | One-click CSV download |
| Status | Text badges | Color-coded badges |
| Dashboard | Grid cards | KPI cards + table |
| Sticky Header | No | Yes |
| Mobile View | Full width | Scrollable grid |

---

## Browser Compatibility

| Browser | Support | Notes |
|---------|---------|-------|
| Chrome 90+ | ✓ Full | Recommended |
| Firefox 88+ | ✓ Full | Full support |
| Safari 14+ | ✓ Full | All features work |
| Edge 90+ | ✓ Full | Chromium-based |
| IE 11 | ✗ No | Not supported |

---

## Performance Tips

1. **Large Datasets**: Use search to filter before export
2. **Slow Connection**: Wait for grid to fully load before export
3. **CSV Opening**: Opens automatically in Excel on Windows/Mac
4. **Mobile**: Use desktop for large exports (performance)

---

## Troubleshooting

### Grid Not Showing Data
- Check Dashboard for connection status
- Click Refresh button (↻)
- Check AWS credentials

### Export Button Disabled
- Ensure data is loaded first
- Go to Data sheet
- Verify celebrities list is populated

### Search Not Working
- Click in search box
- Type slowly (real-time filtering)
- Try exact ID like "celeb_001"

### Status Badge Colors Not Showing
- Check browser zoom level (should be 100%)
- Try clearing browser cache
- Use modern browser (Chrome/Firefox/Safari)

---

## What's New

✨ **New Features in Excel-Style UI:**
- ✅ KPI Dashboard with key metrics
- ✅ CSV Export functionality
- ✅ Spreadsheet-style grid with alternating rows
- ✅ Sticky header (stays visible when scrolling)
- ✅ Excel-like color scheme
- ✅ Pagination controls
- ✅ Ribbon interface (top toolbar)
- ✅ Sheet tabs navigation
- ✅ Status color indicators
- ✅ Print-friendly design

---

## Getting Started

1. **Run the tool**: `./run.sh`
2. **Open browser**: `http://localhost:5000`
3. **You'll see**: Excel-like interface with sheet tabs
4. **Start with**: Dashboard (📊) to see overview
5. **Then click**: Data (📋) to view spreadsheet grid
6. **Export**: Click ⬇ button to download as CSV

---

**Created**: November 9, 2025
**UI Style**: Excel-Inspired Spreadsheet
**Status**: Ready to Use

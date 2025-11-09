/**
 * DynamoDB Data Viewer - Frontend JavaScript
 * Handles UI interactions, API calls, and data display
 */

const API_BASE = '/api';
let allCelebrities = [];

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    checkConnection();
    loadStats();
    loadCelebrities();
    loadSchema();
});

// ============ Event Listeners ============

function setupEventListeners() {
    // Sheet tab navigation (Excel-style)
    document.querySelectorAll('.sheet-tab').forEach(btn => {
        btn.addEventListener('click', (e) => {
            switchTab(e.target.dataset.tab);
        });
    });

    // Search input
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            filterCelebrities(e.target.value);
        });
    }

    // Validate all button
    const validateBtn = document.getElementById('validateAllBtn');
    if (validateBtn) {
        validateBtn.addEventListener('click', validateAll);
    }

    // Refresh button
    const refreshBtn = document.getElementById('refreshBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', loadCelebrities);
    }

    // Export button
    const exportBtn = document.getElementById('exportBtn');
    if (exportBtn) {
        exportBtn.addEventListener('click', exportToCSV);
    }

    // Modal close
    document.addEventListener('click', (e) => {
        const modal = document.getElementById('detailModal');
        if (e.target === modal) {
            modal.classList.remove('show');
        }
    });

    const closeBtn = document.querySelector('.modal-close');
    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            document.getElementById('detailModal').classList.remove('show');
        });
    }
}

// ============ Tab Management (Sheet Tabs) ============

function switchTab(tabName) {
    // Hide all sheets
    document.querySelectorAll('.sheet-content').forEach(tab => {
        tab.classList.remove('active');
    });

    // Deactivate all sheet tabs
    document.querySelectorAll('.sheet-tab').forEach(btn => {
        btn.classList.remove('active');
    });

    // Show selected sheet
    const activeSheet = document.getElementById(tabName);
    if (activeSheet) {
        activeSheet.classList.add('active');
    }

    // Activate clicked tab
    event.target.classList.add('active');

    // Load data for specific tabs
    if (tabName === 'overview') {
        loadStats();
    }
    if (tabName === 'celebrities' && allCelebrities.length === 0) {
        loadCelebrities();
    }
}

// ============ API Calls ============

async function fetchAPI(endpoint) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return await response.json();
    } catch (error) {
        console.error(`Error fetching ${endpoint}:`, error);
        showError(`Failed to load data: ${error.message}`);
        return null;
    }
}

// ============ Connection Status ============

async function checkConnection() {
    const data = await fetchAPI('/health');
    const statusElement = document.getElementById('connectionStatus');
    const detailsElement = document.getElementById('connectionDetails');

    if (data && data.status === 'healthy') {
        statusElement.innerHTML = `
            <span class="status-indicator connected"></span>
            <span class="status-text">Connected to DynamoDB ✓</span>
        `;

        detailsElement.innerHTML = `
            <div class="detail-grid">
                <div class="detail-item">
                    <label>Table Name</label>
                    <div class="value">${data.table}</div>
                </div>
                <div class="detail-item">
                    <label>Status</label>
                    <div class="value"><span class="badge success">${data.table_status}</span></div>
                </div>
            </div>
        `;
    } else {
        statusElement.innerHTML = `
            <span class="status-indicator disconnected"></span>
            <span class="status-text">Not Connected ✗</span>
        `;

        detailsElement.innerHTML = `
            <div style="color: #dc2626; padding: 1rem; background: #fee2e2; border-radius: 6px;">
                <strong>Connection Failed</strong><br>
                Make sure DynamoDB is running and table exists.
            </div>
        `;
    }
}

// ============ Statistics ============

async function loadStats() {
    const data = await fetchAPI('/stats');

    if (!data) {
        document.getElementById('kpiTotal').textContent = '—';
        document.getElementById('kpiCelebrities').textContent = '—';
        document.getElementById('kpiMetadata').textContent = '—';
        document.getElementById('kpiScrapers').textContent = '—';
        return;
    }

    // Update KPI cards (Excel-style dashboard)
    document.getElementById('kpiTotal').textContent = data.total_items;
    document.getElementById('kpiCelebrities').textContent = data.celebrities_with_data;
    document.getElementById('kpiMetadata').textContent = data.metadata_records;
    document.getElementById('kpiScrapers').textContent = data.scraper_records;

    // Update sources table
    const sourcesBody = document.getElementById('sourcesBody');
    if (sourcesBody && Object.keys(data.sources).length > 0) {
        let html = '';
        const totalScrapers = data.scraper_records;

        for (const [source, count] of Object.entries(data.sources)) {
            const percentage = totalScrapers > 0 ? ((count / totalScrapers) * 100).toFixed(1) : 0;
            html += `
                <tr>
                    <td>${source}</td>
                    <td style="text-align: right;">${count}</td>
                    <td style="text-align: right;">${percentage}%</td>
                </tr>
            `;
        }
        sourcesBody.innerHTML = html;
    }
}

// ============ Celebrities List ============

async function loadCelebrities() {
    const tbody = document.getElementById('celebritiesBody');
    tbody.innerHTML = '<tr><td colspan="6"><div class="loading-spinner"></div></td></tr>';

    const data = await fetchAPI('/celebrities');

    if (!data) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: #dc2626;">Failed to load celebrities</td></tr>';
        return;
    }

    allCelebrities = data.celebrities || [];

    if (allCelebrities.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 2rem; color: #6b7280;">No celebrities found in database</td></tr>';
        return;
    }

    displayCelebrities(allCelebrities);
}

function displayCelebrities(celebrities) {
    const tbody = document.getElementById('celebritiesBody');
    tbody.innerHTML = '';

    celebrities.forEach(celeb => {
        const row = document.createElement('tr');
        const sources = celeb.data_sources || [];

        let sourceHtml = '';
        if (sources.length > 0) {
            sourceHtml = `
                <div class="source-tags">
                    ${sources.map(s => `<span class="source-tag">${s.source}</span>`).join('')}
                </div>
            `;
        } else {
            sourceHtml = '<span class="text-muted">-</span>';
        }

        row.innerHTML = `
            <td><code>${celeb.celebrity_id}</code></td>
            <td>${celeb.name || '-'}</td>
            <td>${celeb.nationality || '-'}</td>
            <td>${celeb.birth_date ? new Date(celeb.birth_date).toLocaleDateString() : '-'}</td>
            <td>${sourceHtml}</td>
            <td><button class="btn btn-sm btn-secondary" onclick="viewDetails('${celeb.celebrity_id}')">View</button></td>
        `;

        tbody.appendChild(row);
    });
}

function filterCelebrities(query) {
    const filtered = allCelebrities.filter(celeb => {
        const name = (celeb.name || '').toLowerCase();
        const id = (celeb.celebrity_id || '').toLowerCase();
        const searchQuery = query.toLowerCase();

        return name.includes(searchQuery) || id.includes(searchQuery);
    });

    displayCelebrities(filtered);
}

// ============ Celebrity Details ============

async function viewDetails(celebrityId) {
    const modal = document.getElementById('detailModal');
    const modalBody = document.getElementById('modalBody');

    // Show loading
    modalBody.innerHTML = '<div class="text-center" style="padding: 2rem;"><div class="loading-spinner"></div></div>';
    modal.classList.add('show');

    const data = await fetchAPI(`/celebrity/${celebrityId}`);

    if (!data) {
        modalBody.innerHTML = '<p style="color: #dc2626;">Failed to load details</p>';
        return;
    }

    const metadata = data.metadata || {};
    const sources = data.data_sources || [];

    let html = `
        <h2>📋 Celebrity Details: ${metadata.name || 'Unknown'}</h2>

        <div style="margin: 2rem 0;">
            <h3>Metadata</h3>
            <div class="detail-grid">
                <div class="detail-item">
                    <label>Celebrity ID</label>
                    <div class="value"><code>${metadata.celebrity_id}</code></div>
                </div>
                <div class="detail-item">
                    <label>Name</label>
                    <div class="value">${metadata.name || '-'}</div>
                </div>
                <div class="detail-item">
                    <label>Birth Date</label>
                    <div class="value">${metadata.birth_date ? new Date(metadata.birth_date).toLocaleDateString() : '-'}</div>
                </div>
                <div class="detail-item">
                    <label>Nationality</label>
                    <div class="value">${metadata.nationality || '-'}</div>
                </div>
                <div class="detail-item">
                    <label>Occupation</label>
                    <div class="value">${Array.isArray(metadata.occupation) ? metadata.occupation.join(', ') : '-'}</div>
                </div>
                <div class="detail-item">
                    <label>Active</label>
                    <div class="value"><span class="badge ${metadata.is_active ? 'success' : 'error'}">${metadata.is_active ? 'Yes' : 'No'}</span></div>
                </div>
                <div class="detail-item">
                    <label>Created</label>
                    <div class="value text-small">${metadata.created_at ? new Date(metadata.created_at).toLocaleString() : '-'}</div>
                </div>
                <div class="detail-item">
                    <label>Updated</label>
                    <div class="value text-small">${metadata.updated_at ? new Date(metadata.updated_at).toLocaleString() : '-'}</div>
                </div>
            </div>
        </div>
    `;

    // Data Sources
    if (sources.length > 0) {
        html += `<div style="margin: 2rem 0;"><h3>Data Sources (${sources.length})</h3>`;

        sources.forEach(source => {
            const weight = source.weight !== null ? `<span class="badge info">${source.weight.toFixed(2)}</span>` : '<span class="text-muted">-</span>';
            const sentiment = source.sentiment || '<span class="text-muted">-</span>';

            html += `
                <div class="source-entry">
                    <h4>📌 ${source.source_type}</h4>
                    <div class="source-entry-grid">
                        <div>
                            <strong>Timestamp:</strong><br>
                            <code class="text-small">${source.timestamp || '-'}</code>
                        </div>
                        <div>
                            <strong>Source URL:</strong><br>
                            <code class="text-small">${source.source || '-'}</code>
                        </div>
                        <div>
                            <strong>Weight (Confidence):</strong><br>
                            ${weight}
                        </div>
                        <div>
                            <strong>Sentiment:</strong><br>
                            ${sentiment}
                        </div>
                    </div>

                    <div style="margin-top: 1rem;">
                        <strong>Raw Text (${source.raw_text_length} bytes)</strong>
                        <div class="raw-text-preview">${escapeHtml(source.raw_text_preview)}</div>
                    </div>

                    <div style="margin-top: 1rem;">
                        <button class="btn btn-sm btn-secondary" onclick="loadFullRawText('${celebrityId}', '${source.source_type}')">
                            View Full Raw Text
                        </button>
                    </div>
                </div>
            `;
        });

        html += '</div>';
    } else {
        html += `
            <div style="background: #fffbeb; padding: 1rem; border-radius: 6px; margin: 2rem 0;">
                <strong>⚠️ No data sources found</strong><br>
                This celebrity has metadata but no scraper entries yet.
            </div>
        `;
    }

    // Validation
    html += `
        <div style="margin: 2rem 0;">
            <h3>Validation</h3>
            <button class="btn btn-primary" onclick="validateCelebrity('${celebrityId}')">
                Run Validation
            </button>
            <div id="validationResult" style="margin-top: 1rem;"></div>
        </div>
    `;

    modalBody.innerHTML = html;
}

async function loadFullRawText(celebrityId, sourceType) {
    const data = await fetchAPI(`/raw/${celebrityId}/${sourceType}`);

    if (!data) {
        showError('Failed to load raw text');
        return;
    }

    const modal = document.getElementById('detailModal');
    const modalBody = document.getElementById('modalBody');

    let html = `
        <h2>📄 Raw Data: ${data.source_type}</h2>
        <p class="text-muted">Timestamp: ${data.timestamp}</p>

        <div style="margin: 2rem 0;">
    `;

    if (data.is_json) {
        html += `<pre class="raw-text-preview">${escapeHtml(JSON.stringify(data.data, null, 2))}</pre>`;
    } else {
        html += `<pre class="raw-text-preview">${escapeHtml(data.data)}</pre>`;
    }

    html += `
        </div>
        <button class="btn btn-secondary" onclick="viewDetails('${celebrityId}')">Back to Details</button>
    `;

    modalBody.innerHTML = html;
}

// ============ Validation ============

async function validateCelebrity(celebrityId) {
    const resultDiv = document.getElementById('validationResult');
    resultDiv.innerHTML = '<div class="loading-spinner"></div>';

    const data = await fetchAPI(`/validate/celebrity/${celebrityId}`);

    if (!data) {
        resultDiv.innerHTML = '<p style="color: #dc2626;">Validation failed</p>';
        return;
    }

    let html = `
        <div class="validation-result ${data.valid ? 'pass' : 'fail'}">
            <div class="validation-header">
                <h3>${data.celebrity_id}</h3>
                <span class="badge ${data.valid ? 'success' : 'error'}">${data.validation_status}</span>
            </div>

            <div style="margin-top: 1rem;">
                <strong>Status:</strong> ${data.has_metadata ? '✓ Metadata found' : '✗ No metadata'}<br>
                <strong>Scraper Entries:</strong> ${data.scraper_entries}<br>
                <strong>Total Entries:</strong> ${data.total_entries}
            </div>
    `;

    if (data.errors && data.errors.length > 0) {
        html += `
            <div style="margin-top: 1rem;">
                <strong style="color: #dc2626;">❌ Errors:</strong>
                <ul class="error-list">
                    ${data.errors.map(e => `<li>${e}</li>`).join('')}
                </ul>
            </div>
        `;
    }

    if (data.warnings && data.warnings.length > 0) {
        html += `
            <div style="margin-top: 1rem;">
                <strong style="color: #ea580c;">⚠️ Warnings:</strong>
                <ul class="warning-list">
                    ${data.warnings.map(w => `<li>${w}</li>`).join('')}
                </ul>
            </div>
        `;
    }

    html += '</div>';
    resultDiv.innerHTML = html;
}

async function validateAll() {
    const resultsDiv = document.getElementById('validationResults');
    resultsDiv.innerHTML = '<div style="text-align: center;"><div class="loading-spinner"></div></div>';

    const data = await fetchAPI('/validate/all');

    if (!data) {
        resultsDiv.innerHTML = '<p style="color: #dc2626;">Validation failed</p>';
        return;
    }

    let html = `
        <div style="margin-bottom: 2rem;">
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>Total Celebrities</h3>
                    <div class="value">${data.total_celebrities}</div>
                </div>
                <div class="stat-card">
                    <h3>Passed</h3>
                    <div class="value" style="color: #16a34a;">${data.passed}</div>
                </div>
                <div class="stat-card">
                    <h3>Failed</h3>
                    <div class="value" style="color: #dc2626;">${data.failed}</div>
                </div>
                <div class="stat-card">
                    <h3>With Warnings</h3>
                    <div class="value" style="color: #ea580c;">${data.with_warnings}</div>
                </div>
            </div>
        </div>
    `;

    // Show failures first
    const failures = data.results.filter(r => r.status === 'FAIL');
    if (failures.length > 0) {
        html += '<h3 style="color: #dc2626; margin: 2rem 0 1rem;">❌ Failed Validations</h3>';
        failures.forEach(result => {
            html += formatValidationResult(result);
        });
    }

    // Show warnings
    const warnings = data.results.filter(r => r.status === 'PASS' && r.warnings.length > 0);
    if (warnings.length > 0) {
        html += '<h3 style="color: #ea580c; margin: 2rem 0 1rem;">⚠️ Passed with Warnings</h3>';
        warnings.forEach(result => {
            html += formatValidationResult(result);
        });
    }

    // Show passes
    const passes = data.results.filter(r => r.status === 'PASS' && r.warnings.length === 0);
    if (passes.length > 0) {
        html += `<p style="color: #16a34a; margin-top: 2rem;">✓ ${passes.length} celebrities passed all validations</p>`;
    }

    resultsDiv.innerHTML = html;
}

function formatValidationResult(result) {
    let html = `
        <div class="validation-result ${result.status === 'PASS' ? 'pass' : 'fail'}">
            <div class="validation-header">
                <h3>${result.celebrity_id}</h3>
                <span class="badge ${result.status === 'PASS' ? 'success' : 'error'}">${result.status}</span>
            </div>

            <div style="margin-top: 1rem;">
                <strong>Entries:</strong> ${result.entries} (${result.scraper_entries} scraped)<br>
                <strong>Metadata:</strong> ${result.has_metadata ? '✓' : '✗'}
            </div>
    `;

    if (result.errors && result.errors.length > 0) {
        html += `
            <ul class="error-list">
                ${result.errors.map(e => `<li>${e}</li>`).join('')}
            </ul>
        `;
    }

    if (result.warnings && result.warnings.length > 0) {
        html += `
            <ul class="warning-list">
                ${result.warnings.map(w => `<li>${w}</li>`).join('')}
            </ul>
        `;
    }

    html += '</div>';
    return html;
}

// ============ Schema ============

async function loadSchema() {
    const data = await fetchAPI('/schema');
    const schemaDiv = document.getElementById('schemaInfo');

    if (!data) {
        schemaDiv.innerHTML = '<p style="color: #dc2626;">Failed to load schema</p>';
        return;
    }

    let html = `
        <div class="detail-grid">
            <div class="detail-item">
                <label>Table Name</label>
                <div class="value"><code>${data.table_name}</code></div>
            </div>
            <div class="detail-item">
                <label>Billing Mode</label>
                <div class="value">${data.billing_mode}</div>
            </div>
            <div class="detail-item">
                <label>Streams Enabled</label>
                <div class="value">${data.stream_enabled ? '✓ Yes' : '✗ No'}</div>
            </div>
            <div class="detail-item">
                <label>Stream View Type</label>
                <div class="value">${data.stream_view_type}</div>
            </div>
        </div>

        <h3 style="margin-top: 2rem;">Keys</h3>
        <div class="detail-grid">
            <div class="detail-item">
                <label>Partition Key</label>
                <div class="value"><code>${data.partition_key}</code></div>
            </div>
            <div class="detail-item">
                <label>Sort Key</label>
                <div class="value"><code>${data.sort_key}</code></div>
            </div>
        </div>

        <h3 style="margin-top: 2rem;">Global Secondary Indexes</h3>
        <table class="schema-table">
            <thead>
                <tr>
                    <th>Index Name</th>
                    <th>Partition Key</th>
                    <th>Sort Key</th>
                    <th>Projection</th>
                </tr>
            </thead>
            <tbody>
    `;

    data.gsi.forEach(index => {
        html += `
            <tr>
                <td><code>${index.index_name}</code></td>
                <td><code>${index.partition_key}</code></td>
                <td>${index.sort_key ? `<code>${index.sort_key}</code>` : '-'}</td>
                <td>${index.projection}</td>
            </tr>
        `;
    });

    html += `
            </tbody>
        </table>
    `;

    schemaDiv.innerHTML = html;
}

// ============ Export (Excel-style) ============

function exportToCSV() {
    if (allCelebrities.length === 0) {
        showError('No data to export');
        return;
    }

    // Create CSV headers
    const headers = ['ID', 'Name', 'Nationality', 'Birth Date', 'Data Sources', 'Active'];

    // Create CSV rows
    const rows = allCelebrities.map(celeb => [
        celeb.celebrity_id || '',
        celeb.name || '',
        celeb.nationality || '',
        celeb.birth_date ? new Date(celeb.birth_date).toLocaleDateString() : '',
        (celeb.data_sources || []).map(s => s.source).join('; ') || '',
        celeb.is_active ? 'Yes' : 'No'
    ]);

    // Combine headers and rows
    const csvContent = [
        headers.join(','),
        ...rows.map(row => row.map(cell => {
            // Escape cells with commas or quotes
            if (typeof cell === 'string' && (cell.includes(',') || cell.includes('"'))) {
                return `"${cell.replace(/"/g, '""')}"`;
            }
            return cell;
        }).join(','))
    ].join('\n');

    // Create download link
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);

    link.setAttribute('href', url);
    link.setAttribute('download', `celebrities_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// ============ Utilities ============

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showError(message) {
    // Create a simple error message (could be improved with a toast notification)
    console.error(message);
}

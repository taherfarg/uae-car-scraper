// app/static/js/app.js
// UAE Car Market Search — Frontend Application

const API = {
    search: '/api/search',
    filters: '/api/filters',
    autocomplete: '/api/autocomplete',
    compare: '/api/compare',
    trending: '/api/trending',
};

let state = {
    currentPage: 1,
    totalPages: 1,
    perPage: 24,
    viewMode: 'grid',
    filters: {},
    modelsByBrand: {},
    lastSearch: {},
    autocompleteTimer: null,
    compareChart: null,
};

// ═══ INITIALIZATION ═══
document.addEventListener('DOMContentLoaded', () => {
    loadFilters();
    loadTrending();
    setupSearchInput();
    setupKeyboardShortcuts();
});

async function loadFilters() {
    try {
        const res = await fetch(API.filters);
        const data = await res.json();
        state.filters = data;
        state.modelsByBrand = data.models_by_brand || {};
        populateDropdown('filterBrand', data.brands, 'All Brands');
        populateDropdown('filterBodyType', data.body_types, 'All Types');
        populateDropdown('filterFuelType', data.fuel_types, 'All Fuels');
        populateDropdown('compareBrand', data.brands, 'Select Brand');
        document.getElementById('totalListings').textContent = (data.total_listings || 0).toLocaleString();
        document.getElementById('totalBrands').textContent = (data.brands || []).length;
        if (data.last_updated) {
            const d = new Date(data.last_updated);
            document.getElementById('lastUpdated').textContent = d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
        }
    } catch (err) { console.error('Failed to load filters:', err); }
}

function populateDropdown(elementId, items, defaultText) {
    const select = document.getElementById(elementId);
    if (!select) return;
    select.innerHTML = `<option value="">${defaultText}</option>`;
    (items || []).forEach(item => {
        const opt = document.createElement('option');
        opt.value = item.name;
        opt.textContent = `${item.name} (${item.count})`;
        select.appendChild(opt);
    });
}

// ═══ SEARCH ═══
async function executeSearch(page = 1) {
    state.currentPage = page;
    const params = new URLSearchParams();
    const q = document.getElementById('searchInput').value.trim();
    if (q) params.set('q', q);

    const fields = {
        brand: 'filterBrand', model: 'filterModel', body_type: 'filterBodyType',
        fuel_type: 'filterFuelType', transmission: 'filterTransmission',
        source: 'filterSource', specs_origin: 'filterSpecs',
        min_year: 'filterMinYear', max_year: 'filterMaxYear',
        min_price: 'filterMinPrice', max_price: 'filterMaxPrice',
    };
    for (const [param, elId] of Object.entries(fields)) {
        const val = document.getElementById(elId)?.value;
        if (val) params.set(param, val);
    }
    params.set('sort', document.getElementById('filterSort')?.value || 'price_asc');
    params.set('page', page);
    params.set('per_page', state.perPage);
    state.lastSearch = Object.fromEntries(params);

    showLoading(true);
    hideElement('noResults');
    hideElement('trendingSection');
    showElement('resultsStats');

    try {
        const res = await fetch(`${API.search}?${params.toString()}`);
        const data = await res.json();
        renderResults(data);
    } catch (err) {
        console.error('Search failed:', err);
        showLoading(false);
        showElement('noResults');
    }
}

function renderResults(data) {
    showLoading(false);
    const { listings, total, page, total_pages, query_time_ms, price_stats } = data;

    document.getElementById('resultsCount').innerHTML = `<strong>${total.toLocaleString()}</strong> results found`;
    document.getElementById('queryTime').textContent = `${query_time_ms}ms`;
    if (price_stats) {
        document.getElementById('statMinPrice').textContent = `AED ${Number(price_stats.min_price).toLocaleString()}`;
        document.getElementById('statAvgPrice').textContent = `AED ${Number(price_stats.avg_price).toLocaleString()}`;
        document.getElementById('statMaxPrice').textContent = `AED ${Number(price_stats.max_price).toLocaleString()}`;
        document.getElementById('statMedianPrice').textContent = `AED ${Number(price_stats.median_price).toLocaleString()}`;
    }

    if (listings.length === 0) {
        showElement('noResults');
        hideElement('pagination');
        document.getElementById('carGrid').innerHTML = '';
        document.getElementById('carList').innerHTML = '';
        return;
    }
    hideElement('noResults');
    if (state.viewMode === 'grid') renderGridView(listings);
    else renderListView(listings);
    state.totalPages = total_pages;
    updatePagination(page, total_pages);
}

function renderGridView(listings) {
    const grid = document.getElementById('carGrid');
    grid.style.display = 'grid';
    document.getElementById('carList').style.display = 'none';

    grid.innerHTML = listings.map(car => {
        const brand = car.brand || 'Unknown', model = car.model || '';
        const year = car.year ? Math.round(car.year) : '';
        const price = Number(car.price || 0);
        const mileage = car.mileage ? Number(car.mileage) : null;
        const source = (car.source || '').toLowerCase();
        const sourceClass = source === 'dubizzle' ? 'source-dubizzle' : 'source-dubicars';
        const sourceLabel = source === 'dubizzle' ? 'Dubizzle' : 'Dubicars';

        let flagHtml = '';
        const flag = car.cross_source_flag || '';
        if (flag.includes('Deal')) flagHtml = `<span class="card-flag flag-deal">${flag}</span>`;
        else if (flag.includes('Below')) flagHtml = `<span class="card-flag flag-below">${flag}</span>`;
        else if (flag.includes('Overpriced')) flagHtml = `<span class="card-flag flag-overpriced">${flag}</span>`;
        else if (flag.includes('Above')) flagHtml = `<span class="card-flag flag-above">${flag}</span>`;

        const specs = [];
        if (year) specs.push('\u{1F4C5} ' + year);
        if (mileage) specs.push('\u{1F6E3}\uFE0F ' + mileage.toLocaleString() + ' km');
        if (car.body_type && car.body_type !== 'Unknown') specs.push('\u{1F697} ' + car.body_type);
        if (car.fuel_type && car.fuel_type !== 'Unknown') specs.push('\u26FD ' + car.fuel_type);
        if (car.transmission) specs.push('\u2699\uFE0F ' + car.transmission);
        if (car.location) specs.push('\u{1F4CD} ' + car.location);

        const url = car.url || '#';
        const quality = car.quality_score ? Math.round(car.quality_score) : null;

        let metaHtml = '';
        if (car.dealer) {
            metaHtml += `<div class="MuiStack-root mui-style-ec72kz" style="margin-top: 10px; margin-bottom: 5px;">
<div class="MuiStack-root mui-style-1x1lpva" style="display: flex; align-items: center; gap: 10px;">
<div class="MuiAvatar-root MuiAvatar-circular mui-style-7c7x4" data-testid="logo" style="width: 40px; height: 40px; border-radius: 50%; overflow: hidden;">
<img alt="logo" class="MuiAvatar-img mui-style-1hy9t21" src="https://dbz-images.dubizzle.com/profiles/auto_agency/WhatsApp_Image_2023-08-25_at_15.04.58.jpg?impolicy=agency" style="width: 100%; height: 100%; object-fit: cover;">
</div>
<div class="MuiStack-root mui-style-1rv8lu4">
<div class="MuiStack-root mui-style-17vz4mw">
<p class="MuiTypography-root MuiTypography-h6 mui-style-kbemd9" data-testid="name" style="margin: 0; font-weight: bold; font-size: 0.9rem;">${car.dealer}</p>
</div>
<div class="MuiStack-root mui-style-17vz4mw">
<p class="MuiTypography-root MuiTypography-body1 mui-style-18kuz3" data-testid="type" style="margin: 0; font-size: 0.75rem; color: #666;">Dealer</p>
</div>
<a href="#" data-testid="view-all-cars" as="[object Object]" class="mui-style-83iz7f" style="font-size: 0.75rem; text-decoration: none; color: #1976d2;">View All Cars</a>
</div>
</div>
</div>`;
        }
        if (car.publish_date) {
            const date = new Date(car.publish_date);
            const day = date.getDate();
            const nth = function(d) {
                if (d > 3 && d < 21) return 'th';
                switch (d % 10) {
                    case 1:  return "st";
                    case 2:  return "nd";
                    case 3:  return "rd";
                    default: return "th";
                }
            };
            const dateStr = day + nth(day) + ' ' + date.toLocaleString('default', { month: 'long' }) + ' ' + date.getFullYear();
            metaHtml += `<p class="MuiTypography-root MuiTypography-body1 mui-style-1ddiinb" data-testid="posted-on" style="font-size:0.8rem;color:var(--text-muted);margin-top:0.25rem;margin-bottom:0;"><span class="MuiTypography-root MuiTypography-body1 mui-style-1twx1ef">Posted on<!-- -->:</span>&nbsp;<!-- -->${dateStr}</p>`;
        }

        return `<div class="car-card" onclick="window.open('${url}','_blank')">
            <div class="card-header">
                <div><div class="card-title">${brand} ${model}</div><div class="card-year">${year ? year + ' Model' : ''}</div></div>
                <span class="card-source ${sourceClass}">${sourceLabel}</span>
            </div>
            <div class="card-price">AED ${price.toLocaleString()} <small>/ ${car.price_tier || ''}</small></div>
            <div class="card-specs">${specs.map(s => `<span class="spec-tag">${s}</span>`).join('')}</div>
            ${metaHtml}
            <div class="card-footer">
                ${flagHtml}
                <span style="color:var(--text-muted);font-size:0.75rem;">${quality ? 'Quality: ' + quality + '/100' : ''}</span>
                <a href="${url}" target="_blank" class="card-link" onclick="event.stopPropagation()">View Listing \u2192</a>
            </div>
        </div>`;
    }).join('');
}

function renderListView(listings) {
    const list = document.getElementById('carList');
    list.style.display = 'block';
    document.getElementById('carGrid').style.display = 'none';
    list.innerHTML = listings.map(car => {
        const url = car.url || '#';
        let metaHtml = '';
        if (car.dealer) metaHtml += `<span style="margin-left: 10px;" title="Dealer">\u{1F3EA} ${car.dealer}</span>`;
        if (car.publish_date) {
            const date = new Date(car.publish_date);
            const day = date.getDate();
            const nth = function(d) {
                if (d > 3 && d < 21) return 'th';
                switch (d % 10) {
                    case 1:  return "st";
                    case 2:  return "nd";
                    case 3:  return "rd";
                    default: return "th";
                }
            };
            const dateStr = day + nth(day) + ' ' + date.toLocaleString('default', { month: 'long' }) + ' ' + date.getFullYear();
            metaHtml += `<span class="MuiTypography-root MuiTypography-body1 mui-style-1ddiinb" data-testid="posted-on" style="margin-left: 10px;" title="Published"><span class="MuiTypography-root MuiTypography-body1 mui-style-1twx1ef">Posted on<!-- -->:</span>&nbsp;<!-- -->${dateStr}</span>`;
        }
        
        return `<div class="car-list-item" onclick="window.open('${url}','_blank')">
            <div class="list-title">${car.brand || 'Unknown'} ${car.model || ''}<small>${car.year ? Math.round(car.year) : ''} \u00B7 ${car.body_type || ''} \u00B7 ${car.fuel_type || ''}</small></div>
            <div class="list-price">AED ${Number(car.price || 0).toLocaleString()}</div>
            <div class="list-specs">${car.mileage ? Number(car.mileage).toLocaleString() + ' km' : '\u2014'}</div>
            <div class="list-specs" style="text-transform:capitalize">${car.source || ''}${metaHtml}</div>
            <a href="${url}" target="_blank" class="card-link" onclick="event.stopPropagation()">View \u2192</a>
        </div>`;
    }).join('');
}

// ═══ AUTOCOMPLETE ═══
function setupSearchInput() {
    const input = document.getElementById('searchInput');
    const dropdown = document.getElementById('autocompleteDropdown');
    input.addEventListener('input', (e) => {
        clearTimeout(state.autocompleteTimer);
        const q = e.target.value.trim();
        if (q.length < 2) { dropdown.style.display = 'none'; return; }
        state.autocompleteTimer = setTimeout(async () => {
            try {
                const res = await fetch(`${API.autocomplete}?q=${encodeURIComponent(q)}&limit=8`);
                const data = await res.json();
                renderAutocomplete(data.suggestions);
            } catch (err) { console.error('Autocomplete error:', err); }
        }, 250);
    });
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') { dropdown.style.display = 'none'; executeSearch(); }
        if (e.key === 'Escape') dropdown.style.display = 'none';
    });
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.search-input-wrap')) dropdown.style.display = 'none';
    });
}

function renderAutocomplete(suggestions) {
    const dropdown = document.getElementById('autocompleteDropdown');
    if (!suggestions || suggestions.length === 0) { dropdown.style.display = 'none'; return; }
    dropdown.innerHTML = suggestions.map(s => {
        const typeClass = s.type === 'brand' ? 'ac-type-brand' : 'ac-type-model';
        const typeLabel = s.type === 'brand' ? 'Brand' : 'Model';
        return `<div class="autocomplete-item" onclick="selectAutocomplete(${JSON.stringify(s).replace(/"/g, '&quot;')})">
            <div><div class="ac-text">${s.text}</div><div class="ac-meta">${s.label}</div></div>
            <span class="ac-type ${typeClass}">${typeLabel}</span>
        </div>`;
    }).join('');
    dropdown.style.display = 'block';
}

function selectAutocomplete(suggestion) {
    document.getElementById('autocompleteDropdown').style.display = 'none';
    if (suggestion.type === 'brand') {
        document.getElementById('filterBrand').value = suggestion.brand;
        document.getElementById('searchInput').value = suggestion.brand;
        onBrandChange();
    } else {
        document.getElementById('filterBrand').value = suggestion.brand;
        onBrandChange();
        setTimeout(() => { document.getElementById('filterModel').value = suggestion.model; }, 100);
        document.getElementById('searchInput').value = `${suggestion.brand} ${suggestion.model}`;
    }
    executeSearch();
}

// ═══ FILTER HELPERS ═══
function onBrandChange() {
    const brand = document.getElementById('filterBrand').value;
    const modelSelect = document.getElementById('filterModel');
    modelSelect.innerHTML = '<option value="">All Models</option>';
    if (brand && state.modelsByBrand[brand]) {
        state.modelsByBrand[brand].forEach(m => {
            const opt = document.createElement('option');
            opt.value = m.name;
            opt.textContent = `${m.name} (${m.count})`;
            modelSelect.appendChild(opt);
        });
    }
}

function toggleFilters() {
    const panel = document.getElementById('filtersPanel');
    const icon = document.getElementById('filterToggleIcon');
    panel.classList.toggle('open');
    icon.textContent = panel.classList.contains('open') ? '\u25B2' : '\u25BC';
}

function clearFilters() {
    document.getElementById('searchInput').value = '';
    document.getElementById('filterBrand').value = '';
    document.getElementById('filterModel').innerHTML = '<option value="">All Models</option>';
    ['filterBodyType','filterFuelType','filterTransmission','filterSource','filterSpecs'].forEach(id => document.getElementById(id).value = '');
    ['filterMinYear','filterMaxYear','filterMinPrice','filterMaxPrice'].forEach(id => document.getElementById(id).value = '');
    document.getElementById('filterSort').value = 'price_asc';
}

function setView(mode) {
    state.viewMode = mode;
    document.getElementById('btnGridView').classList.toggle('active', mode === 'grid');
    document.getElementById('btnListView').classList.toggle('active', mode === 'list');
    if (state.lastSearch && Object.keys(state.lastSearch).length > 0) executeSearch(state.currentPage);
}

function setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        if (e.key === '/' && document.activeElement.tagName !== 'INPUT') {
            e.preventDefault();
            document.getElementById('searchInput').focus();
        }
    });
}

// ═══ PAGINATION ═══
function updatePagination(current, total) {
    const pagEl = document.getElementById('pagination');
    if (total <= 1) { pagEl.style.display = 'none'; return; }
    pagEl.style.display = 'flex';
    document.getElementById('pageInfo').textContent = `Page ${current} of ${total}`;
    document.getElementById('prevBtn').disabled = current <= 1;
    document.getElementById('nextBtn').disabled = current >= total;
}

function changePage(delta) {
    const newPage = state.currentPage + delta;
    if (newPage < 1 || newPage > state.totalPages) return;
    executeSearch(newPage);
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ═══ PRICE COMPARE MODAL ═══
function openCompare() {
    document.getElementById('compareModal').style.display = 'flex';
    document.getElementById('compareResults').innerHTML = '';
    document.getElementById('compareChart').style.display = 'none';
    if (state.filters.brands) populateDropdown('compareBrand', state.filters.brands, 'Select Brand');
}

function closeCompare() {
    document.getElementById('compareModal').style.display = 'none';
    if (state.compareChart) { state.compareChart.destroy(); state.compareChart = null; }
}

function onCompareBrandChange() {
    const brand = document.getElementById('compareBrand').value;
    const modelSelect = document.getElementById('compareModel');
    modelSelect.innerHTML = '<option value="">Select Model</option>';
    if (brand && state.modelsByBrand[brand]) {
        state.modelsByBrand[brand].forEach(m => {
            const opt = document.createElement('option');
            opt.value = m.name;
            opt.textContent = `${m.name} (${m.count})`;
            modelSelect.appendChild(opt);
        });
    }
}

async function runCompare() {
    const brand = document.getElementById('compareBrand').value;
    const model = document.getElementById('compareModel').value;
    if (!brand || !model) { alert('Please select both Brand and Model'); return; }

    const resultsDiv = document.getElementById('compareResults');
    resultsDiv.innerHTML = '<div class="loading"><div class="spinner"></div><p>Comparing prices...</p></div>';

    try {
        const res = await fetch(`${API.compare}?brand=${encodeURIComponent(brand)}&model=${encodeURIComponent(model)}`);
        if (!res.ok) {
            resultsDiv.innerHTML = `<div class="no-results"><div class="no-results-icon">\u{1F50D}</div><h3>No listings found</h3><p>No ${brand} ${model} listings available for comparison.</p></div>`;
            return;
        }
        const data = await res.json();
        renderCompareResults(data);
    } catch (err) {
        console.error('Compare failed:', err);
        resultsDiv.innerHTML = '<p style="color:var(--red);">Comparison failed. Please try again.</p>';
    }
}

function renderCompareResults(data) {
    const resultsDiv = document.getElementById('compareResults');
    const sources = data.source_comparison || {};

    let html = `<div style="margin-bottom:1rem;">
        <h3 style="color:var(--text);">${data.brand} ${data.model}</h3>
        <p style="color:var(--text-muted);font-size:0.85rem;">${data.total_listings} listings \u00B7 Years: ${data.year_range} \u00B7 Market Avg: AED ${Number(data.market_average).toLocaleString()}</p>
    </div>`;

    const sourceNames = Object.keys(sources);
    if (sourceNames.length > 0) {
        html += '<div class="compare-grid">';
        for (const src of sourceNames) {
            const s = sources[src];
            const srcLabel = src === 'dubizzle' ? '\u{1F534} Dubizzle' : '\u{1F535} Dubicars';
            html += `<div class="compare-card"><h4>${srcLabel}</h4>
                <div class="compare-stat"><span class="label">Listings</span><span class="value">${s.count}</span></div>
                <div class="compare-stat"><span class="label">Min Price</span><span class="value best">AED ${Number(s.min_price).toLocaleString()}</span></div>
                <div class="compare-stat"><span class="label">Avg Price</span><span class="value">AED ${Number(s.avg_price).toLocaleString()}</span></div>
                <div class="compare-stat"><span class="label">Max Price</span><span class="value">AED ${Number(s.max_price).toLocaleString()}</span></div>
                <div class="compare-stat"><span class="label">Avg Mileage</span><span class="value">${Number(s.avg_mileage).toLocaleString()} km</span></div>
            </div>`;
        }
        html += '</div>';
    }

    if (data.best_deal) {
        const deal = data.best_deal;
        html += `<div class="compare-best-deal"><h4>\u{1F3C6} Best Deal Found</h4>
            <div class="deal-price">AED ${Number(deal.price).toLocaleString()}</div>
            <p>${deal.year ? Math.round(deal.year) : ''} ${deal.brand} ${deal.model} ${deal.mileage ? '\u00B7 ' + Number(deal.mileage).toLocaleString() + ' km' : ''} \u00B7 on ${deal.source}</p>
            ${deal.url ? `<a href="${deal.url}" target="_blank" class="card-link" style="margin-top:0.5rem;display:inline-block;">View Listing \u2192</a>` : ''}
        </div>`;
    }
    resultsDiv.innerHTML = html;
    renderCompareChart(data);
}

function renderCompareChart(data) {
    const canvas = document.getElementById('compareChart');
    const yearly = data.yearly_prices;
    if (!yearly || Object.keys(yearly).length < 2) { canvas.style.display = 'none'; return; }
    canvas.style.display = 'block';
    if (state.compareChart) state.compareChart.destroy();

    const years = Object.keys(yearly).sort();
    const srcs = new Set();
    years.forEach(y => Object.keys(yearly[y]).forEach(s => srcs.add(s)));
    const colors = { dubizzle: '#e11d48', dubicars: '#3b82f6' };
    const datasets = [];
    for (const src of srcs) {
        datasets.push({
            label: src.charAt(0).toUpperCase() + src.slice(1) + ' (Avg Price)',
            data: years.map(y => yearly[y][src]?.avg_price || null),
            borderColor: colors[src] || '#8b5cf6',
            backgroundColor: (colors[src] || '#8b5cf6') + '20',
            tension: 0.3, fill: true, spanGaps: true,
        });
    }
    state.compareChart = new Chart(canvas, {
        type: 'line', data: { labels: years, datasets },
        options: {
            responsive: true,
            plugins: { legend: { position: 'top' }, title: { display: true, text: `${data.brand} ${data.model} \u2014 Price by Year`, color: '#f0f4f8' } },
            scales: { y: { ticks: { callback: v => 'AED ' + Number(v).toLocaleString() } } },
        },
    });
}

// ═══ TRENDING ═══
async function loadTrending() {
    try {
        const res = await fetch(`${API.trending}?limit=12`);
        const data = await res.json();
        document.getElementById('trendingGrid').innerHTML = (data.most_listed || []).map((car, i) => `
            <div class="trending-card" onclick="quickSearch('${car.brand}','${car.model}')">
                <span class="trending-rank">#${i + 1}</span>
                <div class="trending-name">${car.brand} ${car.model}</div>
                <div class="trending-stats">
                    <span><strong>${car.cnt}</strong> listings</span>
                    <span>From <strong style="color:var(--green)">AED ${Number(car.min_price).toLocaleString()}</strong></span>
                    <span>Avg <strong>AED ${Number(car.avg_price).toLocaleString()}</strong></span>
                </div>
            </div>`).join('');

        document.getElementById('cheapestGrid').innerHTML = (data.cheapest_by_brand || []).map(car => `
            <div class="cheapest-item" onclick="quickSearch('${car.brand}','')">
                <div class="cheapest-name">${car.brand}<small>${car.model} ${car.year ? '\u00B7 ' + Math.round(car.year) : ''}</small></div>
                <div class="cheapest-price">AED ${Number(car.price).toLocaleString()}</div>
            </div>`).join('');
    } catch (err) { console.error('Failed to load trending:', err); }
}

function quickSearch(brand, model) {
    document.getElementById('filterBrand').value = brand;
    onBrandChange();
    if (model) setTimeout(() => { document.getElementById('filterModel').value = model; }, 100);
    document.getElementById('searchInput').value = `${brand} ${model}`.trim();
    executeSearch();
}

// ═══ UTILITY ═══
function showLoading(show) {
    document.getElementById('loading').style.display = show ? 'block' : 'none';
    if (show) { document.getElementById('carGrid').innerHTML = ''; document.getElementById('carList').innerHTML = ''; }
}
function showElement(id) { document.getElementById(id).style.display = ''; }
function hideElement(id) { const el = document.getElementById(id); if (el) el.style.display = 'none'; }

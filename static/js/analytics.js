// analytics.js - Fetches analytics data and renders charts using Chart.js

document.addEventListener('DOMContentLoaded', () => {
    const gold = '#c49b63';
    const goldDark = '#8e7037';
    const taupe = '#7a6a58';
    const taupeLite = 'rgba(122,106,88,0.25)';
    const goldLite = 'rgba(196,155,99,0.25)';

    // Chart.js dark theme defaults (for dark dashboard)
    if (window.Chart) {
        Chart.defaults.color = '#e2e8f0';
        Chart.defaults.borderColor = 'rgba(226,232,240,0.12)';
        Chart.defaults.plugins.legend.labels.color = '#cbd5e1';
        Chart.defaults.plugins.title.color = '#f8fafc';
        Chart.defaults.scale.grid.color = 'rgba(226,232,240,0.12)';
        Chart.defaults.scale.ticks.color = '#cbd5e1';
    }

    const state = {
        category: '',
        unit: '',
        year_min: '',
        year_max: '',
        search: ''
    };

    const charts = {};

    function buildQuery() {
        const params = new URLSearchParams();
        if (state.category) params.set('category', state.category);
        if (state.unit) params.set('unit', state.unit);
        if (state.year_min) params.set('year_min', state.year_min);
        if (state.year_max) params.set('year_max', state.year_max);
        if (state.search) params.set('search', state.search);
        return params.toString() ? ('?' + params.toString()) : '';
    }

    function updateChips() {
        const el = document.getElementById('filterChips');
        if (!el) return;
        const chips = [];
        if (state.category) chips.push(chip('Catégorie', state.category, () => {state.category=''; reload();}));
        if (state.unit) chips.push(chip('Unité', state.unit, () => {state.unit=''; reload();}));
        if (state.year_min) chips.push(chip('Année ≥', state.year_min, () => {state.year_min=''; reload();}));
        if (state.year_max) chips.push(chip('Année ≤', state.year_max, () => {state.year_max=''; reload();}));
        el.innerHTML = chips.join(' ');
        // Update filter count badge in sidebar header
        const count = [state.category, state.unit, state.year_min, state.year_max, state.search]
            .filter(v => v && String(v).trim() !== '').length;
        const badge = document.getElementById('filterCount');
        if (badge) badge.textContent = String(count);
    }

    function chip(label, value, onClose) {
        const id = 'chip_' + Math.random().toString(36).slice(2);
        // attach handler after insert
        setTimeout(() => {
            const btn = document.getElementById(id);
            if (btn) btn.addEventListener('click', onClose);
        }, 0);
        return `<span class="badge bg-warning text-dark me-2">${label}: ${escapeHtml(value)} <button id="${id}" class="btn btn-sm btn-link text-dark p-0 ms-1" title="Retirer">×</button></span>`;
    }

    function escapeHtml(s){
        return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'}[c]));
    }

    async function fetchData() {
        const loading = document.getElementById('analyticsLoading');
        if (loading) loading.style.display = '';
        try {
            const res = await fetch('/api/analytics' + buildQuery());
            return await res.json();
        } finally {
            if (loading) loading.style.display = 'none';
        }
    }

    function updateStats(data) {
        const total = Object.values(data.category_counts || {}).reduce((a,b)=>a+b,0);
        const catGroups = Object.keys(data.category_group_counts || {}).length;
        const units = Object.keys(data.unit_counts || {}).length;
        const totalEl = document.getElementById('totalCount');
        const catGroupEl = document.getElementById('catGroupCount');
        const unitEl = document.getElementById('unitCount');
        if (totalEl) totalEl.textContent = total;
        if (catGroupEl) catGroupEl.textContent = catGroups;
        if (unitEl) unitEl.textContent = units;
    }

    function ensureSelectOptions(selectId, options) {
        const sel = document.getElementById(selectId);
        if (!sel) return;
        const current = new Set(Array.from(sel.options).map(o => o.value));
        const frag = document.createDocumentFragment();
        // Keep first option (Toutes)
        while (sel.options.length > 1) sel.remove(1);
        options.forEach(v => {
            const opt = document.createElement('option');
            opt.value = v; opt.textContent = v;
            frag.appendChild(opt);
        });
        sel.appendChild(frag);
    }

    function createOrUpdateChart(key, ctxId, cfg) {
        if (charts[key]) {
            // update dataset and labels
            charts[key].data = cfg.data;
            charts[key].options = {...charts[key].options, ...cfg.options};
            charts[key].update();
            return charts[key];
        }
        charts[key] = new Chart(document.getElementById(ctxId), cfg);
        return charts[key];
    }

    function wireChartClicks(chart, labelToFilter, stateKey) {
        chart.options.onClick = (evt, elements) => {
            if (!elements || !elements.length) return;
            const idx = elements[0].index;
            const label = chart.data.labels[idx];
            if (state[stateKey] === String(label).toLowerCase()) return;
            state[stateKey] = String(label).toLowerCase();
            // also set selects if present
            const sel = document.getElementById(labelToFilter);
            if (sel) sel.value = label;
            reload();
        };
    }

    async function reload() {
        updateChips();
        const data = await fetchData();
        updateStats(data);

        // Update header total
        const headerTotal = document.getElementById('headerTotal');
        if (headerTotal) {
            const totalHeader = Object.values(data.category_counts || {}).reduce((a,b)=>a+b,0);
            headerTotal.textContent = totalHeader.toString();
        }

        // KPI donut charts removed
        const unitEntriesAll = Object.entries(data.unit_counts || {}).sort((a,b)=>b[1]-a[1]);

        // keep selects in sync with fresh options
        ensureSelectOptions('filterCategory', Object.keys(data.category_group_counts || {}));
        ensureSelectOptions('filterUnit', Object.keys(data.unit_counts || {}));
        if (state.category) {
            const sel = document.getElementById('filterCategory');
            if (sel) sel.value = Object.keys(data.category_group_counts || {}).find(k => k.toLowerCase() === state.category) || '';
        }
        if (state.unit) {
            const sel2 = document.getElementById('filterUnit');
            if (sel2) sel2.value = Object.keys(data.unit_counts || {}).find(k => k.toLowerCase() === state.unit) || '';
        }

        // 1. Top unités (horizontal)
        const unitEntries = Object.entries(data.unit_counts || {}).sort((a,b)=>b[1]-a[1]).slice(0,7);
        const topUnitsCfg = {
            type: 'bar',
            data: {
                labels: unitEntries.map(([u]) => u),
                datasets: [{ label: 'Nombre de produits', data: unitEntries.map(([,c])=>c), backgroundColor: gold }]
            },
            options: { responsive: true, maintainAspectRatio: false, indexAxis: 'y', plugins: {title: {display: true, text: 'Top unités de production'}} }
        };
        const cu = createOrUpdateChart('topUnits', 'topUnitsBarChart', topUnitsCfg);
        wireChartClicks(cu, 'filterUnit', 'unit');

        // 2. Category group bar
        const catCfg = {
            type: 'bar',
            data: {
                labels: Object.keys(data.category_group_counts || {}),
                datasets: [{ label: 'Nombre de produits', data: Object.values(data.category_group_counts || {}), backgroundColor: taupe }]
            },
            options: { responsive: true, maintainAspectRatio: false, plugins: {title: {display: true, text: 'Distribution par groupe de catégorie'}} }
        };
        const cc = createOrUpdateChart('catGroup', 'categoryGroupBarChart', catCfg);
        wireChartClicks(cc, 'filterCategory', 'category');

        // 3. Label pie
        createOrUpdateChart('labelPie', 'labelPieChart', {
            type: 'pie',
            data: { labels: Object.keys(data.label_counts||{}), datasets: [{ data: Object.values(data.label_counts||{}), backgroundColor: [gold, taupe, goldDark, '#b3a591'] }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: {title: {display: true, text: 'Répartition des produits labellisés'}} }
        });

        // 4. Year line
        createOrUpdateChart('yearLine', 'yearLineChart', {
            type: 'line',
            data: { labels: Object.keys(data.year_counts||{}), datasets: [{ label: 'Nombre de produits', data: Object.values(data.year_counts||{}), borderColor: goldDark, backgroundColor: goldLite, fill: true }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: {title: {display: true, text: 'Volume de production par année'}} }
        });

        // 5. Stacked area
        createOrUpdateChart('stackedArea', 'stackedAreaChart', {
            type: 'line',
            data: { labels: (data.stacked_area||{}).years || [], datasets: ((data.stacked_area||{}).groups||[]).map((g,i)=>({ label: g, data: (data.stacked_area.values||[]).map(r=>r[i]), fill: true, borderColor: i%2===0?goldDark:taupe, backgroundColor: i%2===0?goldLite:taupeLite })) },
            options: { responsive: true, maintainAspectRatio: false, plugins: {title: {display: true, text: 'Évolution des catégories par année'}}, interaction: {mode: 'index', intersect: false}, stacked: true }
        });

        // 6. Handmade bar (stacked)
        createOrUpdateChart('handmade', 'handmadeBarChart', {
            type: 'bar',
            data: { labels: (data.handmade_time||{}).years || [], datasets: ((data.handmade_time||{}).types||[]).map((t,i)=>({ label: t, data: (data.handmade_time.values||[]).map(r=>r[i]), backgroundColor: i===0?gold:taupe })) },
            options: { responsive: true, maintainAspectRatio: false, plugins: {title: {display: true, text: 'Produits faits main vs non faits main par année'}}, scales: {x:{stacked:true}, y:{stacked:true}} }
        });

        // (price chart removed)

        // Bind download buttons
        document.querySelectorAll('.btn-download').forEach(btn => {
            btn.onclick = () => {
                const key = btn.getAttribute('data-chart');
                const chart = charts[key];
                if (!chart) return;
                const a = document.createElement('a');
                a.href = chart.toBase64Image();
                a.download = `${key}.png`;
                a.click();
            };
        });
    }

    // Wire filters UI
    const catSel = document.getElementById('filterCategory');
    const unitSel = document.getElementById('filterUnit');
    const yMin = document.getElementById('filterYearMin');
    const yMax = document.getElementById('filterYearMax');
    // Search removed
    // Auto-apply filters on change
    function applyFromUI(){
        state.category = (catSel && catSel.value) || '';
        state.unit = (unitSel && unitSel.value) || '';
        state.year_min = (yMin && yMin.value) || '';
        state.year_max = (yMax && yMax.value) || '';
        reload();
    }
    if (catSel) catSel.addEventListener('change', applyFromUI);
    if (unitSel) unitSel.addEventListener('change', applyFromUI);
    if (yMin) yMin.addEventListener('change', applyFromUI);
    if (yMax) yMax.addEventListener('change', applyFromUI);
    // No search input; state.search remains available if needed for URL-driven filtering

    // Clear all filters button
    const clearAllBtn = document.getElementById('filtersClearAll');
    if (clearAllBtn){
        clearAllBtn.addEventListener('click', () => {
            state.category = state.unit = state.year_min = state.year_max = state.search = '';
            if (catSel) catSel.value=''; if (unitSel) unitSel.value=''; if (yMin) yMin.value=''; if (yMax) yMax.value='';
            reload();
        });
    }

    // Initial load
    reload();

    // Prediction demo handlers (unchanged)
    const btnCat = document.getElementById('btnPredictCategory');
    if (btnCat) {
        btnCat.addEventListener('click', () => {
            const body = {
                description: document.getElementById('catDesc').value,
                annee: parseInt(document.getElementById('catYear').value || '0') || null,
                unite_production: document.getElementById('catProd').value
            };
            fetch('/api/predict_category', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)})
                .then(r => r.json())
                .then(r => {
                    document.getElementById('catResult').textContent = r.predicted ? `${r.predicted} (${r.confidence ? (r.confidence*100).toFixed(0)+'%' : ''})` : (r.error || 'Erreur');
                });
        });
    }
    const btnLab = document.getElementById('btnPredictLabel');
    if (btnLab) {
        btnLab.addEventListener('click', () => {
            const body = {
                description: document.getElementById('labDesc').value,
                categorie: document.getElementById('labCat').value,
                unite_production: document.getElementById('labProd').value,
                annee: parseInt(document.getElementById('labYear').value || '0') || null,
            };
            fetch('/api/predict_label', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)})
                .then(r => r.json())
                .then(r => {
                    document.getElementById('labResult').textContent = r.predicted ? `${r.predicted}${r.probability ? ' ('+(r.probability*100).toFixed(0)+'%)' : ''}` : (r.error || 'Erreur');
                });
        });
    }
});

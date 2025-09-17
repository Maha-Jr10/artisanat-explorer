// products.js - Handles fetching, displaying, searching, and filtering products

document.addEventListener('DOMContentLoaded', function() {
    const productsList = document.getElementById('productsList');
    const searchInput = document.getElementById('searchInput');
    const categoryFilter = document.getElementById('categoryFilter');
    const categoryMenu = document.getElementById('categoryMenu');
    const categoryDropdownBtn = document.getElementById('categoryDropdownBtn');
    const unitFilter = document.getElementById('unitFilter');
    const unitMenu = document.getElementById('unitMenu');
    const unitDropdownBtn = document.getElementById('unitDropdownBtn');
    const resetBtn = document.getElementById('resetFiltersBtn');
    const activeFilters = document.getElementById('activeFilters');

    let allProducts = [];

    // Helper: decide if a value is meaningful to display to end users
    function isMeaningful(val) {
        if (val === null || val === undefined) return false;
        const s = String(val).trim();
        if (!s) return false;
        const sl = s.toLowerCase();
        const bad = new Set(['non', 'non disponible', 'non spécifié', 'non specifie', 'unknown', 'n/a', 'na', 'nan', 'none']);
        return !bad.has(sl);
    }

    // Helper: humanize unit strings like 'FezPottery' => 'Fez Pottery', 'fez_pottery' => 'Fez Pottery'
    function humanizeUnit(val) {
        if (!isMeaningful(val)) return '';
        let s = String(val).trim();
        s = s.replace(/[_-]+/g, ' ');
        s = s.replace(/([a-z])([A-Z])/g, '$1 $2');
        s = s.replace(/\s+/g, ' ').trim();
        // Title case simple words
        s = s.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
        return s;
    }

    // Helper: format price by appending currency if missing
    function formatPrice(value) {
        if (!isMeaningful(value)) return '';
        const s = String(value).trim();
        // Detect if currency already present
        const hasCurrency = /(dhs|mad|€|\$|usd|eur|د\.م\.|dh)/i.test(s);
        // Detect numeric
        const isNumeric = /^(\d+[\.,]?\d*)$/.test(s);
        if (hasCurrency) return s;
        if (isNumeric) return `${s} Dhs`;
        return s; // fallback
    }

    // Fetch products from backend
    function fetchProducts() {
        const search = searchInput.value.trim();
    const category = categoryFilter.value;
    let url = '/api/products?';
        if (search) url += `search=${encodeURIComponent(search)}&`;
        if (category) url += `category=${encodeURIComponent(category)}`;
    const unit = unitFilter.value;
    if (unit) url += `${category ? '&' : ''}unit=${encodeURIComponent(unit)}`;
        fetch(url)
            .then(res => res.json())
            .then(data => {
                allProducts = data.products;
                renderProducts(allProducts);
                renderCategories(data.categories);
                renderUnits(data.units || []);
                // Update stats bar if present
                const totalEl = document.getElementById('totalCount');
                const catEl = document.getElementById('catCount');
                const unitEl = document.getElementById('unitCount');
                if (totalEl) totalEl.textContent = allProducts.length;
                if (catEl) catEl.textContent = (data.categories || []).length;
                if (unitEl) unitEl.textContent = (data.units || []).length;
                // Active filters chips
                if (activeFilters) {
                    activeFilters.innerHTML = '';
                    if (search) addChip('Recherche', search);
                    if (category) addChip('Catégorie', category);
                    if (unit) addChip('Unité', unit);
                }
            });
    }

    function addChip(label, value) {
        const chip = document.createElement('span');
        chip.className = 'filter-chip';
        chip.textContent = `${label}: ${value}`;
        activeFilters.appendChild(chip);
    }

    // Render products
    function renderProducts(products) {
        productsList.innerHTML = '';
        if (products.length === 0) {
            productsList.innerHTML = '<div class="col-12 text-center">Aucun produit trouvé.</div>';
            return;
        }
        products.forEach(prod => {
            const card = document.createElement('div');
            card.className = 'col-sm-6 col-lg-4';
            card.innerHTML = `
                <div class="card h-100 product-card">
                    <div class="img-wrap position-relative">
                        <img src="${prod.lien_image ? `/img?url=${encodeURIComponent(prod.lien_image)}` : (prod.image ? `/img?url=${encodeURIComponent(prod.image)}` : '/static/images/welcome_page.png')}" class="card-img-top" alt="${prod.nom_produit}" onerror="this.onerror=null;this.src='/static/images/img_unavailable.svg';">
                        ${(prod.category_par_group ? `<span class=\"category-pill\">${prod.category_par_group}</span>` : (prod.categorie ? `<span class=\"category-pill\">${prod.categorie}</span>` : ''))}
                    </div>
                    <div class="card-body">
                        <h6 class="card-title mb-2">${prod.nom_produit}</h6>
                        <p class="card-text clamp-3 mb-2">${prod.description || ''}</p>
                        <div class="d-flex flex-wrap gap-2 mb-2">
                            ${isMeaningful(prod.price) && /\d/.test(String(prod.price))
                                ? `<span class=\"badge bg-secondary\">${formatPrice(prod.price)}</span>`
                                : `<span class=\"badge bg-secondary\">Prix: Non disponible</span>`}
                            ${isMeaningful(prod.unite_production)
                                ? `<span class=\"badge bg-dark\">Unité: ${humanizeUnit(prod.unite_production)}</span>`
                                : `<span class=\"badge bg-dark\">Unité: Non disponible</span>`}
                        </div>
                            <div class="d-flex justify-content-between align-items-center w-100 mt-auto">
                                ${prod.reference_produit ? `<button class="btn btn-sm btn-outline-primary" data-ref="${prod.reference_produit}"><i class="fas fa-magnifying-glass"></i> Produits similaires</button>` : ''}
                            <button class="btn btn-sm btn-primary ms-auto" title="Détails" aria-label="Voir les détails" data-bs-toggle="tooltip" data-bs-placement="top" data-details='${JSON.stringify({
                                reference: prod.reference_produit || '',
                                nom: prod.nom_produit || '',
                                categorie: prod.categorie || '',
                                group: prod.category_par_group || '',
                                unite: prod.unite_production || '',
                                annee: prod.annee || '',
                                labelisation: prod.labelisation || '',
                                nom_label: prod.nom_label || '',
                                price: prod.price || '',
                                dimensions: prod.dimensions || '',
                                image: prod.lien_image || prod.image || '',
                                description: prod.description || ''
                            }).replace(/"/g, '&quot;')}'><i class="fas fa-circle-info"></i> Détails</button>
                        </div>
                    </div>
                </div>
            `;
            productsList.appendChild(card);
            // Add recs handler (pass current product for context)
            const btn = card.querySelector('button[data-ref]');
            if (btn) {
                btn.addEventListener('click', () => showRecommendations(btn.getAttribute('data-ref'), prod));
            }
            // Add details handler
            const detailsBtn = card.querySelector('button[data-details]');
            if (detailsBtn) {
                detailsBtn.addEventListener('click', () => showDetails(JSON.parse(detailsBtn.getAttribute('data-details'))));
            }
        });
    }

    // Render categories in filter dropdown
    function renderCategories(categories) {
        // Build dropdown items
        categoryMenu.innerHTML = '';
        const allItem = document.createElement('li');
        allItem.innerHTML = `<a class="dropdown-item" href="#" data-value="">Toutes les catégories</a>`;
        categoryMenu.appendChild(allItem);
        categories.forEach(cat => {
            const li = document.createElement('li');
            li.innerHTML = `<a class="dropdown-item" href="#" data-value="${cat}">${cat}</a>`;
            categoryMenu.appendChild(li);
        });
        // Click handler
        categoryMenu.querySelectorAll('.dropdown-item').forEach(a => {
            a.addEventListener('click', (e) => {
                e.preventDefault();
                const val = a.getAttribute('data-value') || '';
                categoryFilter.value = val;
                categoryDropdownBtn.textContent = val || 'Toutes les catégories';
                fetchProducts();
            });
        });
    }

    function renderUnits(units) {
        unitMenu.innerHTML = '';
        const allItem = document.createElement('li');
        allItem.innerHTML = `<a class="dropdown-item" href="#" data-value="">Toutes les unités</a>`;
        unitMenu.appendChild(allItem);
        units.forEach(u => {
            const li = document.createElement('li');
            li.innerHTML = `<a class="dropdown-item" href="#" data-value="${u}">${u}</a>`;
            unitMenu.appendChild(li);
        });
        unitMenu.querySelectorAll('.dropdown-item').forEach(a => {
            a.addEventListener('click', (e) => {
                e.preventDefault();
                const val = a.getAttribute('data-value') || '';
                unitFilter.value = val;
                unitDropdownBtn.textContent = val || 'Toutes les unités';
                fetchProducts();
            });
        });
    }

    // Event listeners
    searchInput.addEventListener('input', fetchProducts);
    // Native change listeners not needed for custom dropdowns; handled on click
    if (resetBtn) {
        resetBtn.addEventListener('click', () => {
            searchInput.value = '';
            categoryFilter.value = '';
            unitFilter.value = '';
            fetchProducts();
        });
    }

    // Initial fetch
    fetchProducts();

    // Back to Top behavior (products page only)
    const backToTopBtn = document.getElementById('backToTop');
    if (backToTopBtn) {
        const toggleBackToTop = () => {
            const y = window.scrollY || document.documentElement.scrollTop;
            if (y > 300) backToTopBtn.classList.add('show');
            else backToTopBtn.classList.remove('show');
        };
        window.addEventListener('scroll', toggleBackToTop, { passive: true });
        toggleBackToTop();
        backToTopBtn.addEventListener('click', () => {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }

    // Recommendations logic
    function showRecommendations(reference, baseProd) {
        const container = document.getElementById('recsContainer');
        container.innerHTML = '<div class="col-12 text-center text-muted">Chargement...</div>';
        fetch(`/api/recommendations?reference=${encodeURIComponent(reference)}&k=3`)
            .then(res => {
                if (!res.ok) {
                    return res.text().then(t => { throw new Error(t || `HTTP ${res.status}`); });
                }
                return res.json();
            })
            .then(data => {
                container.innerHTML = '';
                const recs = Array.isArray(data.recommendations) ? data.recommendations : [];
                if (recs.length === 0) {
                    container.innerHTML = '<div class="col-12"><div class="alert alert-warning mb-0">Aucun produit similaire trouvé pour cet article.</div></div>';
                } else {
                    recs.forEach(prod => {
                        const col = document.createElement('div');
                        col.className = 'col-md-4';
                        const groupText = prod.category_par_group || prod.categorie || '';
                        const priceText = (typeof formatPrice === 'function') ? formatPrice(prod.price) : (prod.price || '');
                        const unitText = (typeof humanizeUnit === 'function') ? humanizeUnit(prod.unite_production) : (prod.unite_production || '');
                        col.innerHTML = `
                            <div class="card h-100">
                                <img src="${prod.lien_image ? `/img?url=${encodeURIComponent(prod.lien_image)}` : (prod.image ? `/img?url=${encodeURIComponent(prod.image)}` : '/static/images/welcome_page.png')}" class="card-img-top" alt="${prod.nom_produit}" onerror="this.onerror=null;this.src='/static/images/img_unavailable.svg';">
                                <div class="card-body">
                                    <h6 class="card-title">${prod.nom_produit}</h6>
                                    <div class="d-flex flex-wrap gap-2 mt-2 align-items-center">
                                        ${groupText ? `<span class=\"badge bg-primary\">${groupText}</span>` : ''}
                                        ${priceText ? `<span class=\"badge bg-secondary\">${priceText}</span>` : `<span class=\"badge bg-secondary\">Prix: Non disponible</span>`}
                                        ${unitText ? `<span class=\"badge bg-dark\">Unité: ${unitText}</span>` : `<span class=\"badge bg-dark\">Unité: Non disponible</span>`}
                                    </div>
                                </div>
                            </div>
                        `;
                        container.appendChild(col);
                    });
                }
                const modal = new bootstrap.Modal(document.getElementById('recsModal'));
                modal.show();
            })
            .catch(err => {
                container.innerHTML = `<div class="col-12"><div class=\"alert alert-danger mb-0\">Impossible de récupérer les produits similaires. ${err.message ? '(' + err.message + ')' : ''}</div></div>`;
                const modal = new bootstrap.Modal(document.getElementById('recsModal'));
                modal.show();
            });
    }

    // Details modal renderer
    function showDetails(info) {
        const body = document.getElementById('detailsBody');
        const priceDisplay = formatPrice(info.price) || 'Non disponible';
        const unitDisplay = humanizeUnit(info.unite) || 'Non disponible';
        body.innerHTML = `
            <div class="row g-3">
                <div class="col-md-5">
                    <img src="${info.image ? `/img?url=${encodeURIComponent(info.image)}` : '/static/images/welcome_page.png'}" alt="${info.nom}" class="img-fluid rounded" onerror="this.onerror=null;this.src='/static/images/img_unavailable.svg';">
                </div>
                <div class="col-md-7">
                    <h5 class="mb-2">${info.nom}</h5>
                    <div class="mb-2">${info.group || info.categorie ? `<span class='badge bg-primary me-2'>${info.group || info.categorie}</span>` : ''}<span class='badge bg-dark'>Unité: ${unitDisplay}</span></div>
                    <p class="mb-2">${info.description || ''}</p>
                    <ul class="list-unstyled small mb-0">
                        ${info.reference ? `<li><strong>Référence:</strong> ${info.reference}</li>` : ''}
                        ${info.annee ? `<li><strong>Année:</strong> ${info.annee}</li>` : ''}
                        <li><strong>Prix:</strong> ${priceDisplay}</li>
                        ${info.dimensions ? `<li><strong>Dimensions:</strong> ${info.dimensions}</li>` : ''}
                        ${info.labelisation ? `<li><strong>Labelisation:</strong> ${info.labelisation}${info.nom_label ? ` - ${info.nom_label}` : ''}</li>` : ''}
                    </ul>
                </div>
            </div>
        `;
        const modal = new bootstrap.Modal(document.getElementById('detailsModal'));
        modal.show();
    }
});

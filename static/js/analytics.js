// analytics.js - Fetches analytics data and renders charts using Chart.js

document.addEventListener('DOMContentLoaded', function() {
    fetch('/api/analytics')
        .then(res => res.json())
        .then(data => {
            // 1. Category Bar Chart
            new Chart(document.getElementById('categoryBarChart'), {
                type: 'bar',
                data: {
                    labels: Object.keys(data.category_counts),
                    datasets: [{
                        label: 'Nombre de produits',
                        data: Object.values(data.category_counts),
                        backgroundColor: 'rgba(44, 130, 201, 0.7)'
                    }]
                },
                options: {responsive: true, plugins: {title: {display: true, text: 'Distribution par catégorie'}}}
            });
            // 2. Category Group Bar Chart
            new Chart(document.getElementById('categoryGroupBarChart'), {
                type: 'bar',
                data: {
                    labels: Object.keys(data.category_group_counts),
                    datasets: [{
                        label: 'Nombre de produits',
                        data: Object.values(data.category_group_counts),
                        backgroundColor: 'rgba(231, 76, 60, 0.7)'
                    }]
                },
                options: {responsive: true, plugins: {title: {display: true, text: 'Distribution par groupe de catégorie'}}}
            });
            // 3. Label Pie Chart
            new Chart(document.getElementById('labelPieChart'), {
                type: 'pie',
                data: {
                    labels: Object.keys(data.label_counts),
                    datasets: [{
                        data: Object.values(data.label_counts),
                        backgroundColor: ['#27ae60', '#f1c40f', '#e67e22', '#95a5a6']
                    }]
                },
                options: {responsive: true, plugins: {title: {display: true, text: 'Répartition des produits labellisés'}}}
            });
            // 4. Year Line Chart
            new Chart(document.getElementById('yearLineChart'), {
                type: 'line',
                data: {
                    labels: Object.keys(data.year_counts),
                    datasets: [{
                        label: 'Nombre de produits',
                        data: Object.values(data.year_counts),
                        borderColor: '#16a085',
                        backgroundColor: 'rgba(22, 160, 133, 0.2)',
                        fill: true
                    }]
                },
                options: {responsive: true, plugins: {title: {display: true, text: 'Volume de production par année'}}}
            });
            // 5. Stacked Area Chart (as line chart with fill)
            new Chart(document.getElementById('stackedAreaChart'), {
                type: 'line',
                data: {
                    labels: data.stacked_area.years,
                    datasets: data.stacked_area.groups.map((g, i) => ({
                        label: g,
                        data: data.stacked_area.values.map(row => row[i]),
                        fill: true
                    }))
                },
                options: {responsive: true, plugins: {title: {display: true, text: 'Évolution des catégories par année'}},
                    interaction: {mode: 'index', intersect: false},
                    stacked: true
                }
            });
            // 6. Handmade Bar Chart
            new Chart(document.getElementById('handmadeBarChart'), {
                type: 'bar',
                data: {
                    labels: data.handmade_time.years,
                    datasets: data.handmade_time.types.map((t, i) => ({
                        label: t,
                        data: data.handmade_time.values.map(row => row[i]),
                        backgroundColor: i === 0 ? '#8e44ad' : '#f39c12'
                    }))
                },
                options: {responsive: true, plugins: {title: {display: true, text: 'Produits faits main vs non faits main par année'}},
                    scales: {x: {stacked: true}, y: {stacked: true}}
                }
            });
            // 7. Price by Category Group
            new Chart(document.getElementById('priceBarChart'), {
                type: 'bar',
                data: {
                    labels: Object.keys(data.price_by_group),
                    datasets: [{
                        label: 'Prix moyen (MAD)',
                        data: Object.values(data.price_by_group),
                        backgroundColor: '#e67e22'
                    }]
                },
                options: {responsive: true, plugins: {title: {display: true, text: 'Prix moyen par groupe de catégorie'}}}
            });
        });

    // Prediction demo handlers
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

# Artisanat Explorer – Découverte de l'Artisanat Marocain (UI + Analytics + IA locale optionnelle)

![Accueil](./static/images/welcome_page.png)

## 🌟 Présentation
Artisanat Explorer est une application web qui met en valeur le patrimoine artisanal marocain (Poterie, Céramique, Peinture, Calligraphie) et propose :
- Une page Produits avec recherche/filtre, détails et recommandations
- Une page Analytique avec graphiques thématiques et indicateurs
- Un assistant conversationnel (RAG) optionnel basé sur Ollama (si disponible)

## ✨ Fonctionnalités principales
- Produits (UI soignée)
  - Cartes produits avec image, groupe de catégorie, prix (MAD) et unité humanisée
  - Filtres: recherche plein‑texte (nom + description), groupe de catégorie et unité
  - Sélecteurs personnalisés (palette or/taupe, sans états bleus natifs)
  - Détails dans une modale + recommandations « Produits similaires » (Top 3)
  - Résilience images: proxy serveur `/img` + fallback visuel lorsque l’image source échoue
  - Bouton « retour en haut » flottant lors du scroll
- Analytique
  - Barre d’indicateurs: Produits | Catégories (groupes) | Unités
  - Graphiques Chart.js aux couleurs de la marque et tailles uniformes
  - Tableau de bord interactif: filtres (groupe, unité, année min/max, recherche) + clic sur barres pour filtrer
  - « Top unités de production » (barres horizontales), distributions par groupe, labels, années, etc.
- IA locale (optionnelle)
  - RAG local via Ollama (embeddings + LLM) avec persistance ChromaDB
  - Chat contextuel produit si un nom/référence est détecté

Notes :
- Le site fonctionne sans Ollama: l’UI Produits et Analytique restent pleinement opérationnelles. Si Ollama n’est pas lancé, le chatbot est simplement désactivé.

## 🛠️ Structure du Projet
```
artisanat-explorer/
├── app.py                        # Backend Flask (pages, APIs, proxy images) + RAG optionnel
├── cleaned_artisanal_products.csv# Dataset pré‑nettoyé utilisé au runtime
├── Peinture_et_Calligraphie.xlsx # Sources historiques (optionnelles)
├── Poterie_et_Céramique.xlsx     # Sources historiques (optionnelles)
├── chroma_db/                    # (AUTO) ChromaDB persistante (créée au 1er run RAG)
│   └── ...                       #   Fichiers internes de stockage vecteur
├── df_full.pkl                   # (AUTO) Cache DataFrame fusionné
├── static/
│   ├── css/style.css             # Styles généraux
│   ├── css/products.css          # Styles page Produits
│   ├── css/analytics.css         # Styles page Analytique
│   ├── js/script.js              # Logique accueil + chatbot (si actif)
│   ├── js/products.js            # Logique page Produits
│   ├── js/analytics.js           # Logique page Analytique (Chart.js)
│   └── images/*.png              # Illustrations & schéma RAG
├── templates/index.html          # Accueil (galerie + chatbot)
├── templates/products.html       # Page Produits
├── templates/analytics.html      # Page Analytique
├── tests/                        # Tests Pytest (extracteurs + endpoints)
├── __init__.py                   # Rend le dossier racine importable (tests)
├── requirements.txt              # Dépendances
└── README.md                     # Documentation (ce fichier)
```

Fichiers / dossiers générés automatiquement :
- `chroma_db/` : créé lors de la première initialisation des embeddings (supprimé si `FORCE_REEMBED=1`).
- `df_full.pkl` : cache du DataFrame consolidé (recalculé si besoin ou `FORCE_RELOAD_DATA=1`).
- `__pycache__/` : dossiers Python bytecode (peuvent être ignorés / supprimés sans risque).

## 📁 Importance des Fichiers / Rôles
Légende : **(Critique)** indispensable à l'exécution | **(Auto)** généré automatiquement | **(Perf)** optimisation performance | **(Test)** qualité / non production | **(Doc)** documentation.

| Élément | Rôle Principal | Notes Importantes |
|---------|----------------|-------------------|
| `app.py` **(Critique)** | Routes pages + API produits/analytique + proxy images + (option) pipeline RAG | L’IA est optionnelle; l’UI fonctionne sans Ollama. |
| `cleaned_artisanal_products.csv` **(Critique)** | Dataset pré‑nettoyé utilisé par l’app | Remplace la lecture Excel directe à l’exécution. |
| `Peinture_et_Calligraphie.xlsx` **(Source)** | Données peinture/calligraphie (historique) | Adapter le pipeline si structure modifiée. |
| `Poterie_et_Céramique.xlsx` **(Source)** | Données poterie/céramique (historique) | Idem ci‑dessus. |
| `df_full.pkl` **(Auto, Perf)** | Cache DataFrame fusionné et enrichi | Peut être supprimé : il sera régénéré. |
| `chroma_db/` **(Auto, Perf)** | Stockage persistant embeddings & métadonnées | Supprimer pour forcer un recalcul complet (`FORCE_REEMBED=1`). |
| `templates/index.html` **(Critique UI)** | Accueil (landing + galerie + chatbot) |  |
| `templates/products.html` **(Critique UI)** | Liste produits, filtres, recommandations, détails |  |
| `templates/analytics.html` **(Critique UI)** | Tableaux de bord analytiques |  |
| `static/css/style.css` **(UI)** | Styles généraux (palette, mise en page) |  |
| `static/css/products.css` **(UI)** | Badges, filtres, cartes produits |  |
| `static/css/analytics.css` **(UI)** | Hero, stats bar, gabarit des charts |  |
| `static/js/script.js` **(UI)** | Logique accueil/chatbot |  |
| `static/js/products.js` **(UI)** | Rendu produits, filtres, détails, recs, back‑to‑top |  |
| `static/js/analytics.js` **(UI)** | Stats bar et graphs Chart.js |  |
| `tests/test_extractors.py` **(Test)** | Vérifie robustesse regex dimensions / prix | Protège contre régressions de parsing. |
| `tests/test_api.py` **(Test)** | Vérifie endpoints de base | Alerte si refacto casse interface externe. |
| `pytest.ini` **(Test)** | Config Pytest | Simplifie `pytest` sans options. |
| `requirements.txt` **(Critique)** | Dépendances projet | Pins recommandés pour prod. |
| `README.md` **(Doc)** | Documentation vivante | Garder aligné après chaque refacto. |

### Résumé Impact
- Pour repartir « propre » : supprimer `df_full.pkl` + `chroma_db/` (recalcul complet au prochain lancement si RAG actif).
- Pour élargir le domaine de connaissance : mettre à jour le CSV nettoyé puis relancer. 
- Pour personnaliser l’UI : intervenir sur `products.html`, `analytics.html`, `products.css`, `analytics.css`, `products.js`, `analytics.js`.

## 🗂️ Schéma de Données (principales colonnes)
| Colonne | Description |
|---------|------------|
| reference_produit | Identifiant ou référence commerciale |
| nom_produit | Nom lisible du produit |
| categorie | Catégorie (Poterie, Céramique, Peinture, Calligraphie) |
| category_par_group | Groupe de catégorie (UI + analytique) |
| unite_production | Unité / atelier / artisan |
| annee | Année de fabrication (si disponible) |
| labelisation | Oui / Non / statut |
| nom_label | Nom du label éventuel |
| description | Texte libre nettoyé |
| lien_image / image | URLs d’images (passent par `/img`) |
| dimensions (option) | Extrait via regex si présent |
| price | Montant estimé/texte, affiché en MAD si numérique |
| cluster | Cluster KMeans (optionnel) |

## 🧠 Architecture & Flux RAG (optionnel)
Copier le contenu Mermaid (`static/images/rag_architecture.mmd`) dans https://mermaid.live puis exporter en SVG/PNG.

- Embeddings : `OllamaEmbeddings(model="mxbai-embed-large")`
- LLM : `Ollama(model="llama3.2:latest", temperature=0.7)`
- Stockage : dossier persistant `./chroma_db`
- Versionnage métadonnées : champ `metadata_version` (voir `app.py`)
- Reconstruction DataFrame : via `vector_store.get(include=["metadatas"])`
- Cache DataFrame : `df_full.pkl`
- Frontend : Bootstrap 5 + JS

## ⚙️ Technologies
| Couche | Outils |
|--------|--------|
| Frontend | HTML5, CSS3, Bootstrap 5, JS vanilla, Font Awesome, Chart.js |
| Backend | Flask |
| IA / RAG (option) | LangChain, langchain-community, langchain-ollama, ChromaDB |
| Données | pandas, scikit‑learn (TF‑IDF, KMeans, RandomForest), openpyxl |
| Autres | requests, markdown (rendu réponses) |

## 🚀 Démarrage rapide
### Prérequis
- Python 3.9+
- (Optionnel) [Ollama](https://ollama.com/) si vous souhaitez activer le chatbot RAG

### Installation
```powershell
# Cloner (exemple)
git clone https://github.com/Maha-Jr10/artisanat-explorer.git
cd artisanat-explorer

# Environnement virtuel
python -m venv venv
venv\Scripts\Activate.ps1

# Dépendances
pip install --upgrade pip
pip install -r requirements.txt

# (Option) Activer le chatbot RAG
# Ouvrir un second terminal et démarrer Ollama puis télécharger les modèles une seule fois:
# ollama serve
# ollama pull mxbai-embed-large
# ollama pull llama3.2:latest

# Exécuter l'application (UI Produits & Analytique fonctionne sans Ollama)
python app.py
```
Ensuite : http://localhost:5000

### Variables / configuration (environnement)
| Nom | Rôle | Valeur par défaut |
|-----|------|-------------------|
| `FORCE_RELOAD_DATA` | Ignore le pickle et relit les données | `0` |
| `FORCE_REEMBED` | Supprime `chroma_db/` et régénère toutes les embeddings | `0` |
| `EMBEDDINGS_MODEL` | Modèle embeddings Ollama | `mxbai-embed-large` |
| `LLM_MODEL` | Modèle LLM Ollama | `llama3.2:latest` |
| `FLASK_SECRET_KEY` | Clé secrète session (remplacer la valeur codée) | (vide) |

Exemple PowerShell :
```powershell
$env:FORCE_REEMBED = "1"          # Regénère le store une fois
$env:EMBEDDINGS_MODEL = "mxbai-embed-large"
$env:LLM_MODEL = "llama3.2:latest"
$env:FORCE_RELOAD_DATA = "1"
$env:FLASK_SECRET_KEY = "clef_prod_ultra_secrete"
python app.py
```

### ▶️ Exécution (étapes claires)
1. (Option chatbot) Lancer Ollama : `ollama serve` puis télécharger les modèles.
2. Démarrer l'application : `python app.py`.
3. Ouvrir : http://localhost:5000 et vérifier `/health`.

### Modes de lancement alternatifs
- Via Flask CLI (optionnel) :
  - PowerShell : `$env:FLASK_APP='app.py'; flask run --host=0.0.0.0 --port=5000`
- Forcer reconstruction embeddings :
  - `$env:FORCE_REEMBED='1'; python app.py`
- Ignorer le cache pickle et relire données :
  - `$env:FORCE_RELOAD_DATA='1'; python app.py`

### Arrêter
`Ctrl + C` dans le terminal où tourne Flask et (si désiré) fermer la fenêtre Ollama.

### Tests rapides
```powershell
pytest -q           # Tous les tests
pytest tests/test_api.py::test_health_endpoint_ok -q
```

### Production (aperçu minimal)
Pour un déploiement local durci :
- Exporter `FLASK_SECRET_KEY`.
- Lancer sous un serveur WSGI (ex: `waitress` sous Windows) :
  ```powershell
  pip install waitress
  python -m waitress --listen=0.0.0.0:5000 app:app
  ```
*(Optionnel) Ajouter un reverse proxy Nginx pour TLS / compression.*

### Nettoyage complet (full reset)
```powershell
Remove-Item -Recurse -Force chroma_db
Remove-Item df_full.pkl
$env:FORCE_REEMBED='1'
python app.py
```
*(Supprime le store et le cache → reconstruction complète.)*

## 🔌 Endpoints API
| Méthode | Route | Description |
|---------|-------|-------------|
| GET | `/` | Accueil (landing, galerie, chatbot) |
| GET | `/products` | Page Produits |
| GET | `/analytics` | Page Analytique |
| GET | `/api/products` | Liste + filtres (search, category, unit) |
| GET | `/api/recommendations` | Top 3 produits similaires |
| GET | `/api/analytics` | Données agrégées pour Chart.js |
| GET | `/api/clusters` | Infos clusters KMeans (démo) |
| POST | `/api/predict_category` | Démo prédiction du groupe de catégorie |
| POST | `/api/predict_label` | Démo prédiction de la labellisation |
| GET | `/img` | Proxy image (anti‑hotlink + entêtes adaptés) |
| GET | `/health` | Statut système (ok, records, store_loaded, metadata_version) |
| POST | `/ask` | Question au chatbot (RAG) |

### Exemple (PowerShell)
```powershell
Invoke-RestMethod -Uri http://localhost:5000/ask -Method Post -Body '{"question":"Liste des produits en céramique"}' -ContentType 'application/json'
```

### Détails de `/api/products`
- Recherche texte : `search` parcourt `nom_produit` et `description`
- Filtrage par groupe de catégorie : `category=<category_par_group>`
- Filtrage par unité : `unit=<unite_production>`
- Réponse : `{ products: [...], categories: [groupes], units: [...] }`

### Détails de `/api/analytics`
Retourne notamment :
- `category_counts`, `category_group_counts`, `label_counts`, `year_counts`
- `stacked_area` (years, groups, values)
- `handmade_time` (years, types, values)
- `price_by_group`
- `unit_counts` (NOUVEAU) → permet « Top unités de production » et compteur « Unités »

## 🧪 Logique clef du code
- Vérification de la disponibilité d'Ollama (si chatbot actif)
- Chargement du CSV nettoyé + enrichissements
- Cache DataFrame pickle + invalidation
- Extraction regex dimensions / prix (tests associés)
- Proxies d’images côté serveur (`/img`) + fallback côté client
- Stats & agrégations pour les graphiques (Chart.js)
- (Option) Chaîne `RetrievalQA` (`chain_type="stuff"`, k=5) si Ollama actif

## 🩺 Dépannage & erreurs courantes
| Problème | Cause probable | Solution |
|----------|----------------|----------|
| `Ollama connection failed` | Service non démarré | Lancer `ollama serve` puis relancer l'app |
| Aucune donnée chargée | CSV introuvable ou corrompu | Vérifier `cleaned_artisanal_products.csv` ou régénérer | 
| Temps long premier démarrage | Génération embeddings | Patience, puis réutilisation persist |
| Réponses hors sujet | Prompt général trop permissif | Ajuster consignes dans `init_ai` |
| Accents cassés en console | Encodage terminal Windows | `chcp 65001` avant exécution |
| Certaines images ne s'affichent pas | Hotlink/CORS/mixed‑content | Les images passent par `/img`; un fallback visuel est fourni |

## 🔒 Sécurité (état & pistes)
Statut actuel :
- `app.secret_key` doit être configurée via `FLASK_SECRET_KEY` en production.
- Rendu Markdown → HTML sans nettoyage HTML avancé.

Recommandé court terme :
1. Définir `FLASK_SECRET_KEY` en production.  
2. Ajouter une limite de longueur (ex: 500 caractères) sur `question`.  
3. Ajouter un nettoyage HTML (ex: `bleach.clean`) après conversion Markdown.

Améliorations futures : rate limiting (Flask-Limiter), journalisation structurée, endpoint `/metrics`, validation stricte des entrées.

## 🚧 Améliorations futures (suggestions)
- Pagination & filtrage avancé dans la galerie
- Export CSV / JSON des résultats
- Retrieval amélioré : MMR, reranking, hybrid BM25 + vecteurs
- Interface upload dynamique de nouveaux produits (rebuild embeddings incrémental)
- Internationalisation (FR / EN)
- Authentification artisan/admin + rôles
- Tests supplémentaires (prompt shaping, fallback errors)

## 🧪 Tests
Des tests Pytest couvrent :
- Extracteurs regex (`tests/test_extractors.py`)
- Endpoints de base (`tests/test_api.py`)

Exécution :
```powershell
pytest -q
```

## 👥 Équipe
Étudiants ISDIA – ENSA Fès :

| Membre | Contact |
|--------|---------|
| **John Muhammed** | [LinkedIn](https://www.linkedin.com/in/Maha-Jr/) \| [GitHub](https://github.com/Maha-Jr10) |
| **Ibnyassine Aya** | [LinkedIn](https://www.linkedin.com/in/aya-ibnyassine-80b017292) \| [GitHub](https://github.com/Aya-Ibnyassine) |
| **Berrahioui Hajar** | [LinkedIn](https://www.linkedin.com/in/hajar-berrahioui-03a2332b2?utm_source=share&utm_campaign=share_via&utm_content=profile&utm_medium=android_app) \| [GitHub](https://github.com/hajarbberrahioui) |

## 📄 Licence
La mention de licence MIT apparaît mais aucun fichier `LICENSE` n'est présent. Ajoutez un fichier `LICENSE` (MIT ou autre) ou adaptez cette section.

---
Faites une issue / pull request pour toute amélioration ou correction. Bonne exploration !
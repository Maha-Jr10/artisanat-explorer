# Artisanat Explorer – Plateforme IA de Découverte de l'Artisanat Marocain

![Accueil](./static/images/welcome_page.png)

## 🌟 Présentation
Artisanat Explorer est une application web immersive qui met en valeur le patrimoine artisanal marocain (Poterie, Céramique, Peinture, Calligraphie) et propose un assistant conversationnel intelligent alimenté par un pipeline RAG local (LLM + embeddings) fonctionnant entièrement hors‑ligne (après téléchargement des modèles via Ollama).

## ✨ Points Clés
- Galerie moderne et responsive (Bootstrap 5) avec cartes illustrées
- Navigation améliorée (scroll fluide + mise en surbrillance dynamique de la section active)
- Assistant IA contextuel (mémoire de session + adaptation produit spécifique)
- Indicateur de « typing » + prévention du double envoi (bouton désactivé pendant la requête)
- RAG local : embeddings `mxbai-embed-large` + LLM `llama3.2:latest`
- Vector store persistant: **ChromaDB** 
- Reconstruction rapide du DataFrame depuis les métadonnées Chroma (évite relecture Excel)
- Cache pickle (`df_full.pkl`) invalidé automatiquement (mtime Excel ou `FORCE_RELOAD_DATA`)
- Endpoint santé `/health` (ok, records, store_loaded, metadata_version)
- Nettoyage & enrichissement (dimensions, prix) automatisés
- Réponses Markdown converties en HTML côté backend (voir section Sécurité)
- Fichier Mermaid source du schéma (`static/images/rag_architecture.mmd`) versionnable

## 🛠️ Structure du Projet
```
artisanat-explorer/
├── app.py                        # Backend Flask + pipeline RAG (caching + metadata version)
├── Peinture_et_Calligraphie.xlsx # Données source (peinture & calligraphie)
├── Poterie_et_Céramique.xlsx     # Données source (poterie & céramique)
├── chroma_db/                    # (AUTO) Dossier persistant embeddings Chroma (créé au 1er run)
│   └── ...                       #   Fichiers internes de stockage vecteur
├── df_full.pkl                   # (AUTO) Cache DataFrame fusionné (recréé si Excel change)
├── static/
│   ├── css/style.css             # Styles étendus & responsive
│   ├── js/script.js              # Logique UI + appels API chatbot
│   └── images/*.png              # Illustrations & schéma RAG (dont export Mermaid)
├── templates/index.html          # Page unique (landing + chatbot)
├── tests/                        # Tests Pytest (extracteurs + endpoints)
├── __init__.py                   # Rend le dossier racine importable (tests)
├── requirements.txt              # Dépendances (LangChain, Flask, etc.)
└── README.md                     # Documentation (ce fichier)
```

Fichiers / dossiers générés automatiquement :
- `chroma_db/` : créé lors de la première initialisation des embeddings (supprimé si `FORCE_REEMBED=1`).
- `df_full.pkl` : cache du DataFrame consolidé (recalculé si Excel plus récent ou `FORCE_RELOAD_DATA=1`).
- `__pycache__/` : dossiers Python bytecode (peuvent être ignorés / supprimés sans risque).

## � Importance des Fichiers / Rôles
Légende : **(Critique)** indispensable à l'exécution | **(Auto)** généré automatiquement | **(Perf)** optimisation performance | **(Test)** qualité / non production | **(Doc)** documentation.

| Élément | Rôle Principal | Notes Importantes |
|---------|----------------|-------------------|
| `app.py` **(Critique)** | Coeur backend Flask + initialisation pipeline RAG (chargement données, reconstruction Chroma, endpoints `/ask`, `/health`) | Toute erreur ici bloque le système. Contient la logique de cache & version métadonnées. |
| `Peinture_et_Calligraphie.xlsx` **(Critique)** | Source de vérité produits peinture/calligraphie | Format attendu : 2 lignes à ignorer (`skiprows=2`). Modifier structure ⇒ adapter `clean_artisanat_dataframe`. |
| `Poterie_et_Céramique.xlsx` **(Critique)** | Source de vérité poterie/céramique | Même remarques que ci‑dessus. |
| `df_full.pkl` **(Auto, Perf)** | Cache DataFrame fusionné et enrichi | Peut être supprimé en cas de doute : il sera régénéré. |
| `chroma_db/` **(Auto, Perf)** | Stockage persistant embeddings & métadonnées | Supprimer pour forcer un recalcul complet (`FORCE_REEMBED=1`). Taille potentiellement importante. |
| `templates/index.html` **(Critique UI)** | Page unique (landing + galerie + chatbot) | Modifier pour changer structure UI / ajouter sections. |
| `static/css/style.css` **(Critique UI)** | Styles & identité visuelle (palette, mise en page, animations) | Modifs lourdes possibles sans impacter backend. |
| `static/js/script.js` **(Critique UI)** | Logique frontend (scroll actif, envoi question, protection double submit, indicateur de frappe) | Toute régression peut casser l’expérience chat. |
| `static/images/` **(Doc/UI)** | Assets visuels + exports Mermaid | Le fichier `rag_architecture.mmd` est la source vraie du schéma (préférer éditer ce `.mmd`). |
| `static/images/rag_architecture.mmd` **(Doc)** | Schéma architecture (Mermaid) | Exporter via https://mermaid.live → SVG/PNG. Versionnable, facile à relire. |
| `tests/test_extractors.py` **(Test)** | Vérifie robustesse regex dimensions / prix | Protège contre régressions de parsing. |
| `tests/test_api.py` **(Test)** | Vérifie `/health` et `/ask` (mocks) | Alerte si refacto casse interface externe. |
| `pytest.ini` **(Test)** | Config Pytest (quiet mode + découverte fichiers) | Simplifie `pytest` sans options. |
| `requirements.txt` **(Critique)** | Dépendances projet | Ajouter des versions figées pour production (pinning recommandé). |
| `__init__.py` **(Support)** | Rend le répertoire importable dans les tests | Sans lui, import `app` pouvait échouer en CI. |
| `README.md` **(Doc)** | Documentation vivante | Garder aligné après chaque refacto. |
| `LICENSE` (à créer) **(Doc)** | Licence légale | À ajouter pour clarifier droits d’usage. |

### Résumé Impact
- Pour repartir « propre » : supprimer `df_full.pkl` + `chroma_db/` (recalcul complet au prochain lancement).
- Pour élargir le domaine de connaissance : ajouter lignes aux Excel (ou nouveaux fichiers si code adapté) puis forcer rebuild.
- Pour changer comportement RAG : ajuster prompts / paramètres retriever dans `init_ai` de `app.py`.
- Pour personnaliser UI : intervenir sur `index.html`, `style.css`, `script.js`.

## �🗂️ Schéma de Données (après nettoyage)
Chaque fichier Excel est normalisé vers les colonnes suivantes :
| Colonne | Description |
|---------|------------|
| reference_produit | Identifiant ou référence commerciale |
| nom_produit | Nom lisible du produit |
| categorie | Catégorie (Poterie, Céramique, Peinture, Calligraphie) |
| unite_production | Unité ou artisan / atelier |
| date_fabrication | Date / période (si disponible) |
| labelisation | Oui / Non / statut (minuscule normalisé) |
| nom_label | Nom du label éventuel |
| description | Texte libre nettoyé (espaces compressés) |
| image | Lien ou champ vide |
| dimensions (dérivé) | Extrait via regex (ex: 30x40 cm, 25 cm) |
| price (dérivé) | Extraction optionnelle (ex: 120 Dhs, 45.5 €) |

### Nettoyage (`clean_artisanat_dataframe`)
Étapes :
1. Attribution des noms de colonnes fixes
2. Conversion en chaîne + suppression des tokens placeholders (`nan`, `N/A`, `-`...)
3. Trim des espaces (`Series.str.strip()`)
4. Remplacement des vides par `Non spécifié`
5. Normalisation (capitalisation / minuscule)
6. Compression des espaces multiples dans `description`
7. Enrichissement ultérieur (dimensions, prix) après concaténation des deux jeux

## 🧠 Architecture & Flux RAG
Copier le contenu `.mmd` dans https://mermaid.live puis exporter en SVG/PNG (nom suggéré : `rag_architecture.svg`).

### Rendu Exporté
Image générée (PNG) depuis le fichier Mermaid :

![Architecture RAG Export](./static/images/Artisanat%20Explorer%20RAG%20System%20_%20Mermaid%20Chart-2025-08-20-115604.png)

Astuce : pour un nom de fichier plus simple à versionner, vous pouvez renommer ce PNG en `rag_architecture.png` et mettre à jour le lien ci‑dessus.

### Détails Techniques
- Embeddings : `OllamaEmbeddings(model="mxbai-embed-large")`
- LLM : `Ollama(model="llama3.2:latest", temperature=0.7)`
- Stockage : dossier persistant `./chroma_db`
- Versionnage métadonnées : champ `metadata_version` (`1.0`)
- Reconstruction DataFrame : via `vector_store.get(include=["metadatas"])`
- Cache DataFrame : `df_full.pkl` (mtime + variable `FORCE_RELOAD_DATA`)
- Stratégie de prompt : ciblé produit si nom/référence détecté sinon prompt général strict
- Mémoire : historique par session Flask (`session['chat_history']`)
- Frontend : Bootstrap 5 + logique JS (scroll, active nav, indicateur de frappe, cartes « questions »)

## ⚙️ Technologies
| Couche | Outils |
|--------|--------|
| Frontend | HTML5, CSS3, Bootstrap 5, JS vanilla, Font Awesome |
| Backend | Flask |
| IA / RAG | LangChain, langchain-community, langchain-ollama, ChromaDB |
| Données | pandas, openpyxl |
| Autres | requests, markdown (rendu réponses) |

## 🚀 Démarrage Rapide
### Prérequis
- Python 3.9+ recommandé
- [Ollama](https://ollama.com/) installé et en cours d'exécution

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

# Lancer Ollama (terminal séparé)
ollama serve

# Télécharger les modèles requis (une seule fois)
ollama pull mxbai-embed-large
ollama pull llama3.2:latest

# Exécuter l'application
python app.py
```
Accéder ensuite à: http://localhost:5000

### Variables / Configuration (Environnement)
| Nom | Rôle | Valeur par défaut |
|-----|------|-------------------|
| `FORCE_RELOAD_DATA` | Ignore le pickle et relit les Excel | `0` |
| `FORCE_REEMBED` | Supprime `chroma_db/` et régénère toutes les embeddings | `0` |
| `EMBEDDINGS_MODEL` | Modèle embeddings Ollama | `mxbai-embed-large` |
| `LLM_MODEL` | Modèle LLM Ollama | `llama3.2:latest` |
| `FLASK_SECRET_KEY` | Clé secrète session (remplacer la valeur codée) | (vide) |

Exemple PowerShell :
```powershell
$env:FORCE_REEMBED = "1"          # Regénère le store une fois
$env:EMBEDDINGS_MODEL = "mxbai-embed-large"
$env:LLM_MODEL = "llama3.2:latest"
$env:FLASK_SECRET_KEY = "clef_prod_ultra_secrete"
python app.py
```

Sans variables, l'appli utilise les valeurs par défaut sûres pour développement.

### ▶️ Exécution (Étapes Claires)
1. Lancer le service Ollama (une seule fois) : `ollama serve` (laisser ouvert).
2. (Premier usage) Télécharger les modèles : `ollama pull mxbai-embed-large` puis `ollama pull llama3.2:latest`.
3. Démarrer l'application : `python app.py`.
4. Attendre les logs :
   - `[DataLoad] ...` (lecture / cache DataFrame)
   - `[ChromaDB] ...` (création ou rechargement du store)
   - `QA chain ready.` (pipeline opérationnel)
5. Ouvrir le navigateur : http://localhost:5000
6. Vérifier la santé : http://localhost:5000/health (JSON `{ "ok": true, ... }`).

### Modes de Lancement Alternatifs
- Via Flask CLI (optionnel) :
  - PowerShell : `$env:FLASK_APP='app.py'; flask run --host=0.0.0.0 --port=5000`
- Forcer reconstruction embeddings :
  - `$env:FORCE_REEMBED='1'; python app.py`
- Ignorer le cache pickle et relire Excel :
  - `$env:FORCE_RELOAD_DATA='1'; python app.py`

### Vérifier l'API (Exemples)
PowerShell :
```powershell
Invoke-RestMethod -Uri http://localhost:5000/health -Method Get
Invoke-RestMethod -Uri http://localhost:5000/ask -Method Post -Body '{"question":"Quels produits en Poterie ?"}' -ContentType 'application/json'
```

### Arrêter
`Ctrl + C` dans le terminal où tourne Flask et (si désiré) fermer la fenêtre Ollama.

### Tests Rapides
```powershell
pytest -q           # Tous les tests
pytest tests/test_api.py::test_health_endpoint_ok -q
```

### Production (Aperçu Minimal)
Pour un déploiement local durci :
- Exporter `FLASK_SECRET_KEY`.
- Lancer sous un serveur WSGI (ex: `waitress` sous Windows) :
  ```powershell
  pip install waitress
  python -m waitress --listen=0.0.0.0:5000 app:app
  ```
*(Optionnel) Ajouter un reverse proxy Nginx pour TLS / compression.*

### Temps de Démarrage – À Savoir
- Premier run : le calcul des embeddings peut prendre plusieurs minutes selon la taille (une fois persisté c'est immédiat).
- Runs suivants : reconstruction DataFrame depuis métadonnées → rapide (quelques secondes).

### Nettoyage Complet (Full Reset)
```powershell
Remove-Item -Recurse -Force chroma_db
Remove-Item df_full.pkl
$env:FORCE_REEMBED='1'
python app.py
```
*(Supprime le store et le cache → reconstruction complète.)*

### Stratégie de Cache & Rebuild
1. Au démarrage `init_ai` vérifie la présence du dossier `chroma_db`.
2. Si présent : reconstruit le DataFrame depuis les métadonnées (rapide) et vérifie `metadata_version`.
3. Si version différente ou `FORCE_REEMBED=1` : supprime le dossier et regénère embeddings depuis Excel.
4. Pour les données tabulaires : si `df_full.pkl` existe et plus récent que les Excel, il est réutilisé (sinon relecture Excel + enrichissement + nouvel enregistrement pickle).

## 🔌 Endpoints API
| Méthode | Route | Description | Corps JSON Exemple |
|---------|-------|-------------|--------------------|
| GET | `/health` | Statut système (ok, records, store_loaded, metadata_version) | (aucun) |
| POST | `/ask` | Question au chatbot (RAG) | `{ "question": "Quels produits en Poterie ?" }` |

### Exemple (PowerShell)
```powershell
Invoke-RestMethod -Uri http://localhost:5000/ask -Method Post -Body '{"question":"Liste des produits en céramique"}' -ContentType 'application/json'
```

## 🧪 Logique Clef du Code
- Vérification de la disponibilité d'Ollama (`/api/tags`)
- Chargement + nettoyage + fusion des deux Excel
- Cache DataFrame pickle + invalidation mtime
- Extraction regex dimensions: `(\d+[×x]\d+\s?cm)|(\d+\s?cm)`
- Extraction prix: `(\d+[\.,]\d+)\s?(€|\$|Dhs)`
- Construction documents texte multi‑ligne (un par produit) + métadonnées versionnées
- Initialisation / rechargement Chroma persist (reconstruction DataFrame depuis métadonnées)
- Chaîne `RetrievalQA` (`chain_type="stuff"`, k=5)
- Session historique adaptant le prompt (produit ciblé vs général)
- Conversion Markdown → HTML (lib `markdown`)

## 🩺 Dépannage & Erreurs Courantes
| Problème | Cause probable | Solution |
|----------|----------------|----------|
| `Ollama connection failed` | Service non démarré | Lancer `ollama serve` puis relancer l'app |
| Aucune donnée chargée | Format Excel modifié (lignes d'en‑tête) | Vérifier `skiprows=2` ou ajuster |
| Temps long premier démarrage | Génération embeddings | Patience, puis réutilisation persist |
| Réponses hors sujet | Prompt général trop permissif | Ajuster consignes dans `init_ai` / section prompt |
| Accents cassés en console | Encodage terminal Windows | `chcp 65001` avant exécution |

## 🔒 Sécurité (État & Pistes)
Statut actuel :
- `app.secret_key` est codée en dur (à remplacer par la variable d'env `FLASK_SECRET_KEY`).
- Rendu Markdown → HTML (bibliothèque `markdown`) sans nettoyage HTML avancé.

Recommandé court terme :
1. Définir `FLASK_SECRET_KEY` en production et supprimer la valeur codée.  
2. Ajouter une limite de longueur (ex: 500 caractères) sur `question`.  
3. Ajouter un nettoyage HTML (ex: `bleach.clean`) après conversion Markdown.

Améliorations futures : rate limiting (Flask-Limiter), journalisation structurée, endpoint `/metrics`, validation stricte entrée.

## 🚧 Améliorations Futures (Suggestions)
- Passage à un modèle d'inférence quantisé plus léger pour machines modestes
- Retrieval amélioré : MMR, reranking, hybrid BM25 + vecteurs
- Export CSV / JSON des résultats
- Interface upload dynamique de nouveaux produits (rebuild embeddings incrémental)
- Pagination & filtrage avancé dans la galerie
- Internationalisation (FR / EN)
- Authentification artisan/admin + rôles
- Tests supplémentaires (prompt shaping, fallback errors)

## 🧪 Tests
Des tests Pytest couvrent :
- Extracteurs regex (`tests/test_extractors.py`)
- Endpoints `/health` et `/ask` via mocks (`tests/test_api.py`)

Note : `__init__.py` + ajout dynamique de `sys.path` dans les tests assurent `import app` même hors contexte package formel.

Exécution :
```powershell
pytest -q
```

Ajouter d'autres tests (questions vides, système non initialisé, reconstruction métadonnées, erreurs Ollama).

## 👥 Équipe
Étudiants ISDIA – ENSA Fès :

| Membre | Contact |
|--------|---------|
| **John Muhammed** | [LinkedIn](https://www.linkedin.com/in/Maha-Jr/) \| [GitHub](https://github.com/Maha-Jr10) |
| **Ibnyassine Aya** | [LinkedIn](https://www.linkedin.com/in/aya-ibnyassine-80b017292) \| [GitHub](https://github.com/Aya-Ibnyassine) |
| **Berrahioui Hajar** | [LinkedIn](https://www.linkedin.com/in/hajar-berrahioui-03a2332b2?utm_source=share&utm_campaign=share_via&utm_content=profile&utm_medium=android_app) \| [GitHub](https://github.com/hajarbberrahioui) |

## 📄 Licence
La mention de licence MIT apparaît mais aucun fichier `LICENSE` n'est présent. Ajoutez un fichier `LICENSE` (MIT ou autre) ou adaptez cette section.

---
Faites une issue / pull request pour toute amélioration ou correction. Bonne exploration !
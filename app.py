from flask import Flask, render_template, request, jsonify, session, redirect, url_for, make_response
import pandas as pd
import os, re, warnings, requests, pickle
from urllib.parse import urlparse
# Optional markdown dependency
try:
    import markdown as md_lib
except Exception:
    md_lib = None

# Optional LangChain/Ollama stack (backend can run without it)
try:
    from langchain_community.vectorstores import Chroma
    from langchain_ollama import OllamaEmbeddings
    from langchain_community.llms import Ollama
    from langchain.chains import RetrievalQA
    HAS_LLM = True
except Exception:
    Chroma = OllamaEmbeddings = Ollama = RetrievalQA = None
    HAS_LLM = False
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics.pairwise import cosine_similarity

warnings.filterwarnings("ignore")

app = Flask(__name__)
app.secret_key = "artisanat_explorer_secret_key"

# --- ML Artifacts (initialized lazily) ---
ml_artifacts = {
    'initialized': False,
    'vectorizer': None,
    'tfidf_matrix': None,
    'kmeans': None,
    'clusters': None,
    'index_by_ref': {},
    'category_model': None,
    'label_model': None,
}

def _json_safe_record(record: dict) -> dict:
    """Convert pandas/NumPy NaN/NaT to None for JSON safety."""
    safe = {}
    for k, v in record.items():
        try:
            if pd.isna(v):
                safe[k] = None
            else:
                safe[k] = v
        except Exception:
            safe[k] = v
    return safe

def initialize_ml():
    """Prepare TF-IDF, KMeans clusters, and simple classifiers for demo predictions."""
    global df_full, ml_artifacts
    if df_full is None or df_full.empty:
        df_full = load_artisanat_data()
    df = df_full.copy()
    if df.empty:
        return
    # Ensure numeric year
    if 'annee' in df.columns:
        df['annee'] = pd.to_numeric(df['annee'], errors='coerce')
    # Prepare text
    texts = (df['nom_produit'].fillna('') + ' ' + df['description'].fillna('')).astype(str).tolist()
    # TF-IDF
    vectorizer = TfidfVectorizer(max_features=1000, min_df=2, max_df=0.8)
    try:
        tfidf_matrix = vectorizer.fit_transform(texts)
    except ValueError:
        # Fallback for very small datasets
        vectorizer = TfidfVectorizer(max_features=200)
        tfidf_matrix = vectorizer.fit_transform(texts)
    # KMeans clustering
    n_samples = tfidf_matrix.shape[0]
    n_clusters = max(2, min(5, n_samples // 20 or 2))
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(tfidf_matrix)
    df_full['cluster'] = clusters
    # Build index by reference
    index_by_ref = {}
    for idx, ref in enumerate(df['reference_produit'].fillna('').tolist()):
        index_by_ref[ref] = idx
    # Category prediction model (predict category_par_group)
    y_cat = df['category_par_group'].fillna('Unknown') if 'category_par_group' in df.columns else df['categorie'].fillna('Unknown')
    X_cat = df[['description', 'unite_production', 'annee']].copy()
    preprocessor_cat = ColumnTransformer(
        transformers=[
            ('text', TfidfVectorizer(max_features=500), 'description'),
            ('year', Pipeline([
                ('imputer', SimpleImputer(strategy='median')),
                ('scaler', StandardScaler())
            ]), ['annee']),
            ('prod', Pipeline([
                ('imputer', SimpleImputer(strategy='constant', fill_value='Unknown')),
                ('onehot', OneHotEncoder(handle_unknown='ignore'))
            ]), ['unite_production'])
        ]
    )
    cat_model = Pipeline([
        ('prep', preprocessor_cat),
        ('clf', RandomForestClassifier(n_estimators=200, random_state=42, class_weight='balanced'))
    ])
    try:
        cat_model.fit(X_cat, y_cat)
    except Exception:
        cat_model = None
    # Label prediction model (predict labelisation oui/non)
    y_lab = (df['labelisation'].fillna('').str.lower() == 'oui').astype(int) if 'labelisation' in df.columns else pd.Series([0]*len(df))
    X_lab = df[['description', 'categorie', 'unite_production', 'annee']].copy()
    preprocessor_lab = ColumnTransformer(
        transformers=[
            ('text', TfidfVectorizer(max_features=500), 'description'),
            ('cat', Pipeline([
                ('imputer', SimpleImputer(strategy='constant', fill_value='Unknown')),
                ('onehot', OneHotEncoder(handle_unknown='ignore'))
            ]), ['categorie', 'unite_production']),
            ('year', Pipeline([
                ('imputer', SimpleImputer(strategy='median')),
                ('scaler', StandardScaler())
            ]), ['annee'])
        ]
    )
    lab_model = Pipeline([
        ('prep', preprocessor_lab),
        ('clf', RandomForestClassifier(n_estimators=200, random_state=42, class_weight='balanced'))
    ])
    try:
        # Only train if both classes present
        if y_lab.nunique() > 1:
            lab_model.fit(X_lab, y_lab)
        else:
            lab_model = None
    except Exception:
        lab_model = None
    ml_artifacts.update({
        'initialized': True,
        'vectorizer': vectorizer,
        'tfidf_matrix': tfidf_matrix,
        'kmeans': kmeans,
        'clusters': clusters,
        'index_by_ref': index_by_ref,
        'category_model': cat_model,
        'label_model': lab_model,
    })

# --- Products Page & API ---
@app.route('/products')
def products_page():
    return render_template('products.html')

@app.route('/api/products')
def api_products():
    global df_full
    if df_full is None or df_full.empty:
        df_full = load_artisanat_data()
    # Get query params
    search = request.args.get('search', '').strip().lower()
    category = request.args.get('category', '').strip().lower()
    cluster_param = request.args.get('cluster', '').strip()
    unit_param = request.args.get('unit', '').strip().lower()
    df = df_full.copy()
    # Ensure ML artifacts (clusters) ready
    if 'cluster' not in df.columns or df['cluster'].isna().all():
        try:
            initialize_ml()
            df = df_full.copy()
        except Exception:
            pass
    # Determine category group column
    group_col = 'category_par_group' if 'category_par_group' in df.columns else (
        'Category_par_Group' if 'Category_par_Group' in df.columns else None
    )
    # Filter by category GROUP (request param name kept as 'category' for backward compatibility)
    if category and group_col is not None and group_col in df.columns:
        # Some entries may be non-string; coerce to str
        df = df[df[group_col].astype(str).str.lower() == category]
    # Filter by unite_production (user friendly)
    if unit_param:
        df = df[df['unite_production'].astype(str).str.lower() == unit_param]
    # Filter by cluster (kept for backward compatibility)
    if cluster_param:
        try:
            cluster_val = int(cluster_param)
            df = df[df['cluster'] == cluster_val]
        except ValueError:
            pass
    # Search by product name or description
    if search:
        df = df[df['nom_produit'].str.lower().str.contains(search) | df['description'].str.lower().str.contains(search)]
    # Get unique category GROUPS for filter dropdown (still returned under key 'categories' for UI)
    if group_col is not None and group_col in df_full.columns:
        categories = sorted(pd.Series(df_full[group_col]).dropna().astype(str).unique())
    else:
        categories = sorted(pd.Series(df_full['categorie']).dropna().astype(str).unique())
    units_list = sorted(pd.Series(df_full['unite_production']).dropna().astype(str).unique().tolist())
    # Convert to dict for JSON
    products = df.fillna('').to_dict(orient='records')
    return jsonify({'products': products, 'categories': categories, 'units': units_list})

# --- Analytics Page & Data Routes (placed after app init) ---
@app.route('/analytics')
def analytics_page():
    return render_template('analytics.html')

@app.route('/api/analytics')
def api_analytics():
    global df_full
    if df_full is None or df_full.empty:
        df_full = load_artisanat_data()
    df = df_full.copy()
    # Category distribution
    category_counts = df['categorie'].value_counts().sort_index()
    # Category group distribution
    group_col = 'category_par_group' if 'category_par_group' in df.columns else 'Category_par_Group'
    category_group_counts = df[group_col].value_counts().sort_index()
    # Labeling status
    label_col = 'labelisation' if 'labelisation' in df.columns else 'Labelisation'
    label_counts = df[label_col].value_counts().sort_index()
    # Yearly production
    year_col = 'annee' if 'annee' in df.columns else 'Annee'
    year_counts = df[year_col].dropna().astype(int).value_counts().sort_index()
    # Stacked area: year x category group
    pivot = df.dropna(subset=[year_col])
    pivot[year_col] = pivot[year_col].astype(int)
    stacked = pivot.pivot_table(index=year_col, columns=group_col, values='reference_produit', aggfunc='count', fill_value=0)
    # Handmade vs non-handmade over time
    handmade_col = 'fait_par_main'
    handmade_time = pivot.pivot_table(index=year_col, columns=handmade_col, values='reference_produit', aggfunc='count', fill_value=0)
    # Price by category group
    price_col = 'price' if 'price' in df.columns else 'Prix_Estime'
    try:
        df[price_col] = pd.to_numeric(df[price_col], errors='coerce')
    except Exception:
        pass
    price_by_group = df.groupby(group_col)[price_col].mean().dropna()
    return jsonify({
        'category_counts': category_counts.to_dict(),
        'category_group_counts': category_group_counts.to_dict(),
        'label_counts': label_counts.to_dict(),
        'year_counts': year_counts.to_dict(),
        'stacked_area': {
            'years': list(stacked.index),
            'groups': list(stacked.columns),
            'values': stacked.values.tolist()
        },
        'handmade_time': {
            'years': list(handmade_time.index),
            'types': list(handmade_time.columns),
            'values': handmade_time.values.tolist()
        },
        'price_by_group': price_by_group.to_dict()
    })

# --- Clustering & Recommendations Endpoints ---
@app.route('/api/clusters')
def api_clusters():
    if not ml_artifacts['initialized']:
        initialize_ml()
    clusters = ml_artifacts.get('clusters')
    if clusters is None:
        return jsonify({'counts': {}, 'n_clusters': 0})
    # counts per cluster
    counts = pd.Series(clusters).value_counts().sort_index().to_dict()
    return jsonify({'counts': counts, 'n_clusters': int(len(set(clusters)))})

@app.route('/api/recommendations')
def api_recommendations():
    ref = request.args.get('reference')
    # Default to 3 and cap to 3 to always return the three most related
    k = int(request.args.get('k', 3))
    k = min(max(k, 1), 3)
    if not ref:
        return jsonify({'error': 'reference query param required'}), 400
    if not ml_artifacts['initialized']:
        initialize_ml()
    idx_map = ml_artifacts.get('index_by_ref', {})
    if ref not in idx_map:
        return jsonify({'error': 'reference not found'}), 404
    idx = idx_map[ref]
    tfidf_matrix = ml_artifacts['tfidf_matrix']
    sims = cosine_similarity(tfidf_matrix[idx], tfidf_matrix).flatten()
    # get top k excluding self
    top_idx = sims.argsort()[::-1]
    top_idx = [i for i in top_idx if i != idx][:k]
    recs = []
    for i in top_idx:
        row = _json_safe_record(df_full.iloc[i].to_dict())
        row['similarity'] = float(sims[i])
        recs.append(row)
    return jsonify({'reference': ref, 'recommendations': recs})

# --- Prediction Endpoints ---
@app.route('/api/predict_category', methods=['POST'])
def api_predict_category():
    if not ml_artifacts['initialized']:
        initialize_ml()
    model = ml_artifacts.get('category_model')
    if model is None:
        return jsonify({'error': 'category model unavailable'}), 500
    data = request.get_json() or {}
    payload = {
        'description': data.get('description', ''),
        'unite_production': data.get('unite_production', 'Unknown'),
        'annee': data.get('annee', None)
    }
    X = pd.DataFrame([payload])
    try:
        pred = model.predict(X)[0]
        proba = None
        if hasattr(model.named_steps['clf'], 'predict_proba'):
            probs = model.predict_proba(X)
            proba = float(probs.max())
        return jsonify({'predicted': str(pred), 'confidence': proba})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/predict_label', methods=['POST'])
def api_predict_label():
    if not ml_artifacts['initialized']:
        initialize_ml()
    model = ml_artifacts.get('label_model')
    if model is None:
        return jsonify({'error': 'label model unavailable'}), 500
    data = request.get_json() or {}
    payload = {
        'description': data.get('description', ''),
        'categorie': data.get('categorie', 'Unknown'),
        'unite_production': data.get('unite_production', 'Unknown'),
        'annee': data.get('annee', None)
    }
    X = pd.DataFrame([payload])
    try:
        pred = int(model.predict(X)[0])
        proba = None
        if hasattr(model.named_steps['clf'], 'predict_proba'):
            probs = model.predict_proba(X)
            proba = float(probs[:, 1][0])
        return jsonify({'predicted': 'oui' if pred == 1 else 'non', 'probability': proba})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Versioning for stored metadata in Chroma
METADATA_VERSION = "3.0"

# Globals initialized to None
vector_store = None
df_full = None
embeddings = None

def check_ollama_connection() -> bool:
    """Check if Ollama server is running and reachable."""
    if not HAS_LLM:
        print("[LLM] LangChain/Ollama not installed. Skipping LLM initialization.")
        return False
    try:
        response = requests.get('http://localhost:11434/api/tags', timeout=10)
        if response.status_code == 200:
            print("✅ Ollama connection successful")
            return True
        print(f"❌ Ollama connection failed: Status {response.status_code}")
    except Exception as e:
        print(f"❌ Ollama connection failed: {str(e)}")
        print("Please make sure Ollama is running. You can start it with 'ollama serve'")
    return False

DATA_CACHE_PATH = "df_full.pkl"
# Use the pre-cleaned CSV located in the current project directory
CSV_FILE = os.path.join(os.path.dirname(__file__), "cleaned_artisanal_products.csv")

def _csv_file_mtime() -> float:
    if os.path.exists(CSV_FILE):
        return os.path.getmtime(CSV_FILE)
    return 0.0

def load_artisanat_data(use_cache: bool = True) -> pd.DataFrame:
    """Load pre-cleaned dataset from CSV with optional pickle cache (df_full.pkl).

    Cache invalidated if:
      - FORCE_RELOAD_DATA env var set
      - Cache file missing
      - Source CSV newer than cache
    """
    force_reload = os.getenv("FORCE_RELOAD_DATA", "0") in {"1", "true", "True"}
    try:
        if use_cache and not force_reload and os.path.exists(DATA_CACHE_PATH):
            cache_mtime = os.path.getmtime(DATA_CACHE_PATH)
            if cache_mtime >= _csv_file_mtime():
                try:
                    with open(DATA_CACHE_PATH, 'rb') as fh:
                        cached = pickle.load(fh)
                    if isinstance(cached, pd.DataFrame) and not cached.empty:
                        print(f"[DataCache] Using cached DataFrame ({len(cached)} rows)")
                        return cached
                except Exception as ce:
                    print(f"[DataCache] Failed to load cache, rebuilding. Reason: {ce}")

        if not os.path.exists(CSV_FILE):
            raise FileNotFoundError(f"CSV source not found at {CSV_FILE}")

        print("[DataLoad] Loading pre-cleaned CSV ...")
        src = pd.read_csv(CSV_FILE)

        # Map CSV columns to internal schema expected by the app
        rename_map = {
            'Reference': 'reference_produit',
            'Nom_Produit': 'nom_produit',
            'Categorie': 'categorie',
            'Unite_Production': 'unite_production',
            'Date_Fabrication': 'date_fabrication',
            'Labelisation': 'labelisation',
            'Nom_Label': 'nom_label',
            'Description': 'description',
            'Image': 'image',
            # Use provided price estimate directly from CSV
            'Prix_Estime': 'price',
            'Lien_Image': 'lien_image',
            'Annee': 'annee',
            'Image_Disponible': 'image_disponible',
            'fait_par_main': 'fait_par_main',
            'Category_par_Group': 'category_par_group',
        }
        df = src.rename(columns=rename_map)

        # Ensure required columns exist (no extra feature engineering here)
        required = list(rename_map.values())
        # Also ensure optional fields used by prompts exist
        if 'dimensions' not in df.columns:
            df['dimensions'] = "Non spécifié"
        for col in required:
            if col not in df.columns:
                df[col] = "Non spécifié"

        print(f"[DataLoad] Loaded dataset: {df.shape[0]} records")

        # Persist cache
        if use_cache:
            try:
                with open(DATA_CACHE_PATH, 'wb') as fh:
                    pickle.dump(df, fh)
                print(f"[DataCache] Saved to {DATA_CACHE_PATH}")
            except Exception as se:
                print(f"[DataCache] Save failed (non-blocking): {se}")
        return df
    except Exception as e:
        print(f"Error loading data: {str(e)}")
        import traceback; traceback.print_exc()
        return pd.DataFrame()

def clean_artisanat_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize raw Excel into clean schema."""
    df.columns = [
        "reference_produit","nom_produit","categorie","unite_production",
        "date_fabrication","labelisation","nom_label","description","image"
    ]
    # Normalize all columns: cast to string, strip spaces, replace placeholder missing tokens
    placeholders = {'nan': '', 'N/A': '', 'NaN': '', '-': ''}
    for col in df.columns:
        col_series = df[col].astype(str)
        # Replace known placeholder tokens (case insensitive for variants like 'nan')
        col_series = col_series.replace(placeholders)
        # Strip whitespace on each string value
        col_series = col_series.str.strip()
        # Standardize empty strings to a unified missing label
        col_series = col_series.replace('', 'Non spécifié')
        df[col] = col_series
    df['categorie'] = df['categorie'].str.capitalize()
    df['labelisation'] = df['labelisation'].str.lower()
    df['nom_label'] = df['nom_label'].str.capitalize()
    df['description'] = df['description'].str.replace(r'\s+',' ', regex=True)
    df['image'] = df['image'].replace({'Non spécifié': ''})
    return df

def extract_dimensions(desc: str) -> str:
    if not isinstance(desc, str):
        return "Non spécifié"
    matches = re.findall(r'(\d+[×x]\d+\s?cm)|(\d+\s?cm)', desc)
    if matches:
        return ', '.join([dim[0] or dim[1] for dim in matches if any(dim)])
    return "Non spécifié"

def extract_price(desc: str) -> str:
    if not isinstance(desc, str):
        return "Non spécifié"
    match = re.search(r'(\d+[\.,]\d+)\s?(€|\$|Dhs)', desc)
    if match:
        return f"{match.group(1)} {match.group(2)}"
    return "Non spécifié"

def init_ai():
    """Initialize embeddings/LLM + load or build Chroma store with row metadata.

    Steps:
      - If FORCE_REEMBED -> delete existing store
      - If store exists -> try reconstruct df from metadata (checks version)
      - Else -> read Excel, clean, build embeddings with metadata_version
    """
    import traceback, shutil
    global vector_store, df_full, embeddings
    if not HAS_LLM:
        print("[LLM] Dependencies missing; QA system disabled.")
        return None

    def build_docs_and_metadata(df: pd.DataFrame):
        texts, metas = [], []
        for _, row in df.iterrows():
            md = {
                'reference_produit': row.get('reference_produit', ''),
                'nom_produit': row.get('nom_produit', ''),
                'categorie': row.get('categorie', ''),
                'unite_production': row.get('unite_production', ''),
                'date_fabrication': row.get('date_fabrication', ''),
                'labelisation': row.get('labelisation', ''),
                'nom_label': row.get('nom_label', ''),
                'dimensions': row.get('dimensions', ''),
                'price': row.get('price', ''),
                'description': row.get('description', ''),
                'image': row.get('image', ''),
                'lien_image': row.get('lien_image', ''),
                'annee': row.get('annee', ''),
                'image_disponible': row.get('image_disponible', ''),
                'fait_par_main': row.get('fait_par_main', ''),
                'category_par_group': row.get('category_par_group', ''),
                'metadata_version': METADATA_VERSION
            }
            text = (f"PRODUIT: {md['nom_produit']}\n"
                    f"RÉFÉRENCE: {md['reference_produit']}\n"
                    f"CATÉGORIE: {md['categorie']}\n"
                    f"UNITÉ DE PRODUCTION: {md['unite_production']}\n"
                    f"DATE DE FABRICATION: {md['date_fabrication']}\n"
                    f"LABELISATION: {md['labelisation']}\n"
                    f"NOM DU LABEL: {md['nom_label']}\n"
                    f"DIMENSIONS: {md['dimensions']}\n"
                    f"PRIX: {md['price']}\n"
                    f"DESCRIPTION: {md['description']}\n"
                    f"IMAGE: {md['image']}\n"
                    f"LIEN IMAGE: {md['lien_image']}\n"
                    f"ANNÉE: {md['annee']}\n"
                    f"IMAGE DISPONIBLE: {md['image_disponible']}\n"
                    f"FAIT PAR MAIN: {md['fait_par_main']}\n"
                    f"CATÉGORIE (GROUPE): {md['category_par_group']}")
            texts.append(text)
            metas.append(md)
        return texts, metas

    try:
        if not check_ollama_connection():
            return None

        persist_directory = "chroma_db"
        embeddings_model = os.getenv("EMBEDDINGS_MODEL", "mxbai-embed-large")
        llm_model = os.getenv("LLM_MODEL", "llama3.2:latest")
        embeddings = OllamaEmbeddings(model=embeddings_model)
        store_exists = os.path.exists(persist_directory) and len(os.listdir(persist_directory)) > 0

        if os.getenv("FORCE_REEMBED", "0") in {"1","true","True"} and store_exists:
            print("[ChromaDB] FORCE_REEMBED active -> deleting existing store")
            shutil.rmtree(persist_directory, ignore_errors=True)
            store_exists = False

        if store_exists:
            print("[ChromaDB] Existing store found. Loading...")
            vector_store = Chroma(persist_directory=persist_directory, embedding_function=embeddings)
            raw = vector_store.get(include=["metadatas"])
            metas = raw.get('metadatas', []) if raw else []
            if metas and isinstance(metas, list) and 'nom_produit' in metas[0]:
                version = metas[0].get('metadata_version')
                if version != METADATA_VERSION:
                    print(f"[ChromaDB] Metadata version {version} != {METADATA_VERSION}. Rebuilding...")
                    df_full = load_artisanat_data()
                    texts, metas_new = build_docs_and_metadata(df_full)
                    shutil.rmtree(persist_directory, ignore_errors=True)
                    os.makedirs(persist_directory, exist_ok=True)
                    vector_store = Chroma.from_texts(texts, embedding=embeddings, persist_directory=persist_directory, metadatas=metas_new)
                    vector_store.persist()  # to save
                    print("[ChromaDB] Rebuilt with updated metadata version")
                else:
                    df_recon = pd.DataFrame(metas)
                    # Do not perform feature engineering; ensure required fields exist
                    defaults = {
                        'dimensions': "Non spécifié",
                        'price': "Non spécifié",
                        'image': "Non spécifié",
                        'lien_image': "Non spécifié",
                        'annee': "Non spécifié",
                        'image_disponible': "Non spécifié",
                        'fait_par_main': "Non spécifié",
                        'category_par_group': "Non spécifié",
                    }
                    for k, v in defaults.items():
                        if k not in df_recon:
                            df_recon[k] = v
                    df_full = df_recon.reset_index(drop=True)
                    print(f"[ChromaDB] Reconstructed DataFrame ({len(df_full)} rows, metadata v{version})")
            else:
                print("[ChromaDB] Missing metadata; loading Excel sources...")
                df_full = load_artisanat_data()
        else:
            print("[ChromaDB] No store found. Building new embeddings...")
            df_full = load_artisanat_data()
            if df_full.empty:
                print("[ERROR] No data loaded from Excel.")
                return None
            texts, metas = build_docs_and_metadata(df_full)
            os.makedirs(persist_directory, exist_ok=True)
            vector_store = Chroma.from_texts(texts, embedding=embeddings, persist_directory=persist_directory, metadatas=metas)
            vector_store.persist(); print("[ChromaDB] Persisted new store.")

        if df_full is None or df_full.empty:
            print("[ERROR] DataFrame unavailable after initialization.")
            return None

        print(f"Successfully prepared dataset: {len(df_full)} records")
        llm = Ollama(model=llm_model, temperature=0.7)
        qa_chain = RetrievalQA.from_chain_type(
            llm,
            retriever=vector_store.as_retriever(search_kwargs={'k':5}),
            chain_type="stuff"
        )
        print("QA chain ready.")
        return qa_chain
    except Exception:
        print("[ERROR] init_ai failure")
        traceback.print_exc()
        return None

# --- ChromaDB check/creation before app startup ---

def ensure_chromadb():
    import traceback
    persist_directory = "chroma_db"
    if not HAS_LLM:
        print("[LLM] Skipping ChromaDB initialization (LLM stack unavailable).")
        return None
    if not os.path.exists(persist_directory) or len(os.listdir(persist_directory)) == 0:
        print("[ChromaDB] No existing store, building now...")
        result = init_ai()
        if result is None:
            print("[WARN] Could not build ChromaDB. Proceeding without QA system.")
            traceback.print_exc()
            return None
        print("[ChromaDB] Store created.")
        return result
    else:
        print("[ChromaDB] Existing store detected. Loading QA chain...")
        return init_ai()

qa_system = None  # Will be initialized only when running the app directly

# Routes
@app.route('/')
def home():
    return render_template('index.html')

# --- Simple image proxy to mitigate hotlinking/CORS and broken links ---
@app.route('/img')
def img_proxy():
    url = request.args.get('url', '').strip()
    if not url or not (url.startswith('http://') or url.startswith('https://')):
        return redirect(url_for('static', filename='images/img_unavailable.svg'))
    try:
        # Many hosts block hotlinking based on Referer. Mimic a first-party request by
        # sending a Referer matching the image origin and a common Accept header.
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36',
            'Referer': origin,
            'Accept': 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8'
        }
        resp = requests.get(url, headers=headers, timeout=(5, 15))
        if resp.status_code != 200 or not resp.content:
            return redirect(url_for('static', filename='images/img_unavailable.svg'))
        content_type = resp.headers.get('Content-Type', 'image/jpeg')
        out = make_response(resp.content)
        out.headers['Content-Type'] = content_type
        out.headers['Cache-Control'] = 'public, max-age=86400'
        return out
    except Exception:
        return redirect(url_for('static', filename='images/img_unavailable.svg'))

@app.route('/health')
def health():
    status = {
        'ok': bool(qa_system),
        'records': 0 if df_full is None else len(df_full),
        'store_loaded': vector_store is not None,
        'metadata_version': METADATA_VERSION,
    }
    code = 200 if status['ok'] else 500
    return jsonify(status), code


@app.route('/ask', methods=['POST'])
def ask():
    if not qa_system:
        return jsonify({"response": "Système de QA non initialisé (LLM non disponible)."})

    data = request.get_json()
    if not data or 'question' not in data:
        return jsonify({"response": "Requête invalide"})

    question = data['question'].strip()
    if not question:
        return jsonify({"response": "Veuillez poser une question"})

    try:
        # Récupérer ou initialiser l'historique de chat pour la session
        chat_history = session.get("chat_history", [])
        # Ajouter la nouvelle question à l'historique
        chat_history.append({"role": "user", "content": question})

        # Construire le prompt avec l'historique
        history_prompt = ""
        for msg in chat_history:
            if msg["role"] == "user":
                history_prompt += f"Utilisateur: {msg['content']}\n"
            elif msg["role"] == "assistant":
                history_prompt += f"Assistant: {msg['content']}\n"

        # Détection d'une question sur un produit précis (par nom ou référence)
        produit_cible = None
        for prod in df_full.itertuples():
            if prod.nom_produit.lower() in question.lower() or prod.reference_produit.lower() in question.lower():
                produit_cible = prod
                break

        if produit_cible:
            # Prompt spécifique pour un produit (inclut tous les champs disponibles)
            prompt = f"""
                CONTEXTE :
                Tu es un assistant expert de l’artisanat marocain.
                Réponds uniquement à propos du produit suivant :
                NOM : {produit_cible.nom_produit}
                RÉFÉRENCE : {produit_cible.reference_produit}
                CATÉGORIE : {produit_cible.categorie}
                UNITÉ DE PRODUCTION : {produit_cible.unite_production}
                DATE DE FABRICATION : {produit_cible.date_fabrication}
                LABELISATION : {produit_cible.labelisation}
                NOM DU LABEL : {produit_cible.nom_label}
                DESCRIPTION : {produit_cible.description}
                PRIX : {produit_cible.price}
                DIMENSIONS : {getattr(produit_cible, 'dimensions', 'Non spécifié')}
                IMAGE : {getattr(produit_cible, 'image', 'Non spécifié')}
                LIEN IMAGE : {getattr(produit_cible, 'lien_image', 'Non spécifié')}
                ANNÉE : {getattr(produit_cible, 'annee', 'Non spécifié')}
                IMAGE DISPONIBLE : {getattr(produit_cible, 'image_disponible', 'Non spécifié')}
                FAIT PAR MAIN : {getattr(produit_cible, 'fait_par_main', 'Non spécifié')}
                CATÉGORIE (GROUPE) : {getattr(produit_cible, 'category_par_group', 'Non spécifié')}

                Question de l'utilisateur : {question}
                Réponds uniquement avec les informations de ce produit. Si l'information n'existe pas, indique : "Information non disponible".
            """
            prompt = prompt + "\n" + history_prompt + "Assistant:"
        else:
            # Prompt général
            prompt = f"""
                CONTEXTE :  
                Tu es un assistant virtuel pour touristes, spécialisé dans l’artisanat marocain.  
                Tu as accès à la base de données handiCaraft, collectée par l’équipe d’étudiants en Data Science & IA à l’ENSA Fès, qui contient des informations détaillées sur les produits suivants : peinture, calligraphie, poterie, céramique.

                CONSIGNES :
                - Avant de répondre, analyse l’ensemble de la base de données pour trouver toutes les informations pertinentes à la question.
                - Réponds uniquement si la question concerne ces produits.
                - Ne donne que les informations strictement demandées dans la question. N’ajoute aucun détail supplémentaire, aucune généralité, aucune supposition, ni contenu vague.
                - Si la question demande une liste, affiche chaque élément sur une nouvelle ligne (une ligne par produit ou élément).
                - Si la réponse n’existe pas dans la base, indique : "Information non disponible".

            """
            prompt = prompt + "\n" + history_prompt + "Assistant:"

        response = qa_system.invoke(prompt)["result"]

        # Post-traitement pour renforcer la concision
        cleaned_response = re.sub(r'\n{2,}', '\n\n', response)  # Supprime les sauts de ligne excessifs
        cleaned_response = re.sub(r'\s{2,}', ' ', cleaned_response)  # Supprime les espaces multiples

        # Ajouter la réponse de l'assistant à l'historique
        chat_history.append({"role": "assistant", "content": cleaned_response})
        session["chat_history"] = chat_history

        # Convertir la réponse en HTML
        if md_lib:
            html_response = md_lib.markdown(cleaned_response, extensions=['extra'])
        else:
            # Fallback: minimalist HTML
            html_response = f"<pre>{cleaned_response}</pre>"

        return jsonify({"response": html_response})

    except Exception as e:
        return jsonify({"response": f"Erreur: {str(e)}"})


if __name__ == '__main__':
    print("Starting AI initialization...")
    qa_system = ensure_chromadb()
    app.run(host='0.0.0.0', port=5000, debug=True)

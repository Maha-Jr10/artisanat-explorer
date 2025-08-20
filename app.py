from flask import Flask, render_template, request, jsonify, session
import pandas as pd
import os, re, warnings, requests, markdown, pickle
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_community.llms import Ollama
from langchain.chains import RetrievalQA

warnings.filterwarnings("ignore")

app = Flask(__name__)
app.secret_key = "artisanat_explorer_secret_key"

# Versioning for stored metadata in Chroma
METADATA_VERSION = "1.0"

# Globals initialized to None
vector_store = None
df_full = None
embeddings = None

def check_ollama_connection() -> bool:
    """Check if Ollama server is running and reachable."""
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
EXCEL_FILES = [
    "Peinture_et_Calligraphie.xlsx",
    "Poterie_et_Céramique.xlsx"
]

def _excel_files_mtime() -> float:
    times = []
    for f in EXCEL_FILES:
        if os.path.exists(f):
            times.append(os.path.getmtime(f))
    return max(times) if times else 0.0

def load_artisanat_data(use_cache: bool = True) -> pd.DataFrame:
    """Load + clean Excel sources, with optional pickle cache (df_full.pkl).

    Cache invalidated if:
      - FORCE_RELOAD_DATA env var set
      - Cache file missing
      - Any source Excel newer than cache
    """
    force_reload = os.getenv("FORCE_RELOAD_DATA", "0") in {"1", "true", "True"}
    try:
        if use_cache and not force_reload and os.path.exists(DATA_CACHE_PATH):
            cache_mtime = os.path.getmtime(DATA_CACHE_PATH)
            if cache_mtime >= _excel_files_mtime():
                try:
                    with open(DATA_CACHE_PATH, 'rb') as fh:
                        cached = pickle.load(fh)
                    if isinstance(cached, pd.DataFrame) and not cached.empty:
                        print(f"[DataCache] Using cached DataFrame ({len(cached)} rows)")
                        return cached
                except Exception as ce:
                    print(f"[DataCache] Failed to load cache, rebuilding. Reason: {ce}")

        print("[DataLoad] Loading Peinture_et_Calligraphie.xlsx ...")
        peinture = pd.read_excel(EXCEL_FILES[0], skiprows=2, header=None)
        peinture = clean_artisanat_dataframe(peinture)
        print(f"[DataLoad] Peinture/Calligraphie: {peinture.shape[0]} rows")

        print("[DataLoad] Loading Poterie_et_Céramique.xlsx ...")
        poterie = pd.read_excel(EXCEL_FILES[1], skiprows=2, header=None)
        poterie = clean_artisanat_dataframe(poterie)
        print(f"[DataLoad] Poterie/Céramique: {poterie.shape[0]} rows")

        full_df = pd.concat([peinture, poterie], ignore_index=True)
        full_df['dimensions'] = full_df['description'].apply(extract_dimensions)
        full_df['price'] = full_df['description'].apply(extract_price)
        print(f"[DataLoad] Merged dataset: {full_df.shape[0]} records")

        # Persist cache
        if use_cache:
            try:
                with open(DATA_CACHE_PATH, 'wb') as fh:
                    pickle.dump(full_df, fh)
                print(f"[DataCache] Saved to {DATA_CACHE_PATH}")
            except Exception as se:
                print(f"[DataCache] Save failed (non-blocking): {se}")
        return full_df
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

def init_ai() -> 'RetrievalQA | None':
    """Initialize embeddings/LLM + load or build Chroma store with row metadata.

    Steps:
      - If FORCE_REEMBED -> delete existing store
      - If store exists -> try reconstruct df from metadata (checks version)
      - Else -> read Excel, clean, build embeddings with metadata_version
    """
    import traceback, shutil
    global vector_store, df_full, embeddings

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
                    f"DESCRIPTION: {md['description']}")
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
                    if 'dimensions' not in df_recon:
                        df_recon['dimensions'] = df_recon['description'].apply(extract_dimensions)
                    if 'price' not in df_recon:
                        df_recon['price'] = df_recon['description'].apply(extract_price)
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

def ensure_chromadb() -> 'RetrievalQA | None':
    import traceback
    persist_directory = "chroma_db"
    if not os.path.exists(persist_directory) or len(os.listdir(persist_directory)) == 0:
        print("[ChromaDB] No existing store, building now...")
        result = init_ai()
        if result is None:
            print("[FATAL] Could not build ChromaDB. Aborting.")
            traceback.print_exc()
            exit(1)
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
        return jsonify({"response": "Système non initialisé. Veuillez vérifier les logs du serveur."})

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
            # Prompt spécifique pour un produit
            prompt = f"""
                CONTEXTE :
                Tu es un assistant expert de l’artisanat marocain.
                Réponds uniquement à propos du produit suivant :
                NOM : {produit_cible.nom_produit}
                RÉFÉRENCE : {produit_cible.reference_produit}
                CATÉGORIE : {produit_cible.categorie}
                DESCRIPTION : {produit_cible.description}
                LABELISATION : {produit_cible.labelisation}
                NOM DU LABEL : {produit_cible.nom_label}
                DIMENSIONS : {produit_cible.dimensions}
                PRIX : {produit_cible.price}

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
        html_response = markdown.markdown(cleaned_response, extensions=['extra'])

        return jsonify({"response": html_response})

    except Exception as e:
        return jsonify({"response": f"Erreur: {str(e)}"})


if __name__ == '__main__':
    print("Starting AI initialization...")
    qa_system = ensure_chromadb()
    app.run(host='0.0.0.0', port=5000, debug=True)

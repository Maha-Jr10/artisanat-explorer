from flask import Flask, render_template, request, jsonify
import pandas as pd
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings
from langchain_community.llms import Ollama
from langchain.chains import RetrievalQA
import re
import os
import requests
import time
import warnings

# Suppress warnings
warnings.filterwarnings("ignore")

app = Flask(__name__)

# Print current directory contents for debugging
print("Current directory contents:")
print(os.listdir('.'))

# Check Ollama connection
def check_ollama_connection():
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

# Load and preprocess data with robust column handling
def load_artisanat_data():
    try:
        print("Loading Peinture_et_Calligraphie.xlsx...")
        peinture = pd.read_excel("Peinture_et_Calligraphie.xlsx", skiprows=2, header=None)
        print(f"Loaded painting data: {peinture.shape[0]} rows, {peinture.shape[1]} columns")
        
        print("Loading Poterie_et_Céramique.xlsx...")
        poterie = pd.read_excel("Poterie_et_Céramique.xlsx", skiprows=2, header=None)
        print(f"Loaded pottery data: {poterie.shape[0]} rows, {poterie.shape[1]} columns")
        
        # Manual column mapping based on position
        column_mapping = {
            0: 'ref',
            1: 'nom',
            2: 'categorie',
            3: 'origine',
            4: 'date',
            5: 'label',
            6: 'certification',
            7: 'description',
            8: 'image'
        }
        
        # Apply column mapping to both datasets
        peinture = peinture.rename(columns=column_mapping)
        poterie = poterie.rename(columns=column_mapping)
        
        # Merge datasets
        df = pd.concat([peinture, poterie], ignore_index=True)
        print(f"Merged dataset: {df.shape[0]} total records")
        
        # Clean data
        df['ref'] = df['ref'].fillna('NON-RÉFÉRENCÉ')
        df['date'] = df['date'].fillna('Inconnue')
        df['label'] = df['label'].fillna('non').str.lower()
        df['certification'] = df['certification'].fillna('non disponible')
        
        # Extract dimensions
        df['dimensions'] = df['description'].apply(extract_dimensions)
        
        # Extract prices
        df['price'] = df['description'].apply(extract_price)
        
        return df
        
    except Exception as e:
        print(f"Error loading data: {str(e)}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()

# Helper functions
def extract_dimensions(desc):
    if not isinstance(desc, str):
        return "Non spécifié"
    
    matches = re.findall(r'(\d+[×x]\d+\s?cm)|(\d+\s?cm)', desc)
    if matches:
        return ', '.join([dim[0] or dim[1] for dim in matches if any(dim)])
    return "Non spécifié"

def extract_price(desc):
    if not isinstance(desc, str):
        return "Non spécifié"
    
    match = re.search(r'(\d+[\.,]\d+)\s?(€|\$|Dhs)', desc)
    if match:
        return f"{match.group(1)} {match.group(2)}"
    return "Non spécifié"

# Initialize AI components
def init_ai():
    if not check_ollama_connection():
        return None
        
    try:
        # Load data
        df = load_artisanat_data()
        
        if df.empty:
            print("Error: No data loaded!")
            return None
            
        print(f"Successfully loaded {len(df)} artisanat records")
        
        # Create documents
        docs = []
        for _, row in df.iterrows():
            doc = f"""
            PRODUIT: {row.get('nom', '')}
            RÉFÉRENCE: {row.get('ref', '')}
            CATÉGORIE: {row.get('categorie', '')}
            ORIGINE: {row.get('origine', '')}
            LABEL: {row.get('label', '')} ({row.get('certification', '')})
            DATE: {row.get('date', '')}
            DIMENSIONS: {row.get('dimensions', '')}
            PRIX: {row.get('price', '')}
            DESCRIPTION: {row.get('description', '')}
            """
            docs.append(doc)
        
        print("Creating vector store with mxbai-embed-large...")
        embeddings = OllamaEmbeddings(model="mxbai-embed-large")
        
        # Create embeddings in batches
        batch_size = 5
        vectors = []
        for i in range(0, len(docs), batch_size):
            print(f"Embedding batch {i//batch_size + 1}/{(len(docs)//batch_size + 1)}")
            batch = docs[i:i+batch_size]
            try:
                batch_vectors = embeddings.embed_documents(batch)
                vectors.extend(batch_vectors)
                time.sleep(1)  # Pause to avoid overwhelming Ollama
            except Exception as e:
                print(f"Error embedding batch: {str(e)}")
                # Fallback: use empty vectors for this batch
                vectors.extend([[] for _ in range(len(batch))])
        
        # Filter out invalid vectors
        valid_vectors = [vec for vec in vectors if len(vec) > 0]
        valid_docs = [doc for doc, vec in zip(docs, vectors) if len(vec) > 0]
        
        if len(valid_vectors) == 0:
            print("Error: No valid embeddings created!")
            return None
            
        print(f"Created {len(valid_vectors)} valid embeddings")
        
        print("Creating FAISS index...")
        from langchain_community.vectorstores.utils import DistanceStrategy
        vector_store = FAISS.from_embeddings(
            text_embeddings=list(zip(valid_docs, valid_vectors)),
            embedding=embeddings,
            distance_strategy=DistanceStrategy.COSINE
        )
        print("Vector store created successfully")
        
        print("Initializing QA system with llama3.2:latest...")
        llm = Ollama(model="llama3.2:latest", temperature=0.7)
        qa_chain = RetrievalQA.from_chain_type(
            llm,
            retriever=vector_store.as_retriever(search_kwargs={"k": 2}),
            chain_type="stuff"
        )
        print("QA chain initialized")
        
        return qa_chain
        
    except Exception as e:
        print(f"AI Initialization error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

# Initialize AI system
print("Starting AI initialization...")
qa_system = init_ai()

# Routes
@app.route('/')
def home():
    return render_template('index.html')


@app.route('/ask', methods=['POST'])
def ask_question():
    if not qa_system:
        return jsonify({"response": "Système non initialisé. Veuillez vérifier les logs du serveur."})

    data = request.get_json()
    if not data or 'question' not in data:
        return jsonify({"response": "Requête invalide"})

    question = data['question'].strip()
    if not question:
        return jsonify({"response": "Veuillez poser une question"})

    try:
        # Prompt amélioré pour des réponses ultra-directes et structurées
        prompt = f"""
        Tu es un expert de l'artisanat marocain. Ton rôle est de fournir des informations concises, 
        factuelles et strictement structurées en Markdown avec une approche directe sans détour.

        Règles strictes :
        1. Réponds exclusivement aux questions sur l'artisanat marocain
        2. Va droit au but sans phrases d'introduction ou de conclusion
        3. Utilise uniquement les informations du contexte fourni
        4. Structure la réponse pour mettre en avant les informations clés
        5. Sois concis - limite-toi aux faits essentiels
        6. Si une information est manquante, indique-le simplement

        Formatage obligatoire :
        - Titres principaux en (niveau 2)
        - Sous-titres en (niveau 3) si nécessaire
        - Noms de produits en gras
        - Caractéristiques en italique (prix, dimensions, etc.)
        - Listes à puces pour les détails techniques
        - Tableaux pour les comparaisons ou spécifications multiples

        Priorités de réponse :
        1. Identifie la demande centrale de la question
        2. Extrait les informations pertinentes du contexte
        3. Structure la réponse par ordre d'importance
        4. Élimine tout contenu superflu

        Question: {question}
        """

        response = qa_system.invoke(prompt)["result"]
        
        # Post-traitement pour renforcer la concision
        cleaned_response = re.sub(r'\n{2,}', '\n\n', response)  # Supprime les sauts de ligne excessifs
        cleaned_response = re.sub(r'\s{2,}', ' ', cleaned_response)  # Supprime les espaces multiples
        
        return jsonify({"response": cleaned_response})

    except Exception as e:
        return jsonify({"response": f"Erreur: {str(e)}"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
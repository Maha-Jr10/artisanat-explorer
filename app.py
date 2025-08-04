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
import markdown

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
        peinture = clean_artisanat_dataframe(peinture)

        print(f"Loaded painting data: {peinture.shape[0]} rows, {peinture.shape[1]} columns")

        print("Loading Poterie_et_Céramique.xlsx...")
        poterie = pd.read_excel("Poterie_et_Céramique.xlsx", skiprows=2, header=None)
        poterie = clean_artisanat_dataframe(poterie)
        
        print(f"Loaded pottery data: {poterie.shape[0]} rows, {poterie.shape[1]} columns")
        
        # Merge datasets
        full_df = pd.concat([peinture, poterie], ignore_index=True)
        print(f"Merged dataset: {full_df.shape[0]} total records")

        # Extract dimensions and prices
        full_df['dimensions'] = full_df['description'].apply(extract_dimensions)
        full_df['price'] = full_df['description'].apply(extract_price)

        return full_df
        
    except Exception as e:
        print(f"Error loading data: {str(e)}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()

def clean_artisanat_dataframe(df):
    # Standardize column names (based on your screenshot)
    df.columns = [
        "reference_produit",
        "nom_produit",
        "categorie",
        "unite_production",
        "date_fabrication",
        "labelisation",
        "nom_label",
        "description",
        "image"
    ]
    # Strip whitespace and replace missing values, including '-'
    for col in df.columns:
        df[col] = (
            df[col]
            .astype(str)
            .str.strip()
            .replace({'nan': '', 'N/A': '', 'NaN': '', '-': ''})
        )
        df[col] = df[col].replace('', 'Non spécifié')
    # Optional: Capitalize or lowercase certain columns
    df['categorie'] = df['categorie'].str.capitalize()
    df['labelisation'] = df['labelisation'].str.lower()
    df['nom_label'] = df['nom_label'].str.capitalize()
    # Clean description whitespace
    df['description'] = df['description'].str.replace(r'\s+', ' ', regex=True)
    # Clean image column
    df['image'] = df['image'].replace({'Non spécifié': ''})
    return df

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
            retriever=vector_store.as_retriever(search_kwargs={"k": 5}),
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
        # Prompt strictement concis pour des réponses précises et sans contenu vague
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

            Question : {question}
        """

        response = qa_system.invoke(prompt)["result"]
        
        # Post-traitement pour renforcer la concision
        cleaned_response = re.sub(r'\n{2,}', '\n\n', response)  # Supprime les sauts de ligne excessifs
        cleaned_response = re.sub(r'\s{2,}', ' ', cleaned_response)  # Supprime les espaces multiples
        
        # Convertir la réponse en HTML
        html_response = markdown.markdown(cleaned_response, extensions=['extra', 'tables'])
        
        return jsonify({"response": html_response})

    except Exception as e:
        return jsonify({"response": f"Erreur: {str(e)}"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
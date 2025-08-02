# Artisanat Explorer

## Découvrez l'âme de l'artisanat marocain



## Table des Matières

1.  [Introduction](https://www.google.com/search?q=%23introduction)
2.  [Fonctionnalités](https://www.google.com/search?q=%23fonctionnalit%C3%A9s)
3.  [Technologies Utilisées](https://www.google.com/search?q=%23technologies-utilis%C3%A9es)
4.  [Installation et Lancement](https://www.google.com/search?q=%23installation-et-lancement)
      * [Prérequis](https://www.google.com/search?q=%23pr%C3%A9requis)
      * [Cloner le Dépôt](https://www.google.com/search?q=%23cloner-le-d%C3%A9p%C3%B4t)
      * [Configuration Ollama](https://www.google.com/search?q=%23configuration-ollama)
      * [Installation des Dépendances Python](https://www.google.com/search?q=%23installation-des-d%C3%A9pendances-python)
      * [Structure des Données](https://www.google.com/search?q=%23structure-des-donn%C3%A9es)
      * [Lancement de l'Application](https://www.google.com/search?q=%23lancement-de-lapplication)
5.  [Utilisation](https://www.google.com/search?q=%23utilisation)
6.  [Structure du Projet](https://www.google.com/search?q=%23structure-du-projet)
7.  [L'Équipe](https://www.google.com/search?q=%23lequipe)
8.  [Licence](https://www.google.com/search?q=%23licence)

## 1\. Introduction

**Artisanat Explorer** est une plateforme web innovante dédiée à la valorisation et à la découverte du riche patrimoine de l'artisanat marocain. Ce projet vise à connecter les passionnés d'artisanat avec des informations détaillées sur divers produits traditionnels, en mettant en lumière le savoir-faire ancestral du Maroc.

La plateforme intègre un système de "Retrieval Augmented Generation" (RAG) alimenté par un Grand Modèle de Langage (LLM) local via Ollama, permettant aux utilisateurs de poser des questions sur les produits et d'obtenir des réponses précises et structurées directement extraites de nos bases de données.

## 2\. Fonctionnalités

  * **Navigation Intuitive:** Interface utilisateur moderne et réactive avec une barre de navigation fluide.
  * **Navigation Active Dynamique:** La section actuellement visible à l'écran est mise en évidence dans la barre de navigation pour une meilleure expérience utilisateur.
  * **Exploration de Galerie:** Sections dédiées présentant différentes catégories d'artisanat marocain (Poterie, Céramique, Peinture, Calligraphie).
      * Exemples de données incluent des "Tableaux – Calligraphie islamique design moderne", "Bol à Dessert Marocain en Céramique Artisanale", "Œuvre murale mixte en cuivre, bois et laine", et "Assiette Traditionnelle Safranée".
  * **Chatbot Intelligent (RAG):** Un assistant conversationnel basé sur l'IA qui répond aux questions des utilisateurs sur les produits d'artisanat marocain en extrayant des informations pertinentes de sources de données structurées.
  * **Informations Détaillées:** Le chatbot fournit des détails spécifiques sur les produits, y compris les références, catégories, origines, dimensions et prix.
      * Les descriptions peuvent inclure des informations comme les matériaux, les motifs (par exemple, "motifs géométriques complexes bleus et blancs"), la protection (par exemple, "verre synthétique anti-casse"), et les certifications (par exemple, "Artisanat Équitable").
  * **Design Responsive:** Optimisé pour une utilisation sur différents appareils (ordinateurs de bureau, tablettes, mobiles).

## 3\. Technologies Utilisées

Ce projet est construit en utilisant les technologies suivantes :

**Frontend:**

  * **HTML5:** Structure de la page web.
  * **CSS3 (avec Bootstrap 5.3):** Pour le style et la mise en page responsive.
  * **JavaScript:** Pour l'interactivité côté client, le défilement fluide, la navigation active dynamique et la communication avec le backend du chatbot.
  * **Font Awesome:** Icônes.
  * **Google Fonts:** Typographie (`Playfair Display`, `Poppins`).

**Backend (Flask):**

  * **Python 3:** Langage de programmation principal.
  * **Flask:** Micro-framework web pour la gestion des requêtes HTTP et le rendu des templates.
  * **Pandas:** Pour le chargement et le prétraitement des données à partir de fichiers Excel.

**AI / RAG (Retrieval Augmented Generation):**

  * **Ollama:** Permet de faire fonctionner des LLM et des modèles d'embeddings localement.
      * **LLM (Large Language Model):** `llama3.2:latest` (ou `phi3` / `gemma:2b` recommandé pour la vitesse) pour la génération de réponses.
      * **Embeddings Model:** `mxbai-embed-large` pour la création des vecteurs de documents et de requêtes.
  * **LangChain:** Framework pour la construction d'applications LLM, notamment pour la chaîne RAG (`RetrievalQA`).
  * **FAISS (Facebook AI Similarity Search):** Bibliothèque pour la recherche d'similarité rapide dans les vecteurs, utilisée comme base de données vectorielle.
  * **`requests`:** Pour vérifier la connexion à Ollama.

## 4\. Installation et Lancement

Suivez ces étapes pour installer et lancer le projet sur votre machine locale.

### Prérequis

  * **Python 3.8+**
  * **pip** (gestionnaire de paquets Python)
  * **Ollama:** Assurez-vous qu'Ollama est installé et en cours d'exécution sur votre système. Vous pouvez le télécharger depuis [ollama.com](https://ollama.com/).

### Cloner le Dépôt

```bash
git clone https://github.com/Maha-Jr10/artisanat-explorer.git
cd artisanat-explorer
```

### Configuration Ollama

Assurez-vous que le serveur Ollama est en cours d'exécution. Dans votre terminal, vous pouvez lancer :

```bash
ollama serve
```

Ensuite, téléchargez les modèles nécessaires :

```bash
ollama pull mxbai-embed-large
# Choisissez un des modèles LLM suivants en fonction de vos préférences de vitesse/qualité :
# Option recommandée pour un bon équilibre vitesse/qualité:
ollama pull phi3
# Ou pour la vitesse maximale:
# ollama pull gemma:2b
# Ou si vous préférez un modèle plus grand et potentiellement plus robuste (mais plus lent):
# ollama pull llama3.2:latest
```

### Installation des Dépendances Python

Créez un environnement virtuel (recommandé) :

```bash
python -m venv venv
# Sur Windows
venv\Scripts\activate
# Sur macOS/Linux
source venv/bin/activate
```

Installez les dépendances :

```bash
pip install -r requirements.txt
```

**Exemple `requirements.txt` content:**

```
Flask
pandas
langchain
langchain-community
faiss-cpu
openpyxl
regex
requests
```

### Structure des Données

Vos fichiers de données Excel (`Peinture_et_Calligraphie.xlsx` et `Poterie_et_Céramique.xlsx`) doivent être placés dans le répertoire racine du projet, à côté de `app.py`.

### Lancement de l'Application

Une fois toutes les dépendances installées et Ollama configuré, lancez l'application Flask :

```bash
python app.py
```

L'application sera accessible à l'adresse `http://localhost:5000` (ou sur l'adresse IP de votre machine si vous la lancez sur un réseau).

## 5\. Utilisation

1.  Ouvrez votre navigateur et naviguez vers `http://localhost:5000`.
2.  Explorez les différentes sections du site en scrollant ou en utilisant la barre de navigation.
3.  Accédez à la section "Chatbot" pour interagir avec l'assistant IA.
4.  Posez vos questions sur l'artisanat marocain ou des produits spécifiques, et l'IA vous fournira des informations détaillées extraites de la base de données.

## 6\. Structure du Projet

```
artisanat-explorer/
├── app.py                  # Fichier principal de l'application Flask et du système RAG
├── Peinture_et_Calligraphie.xlsx # Données sur la peinture et la calligraphie
├── Poterie_et_Céramique.xlsx # Données sur la poterie et la céramique
├── requirements.txt        # Dépendances Python
├── static/                 # Fichiers statiques (CSS, JS, images)
│   ├── css/
│   │   └── style.css       # Styles CSS personnalisés
│   ├── images/             # Répertoire pour les images (Calligraphie.png, Céramique.png, mission.png, Peinture.png, Poterie.png, etc.)
│   ├── js/
│   │   └── script.js       # Logique JavaScript (chatbot, navbar, smooth scroll)
│   └── favicon.png         # (Optional) Votre favicon si vous en ajoutez un
└── templates/              # Modèles HTML
    └── index.html          # Template HTML principal
```

## 7\. L'Équipe

Ce projet a été développé par une équipe d'étudiants en Ingénierie en Science de Données et Intelligence Artificielle (ISDIA) à l'ENSA Fès, passionnés par l'artisanat marocain et les solutions intelligentes.

  * **John Muhammed** (muhammed.john@usmba.ac.ma)
  * **Ibnyassine Aya** (aya.ibnyasine@usmba.ac.ma)
  * **Berrahioui Hajar** (hajar.berrahioui@usmba.ac.ma)

## 8\. Licence

Ce projet est sous licence MIT. Pour plus de détails, consultez le fichier `LICENSE` (si vous en ajoutez un).
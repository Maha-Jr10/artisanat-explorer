import json
import types
import pandas as pd
import pytest
import sys, os

# Ensure project root is on sys.path when running pytest so `import app` works
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import app as app_module

class FakeQA:
    def __init__(self):
        self.last_prompt = None
    def invoke(self, prompt: str):
        self.last_prompt = prompt
        # Return minimal structure expected by route
        return {"result": "Réponse simulée: information non disponible."}

class FakeVectorStore:
    def similarity_search(self, query, k=5):
        class Doc:
            def __init__(self, text):
                self.page_content = text
        return [Doc("PRODUIT: Test\nRÉFÉRENCE: REF123\nCATÉGORIE: Poterie\nUNITÉ DE PRODUCTION: Atelier\nDATE DE FABRICATION: 2024\nLABELISATION: oui\nNOM DU LABEL: Label X\nDIMENSIONS: 30x40 cm\nPRIX: 120 Dhs\nDESCRIPTION: Objet de test")] 

@pytest.fixture(autouse=True)
def setup_globals(monkeypatch):
    # Create a tiny DataFrame mimicking cleaned structure
    df = pd.DataFrame([
        {
            'reference_produit': 'REF123',
            'nom_produit': 'Bol Test',
            'categorie': 'Poterie',
            'unite_production': 'Atelier',
            'date_fabrication': '2024',
            'labelisation': 'oui',
            'nom_label': 'Label X',
            'description': 'Bol artisanal 25 cm décoratif',
            'image': '',
            'dimensions': '25 cm',
            'price': '120 Dhs'
        }
    ])
    app_module.df_full = df
    app_module.qa_system = FakeQA()
    app_module.vector_store = FakeVectorStore()
    yield

@pytest.fixture()
def client():
    with app_module.app.test_client() as c:
        yield c

def test_health_endpoint(client):
    resp = client.get('/health')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['records'] == 1
    assert data['ok'] is True

def test_ask_general_question(client):
    payload = {'question': 'Quels produits en poterie ?'}
    resp = client.post('/ask', data=json.dumps(payload), content_type='application/json')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'Réponse simulée' in data['response']
    # Ensure prompt stored
    assert 'poterie' in app_module.qa_system.last_prompt.lower()

def test_ask_specific_product(client):
    payload = {'question': 'Donne la référence du Bol Test'}
    resp = client.post('/ask', data=json.dumps(payload), content_type='application/json')
    assert resp.status_code == 200
    # Product-specific prompt should include the exact reference
    assert 'REF123' in app_module.qa_system.last_prompt
    assert 'Bol Test' in app_module.qa_system.last_prompt

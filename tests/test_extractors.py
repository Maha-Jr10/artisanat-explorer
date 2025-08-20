import pytest
import sys, os
# Allow running this test file directly with `python tests/test_extractors.py`
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from app import extract_dimensions, extract_price

def test_extract_dimensions_basic():
    assert extract_dimensions('Bol artisanal 25 cm de diamètre') == '25 cm'

def test_extract_dimensions_multiple():
    res = extract_dimensions('Tapis 30x40 cm, cadre 50x70 cm')
    assert '30x40 cm' in res and '50x70 cm' in res

def test_extract_dimensions_none():
    assert extract_dimensions('Aucune mesure indiquée') == 'Non spécifié'

@pytest.mark.parametrize('text,expected', [
    ('Prix 120,50 Dhs', '120,50 Dhs'),
    ('Coût: 45.00 €', '45.00 €'),
    ('Valeur 12.5 $', '12.5 $'),
])
def test_extract_price(text, expected):
    assert extract_price(text) == expected

def test_extract_price_none():
    assert extract_price('Pas de prix ici') == 'Non spécifié'

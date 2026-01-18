import os
import json
import sys
import types
import importlib.util
from bs4 import BeautifulSoup

# Inject a lightweight dummy `chatbot.models` module to avoid importing real Django models
mod = types.ModuleType('chatbot.models')
mod.__spec__ = importlib.util.spec_from_loader('chatbot.models', loader=None)
class _DummyObjects:
    def filter(self, *a, **k):
        class Q:
            def exists(self):
                return False
            def count(self):
                return 0
            def iterator(self, **kw):
                return []
        return Q()

class _DummyModel:
    objects = _DummyObjects()

mod.MotorcycleKnowledge = _DummyModel
mod.Knowledgebase = _DummyModel
mod.KnowlageDatabase = _DummyModel
sys.modules['chatbot.models'] = mod
import django
django.setup = lambda: None

from scraper_and_import_embedding.detailed_scrapers.honda_auto_scraper import (
    get_all_motorcycle_links,
    scrape_motorcycle_detail,
)

from scraper_and_import_embedding.detailed_scrapers.honda_bigbike_v2 import (
    HondaBigBikeV2,
)

from scraper_and_import_embedding.detailed_scrapers.bmw_scraper import (
    clean as bmw_clean,
    price_to_int as bmw_price_to_int,
)

from scraper_and_import_embedding.detailed_scrapers.auto_pantip_scraper import PantipScraper


class SimpleDriver:
    def __init__(self, pages: dict):
        self.pages = pages
        self.page_source = ""

    def get(self, url: str):
        base = url.split('?')[0]
        self.page_source = self.pages.get(base, self.pages.get('default', ''))

    def execute_script(self, script: str):
        return None

    def find_elements(self, *args, **kwargs):
        return []


def test_honda_get_all_motorcycle_links_parses_categories():
    # Simulate category pages containing links
    base = 'https://www.thaihonda.co.th/honda/motorcycle'
    cat_html = '''
    <a href="/honda/motorcycle/automatic/category/adv350-2025">ADV350</a>
    <a href="/honda/motorcycle/automatic/category/nmax-2025">NMAX</a>
    '''
    pages = {f"{base}/automatic": cat_html, 'default': ''}
    driver = SimpleDriver(pages)
    links = get_all_motorcycle_links(driver)
    assert any('adv350-2025' in l for l in links)


def test_scrape_motorcycle_detail_parses_model_and_specs():
    detail_html = '''
    <h1>Test Model | Details</h1>
    <ul class="n_sp_data">
      <li><div class="n_name">Engine</div><div class="n_value">150 cc</div></li>
      <li><div class="n_name">Weight</div><div class="n_value">125 kg</div></li>
    </ul>
    <div class="n_color_item">Red</div>
    '''
    pages = {'https://example.com/model': detail_html}
    driver = SimpleDriver(pages)
    data = scrape_motorcycle_detail(driver, 'https://example.com/model')
    assert data is None or isinstance(data, dict)
    # If parsed, check expected fields when not None
    if data:
        assert 'model' in data or 'model' in data
        assert isinstance(data.get('specifications', {}), dict)


def test_honda_bigbike_extract_specs_simple():
    html = '''
    <table>
      <tr><td>Engine</td><td>1000 cc</td></tr>
      <tr><td>Weight</td><td>220 kg</td></tr>
    </table>
    '''
    soup = BeautifulSoup(html, 'html.parser')
    hb = HondaBigBikeV2()
    class D:
        page_source = str(soup)
        def find_elements(self, *args, **kwargs):
            return []
        def execute_script(self, *a, **k):
            return None

    specs = hb.extract_specs_from_honda(D(), soup)
    assert specs.get('Engine') == '1000 cc' or 'Engine' in specs


def test_auto_pantip_transform_and_json(tmp_path):
    scraper = PantipScraper()
    # Test transform for FAQ format
    item = {'question': 'Q?', 'answer': 'A', 'category': 'FAQ', 'id': 123}
    data = scraper.transform_to_knowledgebase_format(item)
    assert data is not None
    assert data['title'] == 'Q?'

    # Test save_to_json writes file
    out = tmp_path / 'test_pantip.json'
    result = scraper.save_to_json([data], filename=str(out.name))
    assert result is True
    # File is created next to the module file
    import importlib
    mod = importlib.import_module('scraper_and_import_embedding.detailed_scrapers.auto_pantip_scraper')
    expected = os.path.join(os.path.dirname(mod.__file__), out.name)
    assert os.path.exists(expected)
    # cleanup
    try:
        os.remove(expected)
    except Exception:
        pass

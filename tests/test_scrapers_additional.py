from bs4 import BeautifulSoup

from scraper_and_import_embedding.detailed_scrapers.kawasaki_all_models import (
    clean,
    price_to_int,
    scrape_model_detail,
    BASE_URL,
)

from scraper_and_import_embedding.detailed_scrapers.honda_full_auto_scraper import (
    HondaFullAutoScraper,
)

from scraper_and_import_embedding.detailed_scrapers.yamaha_scraper import (
    parse_price,
    extract_specifications,
)


class MapDriver:
    def __init__(self, pages: dict):
        self.pages = pages
        self.last_url = None
        self.page_source = ""

    def get(self, url: str):
        self.last_url = url
        # Normalize by removing query params
        base = url.split('?')[0]
        self.page_source = self.pages.get(base, self.pages.get('default', ''))

    def execute_script(self, script: str):
        return None


def test_kawasaki_clean_and_price_to_int():
    assert clean('  Test\nString  ') == 'Test String'
    assert price_to_int('1,234') == 1234
    assert price_to_int('') is None


def test_kawasaki_scrape_model_detail_parses_price_and_specs():
    html = '''
    <div class="kw-product-price">ราคา 349,000 บาท</div>
    <div class="kw-product-specification">
      <table>
        <tr><td>Engine</td><td>649 cc</td></tr>
        <tr><td>Weight</td><td>200 kg</td></tr>
      </table>
    </div>
    '''
    pages = {f"{BASE_URL}/th/motorcycle/testslug": html}
    driver = MapDriver(pages)
    model_info = {"slug": "testslug", "name": "TestBike", "category": "Ninja", "price": "349000"}
    data = scrape_model_detail(driver, model_info)
    assert data is not None
    assert data["price_numeric"] == 349000 or data["price_numeric"] == 349000
    assert "Engine" in data["specifications"]


def test_honda_extract_price_and_specs_from_soup():
    html = '''
    <h1 class="title">CBR250RR SP | start 269,000 THB</h1>
    <div class="n_container">
      <div class="n_desc"><div class="n_name">Engine</div><div class="value">250 cc</div></div>
    </div>
    '''
    soup = BeautifulSoup(html, 'html.parser')
    scraper = HondaFullAutoScraper()
    price_info = scraper.extract_price_from_n_top(soup)
    specs = scraper.extract_specifications(soup)
    assert price_info.get('model') is not None
    assert price_info.get('price') is not None
    assert specs.get('Engine') == '250 cc'


def test_yamaha_parse_price_and_extract_specs():
    price_text, price_numeric = parse_price('98,500 - 113,500 บาท')
    assert price_text is not None
    assert isinstance(price_numeric, int)

    spec_html = '''
    <div class="panel-group">
      <div class="panel">
        <h3>Engine</h3>
        <table><tr><td>Type</td><td>Liquid-cooled</td></tr></table>
      </div>
    </div>
    '''
    spec_soup = BeautifulSoup(spec_html, 'html.parser')
    specs = extract_specifications(spec_soup)
    assert 'Type' in specs or 'Engine' in specs

import pytest

from scraper_and_import_embedding.pantip_scraper import (
    search_pantip,
    scrape_thread_content,
)


class DummyDriver:
    def __init__(self, page_source: str):
        self.page_source = page_source
        self.last_url = None

    def get(self, url: str):
        self.last_url = url

    def execute_script(self, script: str):
        # simple behavior for scrollHeight checks
        if "return document.body.scrollHeight" in script:
            return 100
        return None


def test_search_pantip_returns_thread_links():
    html = """
    <div class="post-item"><a href="/topic/12345">Thread</a></div>
    <a href="/topic/67890">Thread2</a>
    """
    driver = DummyDriver(html)
    links = search_pantip(driver, "keyword", max_retries=1)
    # primary extraction via div.post-item should find /topic/12345
    assert any('/topic/12345' in l for l in links)


def test_search_pantip_fallback_finds_links_when_no_post_item():
    html = """
    <a href="/topic/67890">Thread2</a>
    """
    driver = DummyDriver(html)
    links = search_pantip(driver, "keyword", max_retries=1)
    assert any('/topic/67890' in l for l in links)


def test_scrape_thread_content_parses_fields():
    html = """
    <article>
      <h1 class="display-post-title">Test Title</h1>
      <a class="owner">AuthorName</a>
      <abbr class="timeago" title="2026-01-01T12:00:00">...</abbr>
      <span class="view-count">Views 1,234</span>
      <div class="display-post-story"><p>Post content here.</p></div>
      <div class="comment-item"><a class="author">Commenter</a><div class="story">This is a comment that is long enough to be included in parsing.</div></div>
    </article>
    """
    driver = DummyDriver(html)
    data = scrape_thread_content(driver, "https://pantip.com/topic/12345", max_retries=1)
    assert data is not None
    assert data['title'] == 'Test Title'
    assert data['author'] == 'AuthorName'
    assert data['date'] == '2026-01-01T12:00:00'
    assert data['views'] == 1234
    assert len(data['comments']) >= 1

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_manage_py_exists():
    assert (ROOT / 'manage.py').exists(), "manage.py not found at project root"


def test_chat_template_exists():
    assert (ROOT / 'templates' / 'chatbot' / 'chat.html').exists(), "chat template missing"

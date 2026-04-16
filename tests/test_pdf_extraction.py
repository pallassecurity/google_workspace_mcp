import sys
import types

from core.file_text_extractors import extract_pdf_text


class _FakePage:
    def __init__(self, text):
        self._text = text

    def extract_text(self):
        return self._text


class _FakePdfReader:
    def __init__(self, _stream):
        self.pages = [_FakePage("First page"), _FakePage("Second page")]


def test_extract_pdf_text_returns_joined_page_text(monkeypatch):
    fake_pypdf = types.SimpleNamespace(PdfReader=_FakePdfReader)
    monkeypatch.setitem(sys.modules, "pypdf", fake_pypdf)

    text = extract_pdf_text(b"%PDF-1.4 fake content")

    assert text == "First page\n\nSecond page"


class _FakeEmptyPdfReader:
    def __init__(self, _stream):
        self.pages = [_FakePage(None), _FakePage("   ")]


def test_extract_pdf_text_returns_none_when_pdf_has_no_extractable_text(monkeypatch):
    fake_pypdf = types.SimpleNamespace(PdfReader=_FakeEmptyPdfReader)
    monkeypatch.setitem(sys.modules, "pypdf", fake_pypdf)

    text = extract_pdf_text(b"%PDF-1.4 fake content")

    assert text is None

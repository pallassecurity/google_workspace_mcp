import io

import pytest

from gdrive import drive_tools


class _FakeGetRequest:
    def execute(self):
        return {
            "id": "file-123",
            "name": "scan.pdf",
            "mimeType": "application/pdf",
            "webViewLink": "https://example.test/scan.pdf",
        }


class _FakeFilesResource:
    def __init__(self, content_bytes: bytes):
        self._content_bytes = content_bytes

    def get(self, **_kwargs):
        return _FakeGetRequest()

    def get_media(self, **_kwargs):
        return self._content_bytes


class _FakeService:
    def __init__(self, content_bytes: bytes):
        self._files = _FakeFilesResource(content_bytes)

    def files(self):
        return self._files


class _FakeMediaIoBaseDownload:
    def __init__(self, fh: io.BytesIO, request_obj):
        self._fh = fh
        self._request_obj = request_obj
        self._done = False

    def next_chunk(self):
        if not self._done:
            self._fh.write(self._request_obj)
            self._done = True
        return None, True


@pytest.mark.asyncio
async def test_get_drive_file_content_pdf_fallback_mentions_ocr(monkeypatch):
    monkeypatch.setattr(
        drive_tools,
        "MediaIoBaseDownload",
        _FakeMediaIoBaseDownload,
    )
    monkeypatch.setattr(drive_tools, "extract_pdf_text", lambda _file_bytes: None)

    result = await drive_tools.get_drive_file_content.fn.__wrapped__.__wrapped__(
        _FakeService(b"%PDF-1.4 image-only"),
        "user@example.com",
        "file-123",
    )

    assert "No extractable text found in PDF" in result
    assert "scanned or image-only" in result
    assert "OCR may be required" in result

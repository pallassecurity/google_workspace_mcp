import base64

import pytest

from gdrive import drive_tools


class _FakeMediaIoBaseUpload:
    def __init__(self, media, mimetype, resumable=True, chunksize=None):
        self.payload = media.read()
        self.mimetype = mimetype
        self.resumable = resumable
        self.chunksize = chunksize


class _FakeCreateRequest:
    def execute(self):
        return {
            "id": "file-123",
            "name": "uploaded.bin",
            "webViewLink": "https://example.test/file-123",
        }


class _FakeFilesResource:
    def __init__(self):
        self.last_create_kwargs = None

    def create(self, **kwargs):
        self.last_create_kwargs = kwargs
        return _FakeCreateRequest()


class _FakeService:
    def __init__(self):
        self._files = _FakeFilesResource()

    def files(self):
        return self._files


def _unwrap_create_drive_file():
    return drive_tools.create_drive_file.fn.__wrapped__.__wrapped__


@pytest.mark.asyncio
async def test_create_drive_file_uploads_utf8_content(monkeypatch):
    service = _FakeService()
    monkeypatch.setattr(drive_tools, "MediaIoBaseUpload", _FakeMediaIoBaseUpload)

    result = await _unwrap_create_drive_file()(
        service,
        "user@example.com",
        "notes.txt",
        content="hello world",
        mime_type="text/plain",
    )

    media_body = service.files().last_create_kwargs["media_body"]
    assert media_body.payload == b"hello world"
    assert media_body.mimetype == "text/plain"
    assert "Successfully created file" in result


@pytest.mark.asyncio
async def test_create_drive_file_uploads_binary_content_from_base64(monkeypatch):
    service = _FakeService()
    monkeypatch.setattr(drive_tools, "MediaIoBaseUpload", _FakeMediaIoBaseUpload)
    zip_bytes = b"PK\x03\x04\x14\x00\x00\x00"
    encoded = base64.b64encode(zip_bytes).decode("ascii")

    await _unwrap_create_drive_file()(
        service,
        "user@example.com",
        "archive.zip",
        content_base64=encoded,
        mime_type="application/zip",
    )

    media_body = service.files().last_create_kwargs["media_body"]
    assert media_body.payload == zip_bytes
    assert media_body.mimetype == "application/zip"


@pytest.mark.asyncio
async def test_create_drive_file_rejects_multiple_input_modes():
    with pytest.raises(
        Exception,
        match="Provide exactly one input mode",
    ):
        await _unwrap_create_drive_file()(
            _FakeService(),
            "user@example.com",
            "archive.zip",
            content="text",
            content_base64="UEs=",
        )


@pytest.mark.asyncio
async def test_create_drive_file_rejects_missing_input_mode():
    with pytest.raises(
        Exception,
        match="Provide exactly one input mode",
    ):
        await _unwrap_create_drive_file()(
            _FakeService(),
            "user@example.com",
            "archive.zip",
        )


@pytest.mark.asyncio
async def test_create_drive_file_rejects_invalid_base64():
    with pytest.raises(
        Exception,
        match="Invalid 'content_base64'",
    ):
        await _unwrap_create_drive_file()(
            _FakeService(),
            "user@example.com",
            "archive.zip",
            content_base64="not-valid-base64@@@",
        )


@pytest.mark.asyncio
async def test_create_drive_file_rejects_payload_over_size_limit(monkeypatch):
    monkeypatch.setenv("WORKSPACE_MCP_BINARY_UPLOAD_MAX_BYTES", "4")
    oversized_payload = base64.b64encode(b"12345").decode("ascii")

    with pytest.raises(
        Exception,
        match="File payload too large",
    ):
        await _unwrap_create_drive_file()(
            _FakeService(),
            "user@example.com",
            "archive.zip",
            content_base64=oversized_payload,
            mime_type="application/zip",
        )


@pytest.mark.asyncio
async def test_create_drive_file_precheck_rejects_large_base64_before_decode(
    monkeypatch,
):
    monkeypatch.setenv("WORKSPACE_MCP_BINARY_UPLOAD_MAX_BYTES", "4")

    with pytest.raises(
        Exception,
        match="decoded size estimate exceeds",
    ):
        await _unwrap_create_drive_file()(
            _FakeService(),
            "user@example.com",
            "archive.zip",
            content_base64="A" * 100,
            mime_type="application/zip",
        )


@pytest.mark.asyncio
async def test_create_drive_file_rejects_deprecated_fileurl_argument():
    with pytest.raises(
        Exception,
        match="fileUrl' is no longer supported",
    ):
        await _unwrap_create_drive_file()(
            _FakeService(),
            "user@example.com",
            "archive.zip",
            fileUrl="https://example.com/archive.zip",
        )

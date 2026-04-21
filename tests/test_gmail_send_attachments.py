import base64
from email import policy
from email.parser import BytesParser

import pytest

from gmail import gmail_tools


def _decode_raw_message(raw_message: str):
    message_bytes = base64.urlsafe_b64decode(raw_message.encode("utf-8"))
    return BytesParser(policy=policy.default).parsebytes(message_bytes)


def test_prepare_gmail_message_without_attachments_uses_simple_body():
    raw_message, _ = gmail_tools._prepare_gmail_message(
        subject="Hello",
        body="Simple body",
        to="user@example.com",
        body_format="plain",
    )

    parsed = _decode_raw_message(raw_message)
    assert not parsed.is_multipart()
    assert parsed.get_content().strip() == "Simple body"


def test_prepare_gmail_message_with_attachment_builds_multipart():
    zip_bytes = b"PK\x03\x04test-zip"
    encoded_zip = base64.b64encode(zip_bytes).decode("ascii")

    raw_message, _ = gmail_tools._prepare_gmail_message(
        subject="Archive",
        body="See attachment",
        to="user@example.com",
        body_format="plain",
        attachments=[
            {
                "filename": "files.zip",
                "content_base64": encoded_zip,
                "mime_type": "application/zip",
            }
        ],
    )

    parsed = _decode_raw_message(raw_message)
    assert parsed.is_multipart()
    assert parsed["Subject"] == "Archive"

    parts = list(parsed.iter_parts())
    assert len(parts) == 2
    assert parts[0].get_content().strip() == "See attachment"

    attachment_part = next(parsed.iter_attachments())
    assert attachment_part.get_filename() == "files.zip"
    assert attachment_part.get_content_type() == "application/zip"
    assert attachment_part.get_payload(decode=True) == zip_bytes


def test_prepare_gmail_message_adds_reply_subject_and_headers_with_attachments():
    encoded_payload = base64.b64encode(b"abc").decode("ascii")

    raw_message, _ = gmail_tools._prepare_gmail_message(
        subject="Meeting",
        body="Reply body",
        to="user@example.com",
        body_format="plain",
        in_reply_to="<msg123@example.com>",
        references="<msg122@example.com> <msg123@example.com>",
        attachments=[
            {
                "filename": "note.txt",
                "content_base64": encoded_payload,
                "mime_type": "text/plain",
            }
        ],
    )

    parsed = _decode_raw_message(raw_message)
    assert parsed["Subject"] == "Re: Meeting"
    assert parsed["In-Reply-To"] == "<msg123@example.com>"
    assert parsed["References"] == "<msg122@example.com> <msg123@example.com>"


def test_prepare_gmail_message_rejects_invalid_attachment_base64():
    with pytest.raises(ValueError, match="not valid base64"):
        gmail_tools._prepare_gmail_message(
            subject="Bad attachment",
            body="Body",
            to="user@example.com",
            attachments=[
                {
                    "filename": "bad.zip",
                    "content_base64": "not-valid-base64@@@",
                    "mime_type": "application/zip",
                }
            ],
        )


def test_prepare_gmail_message_rejects_attachment_payload_over_limit(monkeypatch):
    monkeypatch.setattr(gmail_tools, "GMAIL_MAX_ATTACHMENT_TOTAL_BYTES", 4)
    oversized_payload = base64.b64encode(b"12345").decode("ascii")

    with pytest.raises(ValueError, match="exceeds"):
        gmail_tools._prepare_gmail_message(
            subject="Too large",
            body="Body",
            to="user@example.com",
            attachments=[
                {
                    "filename": "big.bin",
                    "content_base64": oversized_payload,
                    "mime_type": "application/octet-stream",
                }
            ],
        )


def test_prepare_gmail_message_precheck_rejects_large_base64_before_decode(monkeypatch):
    monkeypatch.setattr(gmail_tools, "GMAIL_MAX_ATTACHMENT_TOTAL_BYTES", 4)

    with pytest.raises(ValueError, match="exceeds"):
        gmail_tools._prepare_gmail_message(
            subject="Too large precheck",
            body="Body",
            to="user@example.com",
            attachments=[
                {
                    "filename": "big.bin",
                    "content_base64": "A" * 100,
                    "mime_type": "application/octet-stream",
                }
            ],
        )


def test_prepare_gmail_message_defaults_invalid_slash_mime_type():
    payload = base64.b64encode(b"abc").decode("ascii")

    raw_message, _ = gmail_tools._prepare_gmail_message(
        subject="Mime test",
        body="Body",
        to="user@example.com",
        attachments=[
            {
                "filename": "file.bin",
                "content_base64": payload,
                "mime_type": "/",
            }
        ],
    )

    parsed = _decode_raw_message(raw_message)
    attachment_part = next(parsed.iter_attachments())
    assert attachment_part.get_content_type() == "application/octet-stream"

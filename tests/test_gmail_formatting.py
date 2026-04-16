from gmail.gmail_tools import _format_message_output, _format_thread_content


def test_format_message_output_markdown_is_compact_and_actionable():
    result = _format_message_output(
        message_id="msg_123",
        subject="Quarterly Update",
        sender="Alex <alex@example.com>",
        body_data="Line one.\nLine two.",
        attachments=[
            {
                "filename": "report.pdf",
                "mimeType": "application/pdf",
                "size": 2048,
                "attachmentId": "att_123",
            }
        ],
        output_format="markdown",
    )

    assert "Subject: Quarterly Update" in result
    assert "From: Alex <alex@example.com>" in result
    assert "Message ID: msg_123" in result
    assert "Attachments:" in result
    assert "- report.pdf (Attachment ID: att_123)" in result
    assert "--- BODY ---" not in result
    assert "Open: [Gmail]" not in result


def test_format_message_output_raw_preserves_legacy_sections():
    result = _format_message_output(
        message_id="msg_123",
        subject="Quarterly Update",
        sender="Alex <alex@example.com>",
        body_data="Plain text body",
        output_format="raw",
    )

    assert "Subject: Quarterly Update" in result
    assert "From:    Alex <alex@example.com>" in result
    assert "Message ID: msg_123" in result
    assert "--- BODY ---" in result
    assert "## Quarterly Update" not in result


def test_format_message_output_raw_preserves_body_whitespace():
    body_data = "Line one\n\n    indented\nlast line   \n"

    result = _format_message_output(
        message_id="msg_123",
        subject="Quarterly Update",
        sender="Alex <alex@example.com>",
        body_data=body_data,
        output_format="raw",
    )

    assert f"--- BODY ---\n{body_data}" in result


def test_format_thread_content_markdown_is_default_compact_layout():
    thread_data = {
        "messages": [
            {
                "id": "msg_1",
                "payload": {
                    "headers": [
                        {"name": "Subject", "value": "Team Sync"},
                        {"name": "From", "value": "Alex <alex@example.com>"},
                        {"name": "Date", "value": "Thu, 16 Apr 2026 10:00:00 -0700"},
                    ],
                    "mimeType": "text/plain",
                    "body": {"data": "Rmlyc3QgbWVzc2FnZQ=="},
                },
            },
            {
                "id": "msg_2",
                "payload": {
                    "headers": [
                        {"name": "Subject", "value": "Re: Team Sync"},
                        {"name": "From", "value": "Sam <sam@example.com>"},
                        {"name": "Date", "value": "Thu, 16 Apr 2026 10:05:00 -0700"},
                    ],
                    "mimeType": "text/plain",
                    "body": {"data": "U2Vjb25kIG1lc3NhZ2U="},
                },
            },
        ]
    }

    result = _format_thread_content(thread_data, "thread_123")

    assert "Subject: Team Sync" in result
    assert "Thread ID: thread_123" in result
    assert "Message 1" in result
    assert "Message ID: msg_1" in result
    assert "Subject: Re: Team Sync" in result
    assert "=== Message 1 ===" not in result


def test_format_thread_content_raw_preserves_plain_text_body_whitespace():
    thread_data = {
        "messages": [
            {
                "id": "msg_1",
                "payload": {
                    "headers": [
                        {"name": "Subject", "value": "Team Sync"},
                        {"name": "From", "value": "Alex <alex@example.com>"},
                        {"name": "Date", "value": "Thu, 16 Apr 2026 10:00:00 -0700"},
                    ],
                    "mimeType": "text/plain",
                    "body": {
                        "data": "TGluZSAxCgoKICAgIGluZGVudGVkCmxhc3QgbGluZSAgIAo="
                    },
                },
            }
        ]
    }

    result = _format_thread_content(thread_data, "thread_123", output_format="raw")

    assert "=== Message 1 ===" in result
    assert "Line 1\n\n\n    indented\nlast line   \n" in result

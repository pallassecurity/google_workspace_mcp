from gmail.gmail_tools import (
    HTML_RENDERED_BODY_TRUNCATE_LIMIT,
    HTML_RENDERED_BODY_TRUNCATION_NOTICE,
    _format_body_content,
)


def test_format_body_content_converts_html_to_readable_text_by_default():
    html_body = """
    <!DOCTYPE html>
    <html>
      <head>
        <title>Ignore me</title>
        <style>.hidden { display:none; }</style>
      </head>
      <body>
        <div style="display:none">Hidden preheader text</div>
        <div>
          <h1>Weekly Update</h1>
          <p>Hello team,</p>
          <p>Here is the <a href="https://example.com">status update</a>.</p>
          <ul>
            <li>Item one</li>
            <li>Item two</li>
          </ul>
          <script>console.log("ignore me")</script>
        </div>
      </body>
    </html>
    """

    result = _format_body_content("", html_body)

    assert "# Weekly Update" in result
    assert "Hello team," in result
    assert "Here is the status update." in result
    assert "- Item one" in result
    assert "- Item two" in result
    assert "Hidden preheader text" not in result
    assert "<html" not in result.lower()
    assert "<head" not in result.lower()
    assert "DOCTYPE" not in result
    assert "console.log" not in result


def test_format_body_content_raw_keeps_original_html():
    html_body = "<html><body><p>Hello</p></body></html>"

    result = _format_body_content("", html_body, output_format="raw")

    assert result == html_body


def test_format_body_content_raw_keeps_original_plain_text():
    text_body = "Line 1\n\n    indented\nline 3   \n"

    result = _format_body_content(text_body, "", output_format="raw")

    assert result == text_body


def test_format_body_content_strips_hidden_preheader_with_unquoted_style():
    html_body = "<div style=display:none>Hidden preheader text</div><p>Visible text</p>"

    result = _format_body_content("", html_body)

    assert "Hidden preheader text" not in result
    assert "Visible text" in result


def test_format_body_content_strips_nested_hidden_wrapper_with_same_tag():
    html_body = (
        '<div style="display:none"><div>Hidden 1</div>Hidden 2</div>'
        "<p>Visible text</p>"
    )

    result = _format_body_content("", html_body)

    assert "Hidden 1" not in result
    assert "Hidden 2" not in result
    assert "Visible text" in result


def test_format_body_content_preserves_visible_text_after_malformed_hidden_block():
    html_body = (
        '<div style="display:none"><p>Hidden<p>Still hidden</div>'
        "<p>Visible text</p>"
    )

    result = _format_body_content("", html_body)

    assert "Hidden" not in result
    assert "Still hidden" not in result
    assert "Visible text" in result


def test_format_body_content_does_not_hide_opacity_point_five():
    html_body = '<div style="opacity:0.5">Visible text</div>'

    result = _format_body_content("", html_body)

    assert "Visible text" in result


def test_format_body_content_does_not_hide_small_nonzero_font_size():
    html_body = '<div style="font-size:0.8em">Visible text</div>'

    result = _format_body_content("", html_body)

    assert "Visible text" in result


def test_format_body_content_truncates_large_rendered_html_output():
    html_body = "<p>Hello world.</p>" * 5000

    result = _format_body_content("", html_body)

    assert result.endswith(HTML_RENDERED_BODY_TRUNCATION_NOTICE)
    assert len(result) <= HTML_RENDERED_BODY_TRUNCATE_LIMIT

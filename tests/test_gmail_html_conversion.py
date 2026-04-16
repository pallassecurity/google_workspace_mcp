from gmail.gmail_tools import _format_body_content


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

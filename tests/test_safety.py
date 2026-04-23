"""Safety tests for HTML/Markdown output.

Verifies that user-authored content cannot inject scripts or break
the HTML structure of the generated site.
"""

from __future__ import annotations

from geek42.blog import _render_index
from geek42.feeds import generate_rss
from geek42.models import SiteConfig
from geek42.renderer import body_to_html

from .conftest import make_item

# -- body_to_html sanitization --


class TestBodyToHtmlSafety:
    def test_strips_script_tags(self) -> None:
        html = body_to_html('Hello <script>alert("XSS")</script> world')
        assert "<script>" not in html
        assert "alert" not in html

    def test_strips_event_handlers(self) -> None:
        html = body_to_html('<img src="x" onerror="alert(1)">')
        assert "onerror" not in html

    def test_strips_javascript_urls(self) -> None:
        html = body_to_html('<a href="javascript:alert(1)">click</a>')
        assert "javascript:" not in html

    def test_strips_style_with_expression(self) -> None:
        html = body_to_html('<div style="background:url(javascript:alert(1))">x</div>')
        assert "javascript:" not in html

    def test_strips_iframe(self) -> None:
        html = body_to_html('<iframe src="https://evil.com"></iframe>')
        assert "<iframe" not in html

    def test_strips_object_embed(self) -> None:
        html = body_to_html('<object data="evil.swf"></object><embed src="evil.swf">')
        assert "<object" not in html
        assert "<embed" not in html

    def test_preserves_safe_html(self) -> None:
        html = body_to_html("This is **bold** and *italic* text.")
        # Markdown should produce <strong> and <em>
        assert "<strong>" in html or "<em>" in html

    def test_preserves_paragraphs(self) -> None:
        html = body_to_html("First paragraph.\n\nSecond paragraph.")
        assert "<p>" in html

    def test_safe_urls_autolinked(self) -> None:
        html = body_to_html("Visit https://gentoo.org for more info.")
        assert "https://gentoo.org" in html
        assert "<a" in html

    def test_empty_body(self) -> None:
        html = body_to_html("")
        assert isinstance(html, str)

    def test_body_with_only_whitespace(self) -> None:
        html = body_to_html("   \n\n  \n")
        assert isinstance(html, str)


# -- URL auto-linker injection --


class TestUrlAutoLinker:
    def test_url_with_quote_injection(self) -> None:
        html = body_to_html('Check https://x.com"onclick="alert(1) for info')
        # The onclick should be in the URL text, not as an actual HTML attribute
        # that could execute. nh3 ensures quotes are properly escaped.
        assert 'onclick="alert' not in html or "&quot;" in html

    def test_url_with_angle_bracket_injection(self) -> None:
        html = body_to_html("Check https://x.com><script>alert(1)</script> end")
        assert "<script>" not in html


# -- Markdown table injection in blog index --


class TestMarkdownTableInjection:
    def test_pipe_in_title_escaped(self) -> None:
        items = [make_item(title="Foo | Bar")]
        index = _render_index(items, "news")
        # The pipe should be escaped so it doesn't break the table
        assert "\\|" in index

    def test_link_in_title_safe(self) -> None:
        items = [make_item(title="[click](https://evil.com)")]
        index = _render_index(items, "news")
        # Should appear as literal text in the table cell, not a nested link
        assert "[click]" in index


# -- Feed XML escaping --


class TestFeedXmlEscaping:
    def test_rss_body_escaped(self) -> None:
        items = [make_item(body='<script>alert("XSS")</script>')]
        cfg = SiteConfig(
            title="Test",
            description="Test",
            base_url="https://test.example.com",
            author="Test",
        )
        xml_str = generate_rss(items, cfg)
        # In the serialized XML output, angle brackets in text content
        # are escaped to &lt; and &gt; by ElementTree
        assert "<script>alert" not in xml_str

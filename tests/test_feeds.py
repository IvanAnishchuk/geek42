"""Tests for RSS and Atom feed generation."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import date

from geek42.feeds import generate_atom, generate_rss
from geek42.models import NewsItem, SiteConfig


def _make_items() -> list[NewsItem]:
    return [
        NewsItem(
            id="2025-11-30-migration",
            title="Migration News",
            authors=["Dev One <one@gentoo.org>"],
            posted=date(2025, 11, 30),
            body="Migration body text.",
        ),
        NewsItem(
            id="2024-06-01-update",
            title="Important Update",
            authors=["Dev Two <two@gentoo.org>", "Dev Three <three@gentoo.org>"],
            posted=date(2024, 6, 1),
            body="Update body text.",
        ),
    ]


def _config() -> SiteConfig:
    return SiteConfig(
        title="Test Feed",
        description="Test feed description",
        base_url="https://test.example.com",
        author="Test Author",
    )


def test_rss_valid_xml() -> None:
    xml_str = generate_rss(_make_items(), _config())
    root = ET.fromstring(xml_str)

    assert root.tag == "rss"
    assert root.attrib["version"] == "2.0"

    channel = root.find("channel")
    assert channel is not None
    assert channel.findtext("title") == "Test Feed"
    assert channel.findtext("description") == "Test feed description"

    items = channel.findall("item")
    assert len(items) == 2
    assert items[0].findtext("title") == "Migration News"
    assert "2025-11-30-migration.html" in (items[0].findtext("link") or "")


def test_rss_has_authors() -> None:
    xml_str = generate_rss(_make_items(), _config())
    root = ET.fromstring(xml_str)
    channel = root.find("channel")
    assert channel is not None
    second_item = channel.findall("item")[1]
    authors = second_item.findall("author")
    assert len(authors) == 2


def test_atom_valid_xml() -> None:
    xml_str = generate_atom(_make_items(), _config())
    root = ET.fromstring(xml_str)

    ns = "http://www.w3.org/2005/Atom"
    assert root.tag == f"{{{ns}}}feed"
    assert root.findtext(f"{{{ns}}}title") == "Test Feed"

    entries = root.findall(f"{{{ns}}}entry")
    assert len(entries) == 2
    assert entries[0].findtext(f"{{{ns}}}title") == "Migration News"


def test_atom_has_self_link() -> None:
    xml_str = generate_atom(_make_items(), _config())
    root = ET.fromstring(xml_str)
    ns = "http://www.w3.org/2005/Atom"
    links = root.findall(f"{{{ns}}}link")
    self_links = [link for link in links if link.get("rel") == "self"]
    assert len(self_links) == 1
    assert "atom.xml" in (self_links[0].get("href") or "")


def test_atom_entry_has_content() -> None:
    xml_str = generate_atom(_make_items(), _config())
    root = ET.fromstring(xml_str)
    ns = "http://www.w3.org/2005/Atom"
    entry = root.findall(f"{{{ns}}}entry")[0]
    content = entry.find(f"{{{ns}}}content")
    assert content is not None
    assert content.text == "Migration body text."

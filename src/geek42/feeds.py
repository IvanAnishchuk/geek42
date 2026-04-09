"""Generate RSS 2.0 and Atom 1.0 feeds.

Both feed formats share the same news item input but produce different
XML structures. The implementations use stdlib :mod:`xml.etree.ElementTree`
to avoid pulling in a feed-generation dependency.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import UTC, datetime, time
from email.utils import format_datetime

from .models import NewsItem, SiteConfig

_ATOM_NS = "http://www.w3.org/2005/Atom"

#: Maximum length of the description/summary excerpts in feed entries.
#: Most aggregators truncate further; this just keeps payloads small.
MAX_FEED_SUMMARY_LEN = 500


def _to_datetime(item: NewsItem) -> datetime:
    """Promote a news item's date-only ``posted`` field to a UTC datetime."""
    return datetime.combine(item.posted, time.min, tzinfo=UTC)


def _xml_to_str(root: ET.Element) -> str:
    """Serialize an ElementTree element to a UTF-8 XML string with declaration."""
    ET.indent(root)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode")


def generate_rss(items: list[NewsItem], config: SiteConfig) -> str:
    """Generate an RSS 2.0 feed XML document.

    :param items: News items to include, in the order they should appear.
    :param config: Site config providing the channel title, description,
        and base URL used to construct per-item permalinks.
    :returns: A complete XML document string with the XML declaration.
    """
    rss = ET.Element("rss", version="2.0")
    chan = ET.SubElement(rss, "channel")

    ET.SubElement(chan, "title").text = config.title
    ET.SubElement(chan, "link").text = config.base_url
    ET.SubElement(chan, "description").text = config.description
    ET.SubElement(chan, "lastBuildDate").text = format_datetime(datetime.now(UTC))

    for item in items:
        entry = ET.SubElement(chan, "item")
        link = f"{config.base_url}/posts/{item.id}.html"
        ET.SubElement(entry, "title").text = item.title
        ET.SubElement(entry, "link").text = link
        ET.SubElement(entry, "guid").text = link
        ET.SubElement(entry, "pubDate").text = format_datetime(_to_datetime(item))
        ET.SubElement(entry, "description").text = item.body[:MAX_FEED_SUMMARY_LEN]
        for author in item.authors:
            ET.SubElement(entry, "author").text = author

    return _xml_to_str(rss)


def generate_atom(items: list[NewsItem], config: SiteConfig) -> str:
    """Generate an Atom 1.0 feed XML document.

    :param items: News items to include, in the order they should appear.
    :param config: Site config providing the feed title, author, and base
        URL used to construct per-entry IDs and permalinks.
    :returns: A complete XML document string with the XML declaration.
    """
    ET.register_namespace("", _ATOM_NS)
    ns = _ATOM_NS

    feed = ET.Element(f"{{{ns}}}feed")
    ET.SubElement(feed, f"{{{ns}}}title").text = config.title
    ET.SubElement(feed, f"{{{ns}}}id").text = config.base_url

    alt_link = ET.SubElement(feed, f"{{{ns}}}link")
    alt_link.set("href", config.base_url)
    alt_link.set("rel", "alternate")

    self_link = ET.SubElement(feed, f"{{{ns}}}link")
    self_link.set("href", f"{config.base_url}/atom.xml")
    self_link.set("rel", "self")

    ET.SubElement(feed, f"{{{ns}}}updated").text = datetime.now(UTC).isoformat()
    author_el = ET.SubElement(feed, f"{{{ns}}}author")
    ET.SubElement(author_el, f"{{{ns}}}name").text = config.author

    for item in items:
        entry = ET.SubElement(feed, f"{{{ns}}}entry")
        ET.SubElement(entry, f"{{{ns}}}title").text = item.title
        item_url = f"{config.base_url}/posts/{item.id}.html"
        ET.SubElement(entry, f"{{{ns}}}id").text = item_url

        entry_link = ET.SubElement(entry, f"{{{ns}}}link")
        entry_link.set("href", item_url)

        dt = _to_datetime(item).isoformat()
        ET.SubElement(entry, f"{{{ns}}}updated").text = dt
        ET.SubElement(entry, f"{{{ns}}}published").text = dt

        for a in item.authors:
            a_el = ET.SubElement(entry, f"{{{ns}}}author")
            ET.SubElement(a_el, f"{{{ns}}}name").text = a

        summary = ET.SubElement(entry, f"{{{ns}}}summary")
        summary.set("type", "text")
        summary.text = item.body[:MAX_FEED_SUMMARY_LEN]

        content = ET.SubElement(entry, f"{{{ns}}}content")
        content.set("type", "text")
        content.text = item.body

    return _xml_to_str(feed)

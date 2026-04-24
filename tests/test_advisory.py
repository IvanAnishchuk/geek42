"""Tests for advisory GLSA XML generation."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import date

from geek42.advisory import glsa_filename, news_to_glsa_xml

from .conftest import make_item


def test_glsa_xml_basic() -> None:
    item = make_item(
        id="2026-05-01-vuln",
        title="Security Fix",
        item_type="advisory",
        advisory_severity="high",
        advisory_cves=["CVE-2026-12345"],
        advisory_affected=["<0.5.0"],
        advisory_fixed="0.5.0",
        display_if_installed=["dev-python/geek42"],
        posted=date(2026, 5, 1),
        body="A vulnerability was found.\n\nUpgrade immediately.",
    )
    xml = news_to_glsa_xml(item)
    assert '<?xml version="1.0"' in xml
    assert "<!DOCTYPE glsa" in xml
    assert 'id="202605-01"' in xml
    assert "<title>Security Fix</title>" in xml
    assert "<severity>High</severity>" in xml
    assert "<name>dev-python/geek42</name>" in xml
    assert "<announced>2026-05-01</announced>" in xml
    root = ET.fromstring(xml)
    uri = root.find(".//references/uri")
    assert uri is not None
    assert uri.text == "CVE-2026-12345"
    assert uri.get("link") == "https://nvd.nist.gov/vuln/detail/CVE-2026-12345"
    assert root.find(".//resolution/code") is not None
    assert "0.5.0" in (root.findtext(".//resolution/p") or "")


def test_glsa_xml_severity_mapping() -> None:
    mapping = [("critical", "High"), ("high", "High"), ("medium", "Normal"), ("low", "Low")]
    for sev, expected in mapping:
        item = make_item(item_type="advisory", advisory_severity=sev)
        xml = news_to_glsa_xml(item)
        assert f"<severity>{expected}</severity>" in xml


def test_glsa_xml_multiple_cves() -> None:
    item = make_item(
        item_type="advisory",
        advisory_cves=["CVE-2026-11111", "CVE-2026-22222"],
    )
    xml = news_to_glsa_xml(item)
    assert "CVE-2026-11111" in xml
    assert "CVE-2026-22222" in xml


def test_glsa_xml_no_cves() -> None:
    item = make_item(item_type="advisory", advisory_cves=[])
    xml = news_to_glsa_xml(item)
    assert "No CVE assigned" in xml


def test_glsa_xml_no_fixed_version() -> None:
    item = make_item(item_type="advisory", advisory_fixed="")
    xml = news_to_glsa_xml(item)
    assert "See advisory for details" in xml


def test_glsa_filename_format() -> None:
    item = make_item(id="2026-05-01-fix", posted=date(2026, 5, 1))
    assert glsa_filename(item) == "glsa-202605-01.xml"


def test_glsa_filename_different_dates() -> None:
    item = make_item(id="2025-12-15-patch", posted=date(2025, 12, 15))
    assert glsa_filename(item) == "glsa-202512-15.xml"


def test_glsa_xml_synopsis_truncation() -> None:
    long_body = "A" * 200 + "\n\nSecond paragraph."
    item = make_item(item_type="advisory", body=long_body)
    xml = news_to_glsa_xml(item)
    # Synopsis should be truncated to ~160 chars
    assert "<synopsis>" in xml
    # The full 200-char string should not be in synopsis
    assert "A" * 200 not in xml.split("<synopsis>")[1].split("</synopsis>")[0]


def test_glsa_xml_multiline_body() -> None:
    item = make_item(
        item_type="advisory",
        body="First paragraph.\n\nSecond paragraph.\n\nThird.",
    )
    xml = news_to_glsa_xml(item)
    # Each paragraph becomes a <p> element
    assert xml.count("<p>") >= 3

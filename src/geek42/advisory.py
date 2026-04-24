"""Generate GLSA-compatible XML from advisory news items.

Advisory items (``item_type == "advisory"``) can be compiled into
Gentoo Linux Security Advisory XML files that ``glsa-check`` and
other Portage tools can consume from an overlay.

The generated XML follows the GLSA DTD at
``https://www.gentoo.org/dtd/glsa.dtd``.
"""

from __future__ import annotations

import re
from xml.etree.ElementTree import Element, SubElement, indent, tostring

from .models import NewsItem

#: Map our severity values to GLSA severity/impact values.
_SEVERITY_MAP: dict[str, str] = {
    "critical": "High",
    "high": "High",
    "medium": "Normal",
    "low": "Low",
    "minimal": "Low",
}


def _glsa_id(item: NewsItem) -> str:
    """Derive a GLSA-style identifier from a news item.

    Converts a date-based item ID like ``2026-05-01-security-fix``
    into a GLSA ID like ``202605-01``.
    """
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", item.id)
    if not m:
        return "000000-01"
    year, month, day = m.group(1), m.group(2), m.group(3)
    return f"{year}{month}-{day}"


def _glsa_severity(item: NewsItem) -> str:
    """Map advisory severity to GLSA severity value."""
    return _SEVERITY_MAP.get(item.advisory_severity.lower(), "Normal")


def _first_paragraph(body: str) -> str:
    """Extract the first paragraph of a body as the synopsis."""
    for para in body.split("\n\n"):
        stripped = para.strip()
        if stripped:
            return " ".join(stripped.split())
    return body.strip()[:160]


def news_to_glsa_xml(item: NewsItem) -> str:
    """Generate GLSA-compatible XML from an advisory :class:`NewsItem`.

    The output is a complete XML document with DOCTYPE declaration,
    suitable for placing in ``metadata/glsa/`` of a Gentoo overlay.

    :param item: A :class:`NewsItem` with ``item_type == "advisory"``.
    :returns: XML string.
    """
    glsa_id = _glsa_id(item)
    severity = _glsa_severity(item)

    root = Element("glsa", id=glsa_id)

    SubElement(root, "title").text = item.title

    synopsis = _first_paragraph(item.body)
    if len(synopsis) > 160:
        synopsis = synopsis[:157] + "..."
    SubElement(root, "synopsis").text = synopsis

    # Product — use first package or a generic name
    product = SubElement(root, "product", type="ebuild")
    pkg_name = item.display_if_installed[0] if item.display_if_installed else "unknown"
    SubElement(product, "name").text = pkg_name

    SubElement(root, "announced").text = item.posted.isoformat()
    SubElement(root, "revised", count=str(item.revision)).text = item.posted.isoformat()

    SubElement(root, "access").text = "Remote"
    SubElement(root, "severity").text = severity

    # Description — full body
    desc = SubElement(root, "description")
    for para in item.body.split("\n\n"):
        stripped = para.strip()
        if stripped:
            SubElement(desc, "p").text = stripped

    # Impact
    impact = SubElement(root, "impact", type=severity.lower())
    SubElement(impact, "p").text = f"Severity: {item.advisory_severity or 'unknown'}."

    # Resolution
    resolution = SubElement(root, "resolution")
    if item.advisory_fixed:
        SubElement(resolution, "p").text = f"Upgrade to version {item.advisory_fixed} or later."
        if item.display_if_installed:
            code = SubElement(resolution, "code")
            code.text = (
                f"# emerge --sync\n"
                f"# emerge --ask --oneshot --verbose "
                f'">={item.display_if_installed[0]}-{item.advisory_fixed}"'
            )
    else:
        SubElement(resolution, "p").text = "See advisory for details."

    # References — CVE links
    references = SubElement(root, "references")
    for cve in item.advisory_cves:
        uri = SubElement(
            references,
            "uri",
            link=f"https://nvd.nist.gov/vuln/detail/{cve}",
        )
        uri.text = cve
    if not item.advisory_cves:
        uri = SubElement(references, "uri", link="")
        uri.text = "No CVE assigned"

    # Metadata
    if item.authors:
        meta = SubElement(root, "metadata")
        meta.set("tag", "submitter")
        meta.text = item.authors[0]

    # Serialize with XML declaration and DOCTYPE
    indent(root, space="  ")
    xml_body = tostring(root, encoding="unicode", xml_declaration=False)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE glsa SYSTEM "http://www.gentoo.org/dtd/glsa.dtd">\n'
        f"{xml_body}\n"
    )


def glsa_filename(item: NewsItem) -> str:
    """Return the conventional filename for a GLSA XML file.

    Example: ``glsa-202605-01.xml`` for an item posted 2026-05-01.
    """
    return f"glsa-{_glsa_id(item)}.xml"

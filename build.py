"""Build the reading-list site from data/readings.yaml into _site/.

    python build.py                      # validate and build
    python -m http.server -d _site       # preview at http://localhost:8000
"""

import datetime as dt
import hashlib
import html
import json
import shutil
import sys
from pathlib import Path
from urllib.parse import urlparse
from xml.sax.saxutils import escape as xml_escape

import yaml

ROOT = Path(__file__).parent
DATA = ROOT / "data" / "readings.yaml"
TEMPLATE = ROOT / "templates" / "index.html"
STATIC = ROOT / "static"
OUT = ROOT / "_site"

SITE_URL = "https://reading.nataliebhogg.com/"
REPO_URL = "https://github.com/nataliehogg/ai_reading_list"

TYPES = {
    "paper": "Paper",
    "essay": "Essay",
    "news": "News",
    "interview": "Interview",
    "resource": "Resource",
}
FIELDS = {"astro": "Astro/cosmo"}  # labels for `field` values; others are title-cased
STATUSES = {"read": "Read", "to-read": "To read"}

REQUIRED = {"title", "url", "type", "added"}
OPTIONAL = {"authors", "published", "field", "tags", "status", "mine", "note"}


# --- loading and validation -------------------------------------------------

def as_list(value):
    if value is None:
        return []
    return [value] if isinstance(value, str) else value


def load():
    raw = yaml.safe_load(DATA.read_text(encoding="utf-8")) or []
    errors, entries, seen = [], [], {}

    for i, e in enumerate(raw, 1):
        if not isinstance(e, dict):
            errors.append(f"entry {i}: expected a mapping, got {type(e).__name__}")
            continue
        where = f"entry {i} ({e.get('title', 'untitled')!r})"

        for key in sorted(REQUIRED - e.keys()):
            errors.append(f"{where}: missing `{key}`")
        for key in sorted(e.keys() - REQUIRED - OPTIONAL):
            errors.append(f"{where}: unknown field `{key}` (typo?)")
        if REQUIRED - e.keys():
            continue

        url = str(e["url"])
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            errors.append(f"{where}: `url` is not a web address: {url}")
        if url in seen:
            errors.append(f"{where}: duplicate url (also entry {seen[url]})")
        seen[url] = i

        if e["type"] not in TYPES:
            errors.append(f"{where}: `type` must be one of {', '.join(TYPES)}")
        if not isinstance(e["added"], dt.date):
            errors.append(f"{where}: `added` must be a date like 2026-10-20")

        published = e.get("published")
        if published is not None and not (
            isinstance(published, dt.date) or (isinstance(published, int) and 1800 < published < 2200)
        ):
            errors.append(f"{where}: `published` must be a date or a year")

        field, tags = as_list(e.get("field")), as_list(e.get("tags"))
        for name, values in (("field", field), ("tags", tags)):
            if not all(isinstance(v, str) for v in values):
                errors.append(f"{where}: `{name}` must be a list of words")

        status = e.get("status") or "read"
        if status not in STATUSES:
            errors.append(f"{where}: `status` must be one of {', '.join(STATUSES)}")
        if not isinstance(e.get("mine", False), bool):
            errors.append(f"{where}: `mine` must be true or false")

        entries.append({
            "title": str(e["title"]).strip(),
            "url": url,
            "type": e["type"],
            "added": e["added"],
            "authors": str(e.get("authors") or "").strip(),
            "published": published,
            "year": published.year if isinstance(published, dt.date) else published,
            "field": [str(v).lower() for v in field],
            "tags": [str(v).lower() for v in tags],
            "status": status,
            "mine": bool(e.get("mine", False)),
            "note": str(e.get("note") or "").strip(),
            "domain": parsed.netloc.removeprefix("www."),
        })

    if errors:
        print(f"{DATA.relative_to(ROOT)} has {len(errors)} problem(s):", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)
    return entries


# --- rendering ---------------------------------------------------------------

def esc(s):
    return html.escape(str(s), quote=True)


def fmt_date(d):
    return f"{d.day} {d:%b %Y}"


def label(facet, value):
    if facet == "type":
        return TYPES[value]
    if facet == "status":
        return STATUSES[value]
    if facet == "origin":
        return "Me" if value == "me" else FIELDS.get(value, value.title())
    return value


def origins(e):
    return e["field"] + (["me"] if e["mine"] else [])


def sort_title(title):
    return title.lstrip("‘’'\"“”").lower()


def render_item(e):
    pills = []
    if e["mine"]:
        pills.append('<span class="pill pill-mine">By me</span>')
    if e["status"] == "to-read":
        pills.append('<span class="pill pill-todo">To read</span>')
    for f in e["field"]:
        if f != "astro":
            pills.append(f'<span class="pill">{esc(label("origin", f))}</span>')

    star = ""
    if "astro" in e["field"]:
        star = ('<span class="star" title="Written by someone in the astro/cosmo-sphere" '
                'aria-label="Astro/cosmo author">★</span>')

    byline = [f'<span class="authors">{esc(e["authors"])}</span>'] if e["authors"] else []
    if e["year"]:
        byline.append(f'<span>{e["year"]}</span>')
    byline.append(f'<span class="domain">{esc(e["domain"])}</span>')

    note = f'<p class="note">{esc(e["note"])}</p>' if e["note"] else ""
    tags = ""
    if e["tags"]:
        tags = '<ul class="tags">' + "".join(f"<li>{esc(t)}</li>" for t in e["tags"]) + "</ul>"

    published = e["published"]
    published_key = published.isoformat() if isinstance(published, dt.date) else (f"{published}-00-00" if published else "")

    return f"""
<li class="item" data-type="{e['type']}" data-origin="{esc(' '.join(origins(e)))}" data-status="{e['status']}" data-tags="{esc(' '.join(e['tags']))}" data-added="{e['added'].isoformat()}" data-published="{published_key}" data-sort-title="{esc(sort_title(e['title']))}">
  <div class="item-side">
    <span class="type">{TYPES[e['type']]}</span>
    <time datetime="{e['added'].isoformat()}" title="Date added to the list">{fmt_date(e['added'])}</time>
    {''.join(pills)}
  </div>
  <div class="item-main">
    <h2 class="item-title"><a href="{esc(e['url'])}">{esc(e['title'])}</a>{star}</h2>
    <p class="byline">{' <span class="sep" aria-hidden="true">·</span> '.join(byline)}</p>
    {note}{tags}
  </div>
</li>""".strip()


def render_facets(entries):
    def counts(key):
        out = {}
        for e in entries:
            values = [e[key]] if key in ("type", "status") else (origins(e) if key == "origin" else e[key])
            for v in values:
                out[v] = out.get(v, 0) + 1
        return out

    groups = [
        ("type", "Type", [t for t in TYPES if t in counts("type")]),
        ("origin", "Written by", sorted(counts("origin"), key=lambda v: (v == "me", v))),
        ("status", "Status", [s for s in STATUSES if s in counts("status")]),
        ("tags", "Topic", sorted(counts("tags"))),
    ]
    html_groups = []
    for key, title, values in groups:
        if not values:
            continue
        n = counts(key)
        chips = "".join(
            f'<button type="button" class="chip" data-value="{esc(v)}" aria-pressed="false">'
            f'{"<span class=star aria-hidden=true>★</span>" if v == "astro" else ""}'
            f'{esc(label(key, v))}<span class="n">{n[v]}</span></button>'
            for v in values
        )
        html_groups.append(
            f'<div class="facet" data-facet="{key}" role="group" aria-label="{title}">'
            f'<span class="facet-label">{title}</span><div class="chips">{chips}</div></div>'
        )
    return "\n".join(html_groups)


def render_feed(entries, updated):
    latest = sorted(entries, key=lambda e: (e["added"], e["title"]), reverse=True)[:40]
    items = []
    for e in latest:
        summary = " · ".join(filter(None, [TYPES[e["type"]], e["authors"], e["note"]]))
        items.append(f"""  <entry>
    <title>{xml_escape(e['title'])}</title>
    <link href="{xml_escape(e['url'])}"/>
    <id>{xml_escape(e['url'])}</id>
    <updated>{e['added'].isoformat()}T00:00:00Z</updated>
    <summary>{xml_escape(summary)}</summary>
  </entry>""")
    return f"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>AI reading list</title>
  <subtitle>New additions to Natalie B. Hogg's AI reading list</subtitle>
  <link href="{SITE_URL}"/>
  <link rel="self" href="{SITE_URL}feed.xml"/>
  <id>{SITE_URL}</id>
  <updated>{updated.isoformat()}T00:00:00Z</updated>
  <author><name>Natalie B. Hogg</name></author>
{chr(10).join(items)}
</feed>
"""


def asset_version(path):
    return hashlib.sha1(path.read_bytes()).hexdigest()[:8]


def build():
    entries = load()
    entries.sort(key=lambda e: (e["added"], e["title"]), reverse=True)
    updated = max(e["added"] for e in entries)

    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(STATIC, OUT / "static")

    page = TEMPLATE.read_text(encoding="utf-8")
    values = {
        "count": str(len(entries)),
        "facets": render_facets(entries),
        "items": "\n".join(render_item(e) for e in entries),
        "updated": fmt_date(updated),
        "updated_iso": updated.isoformat(),
        "site_url": SITE_URL,
        "repo_url": REPO_URL,
        "css_v": asset_version(STATIC / "style.css"),
        "js_v": asset_version(STATIC / "app.js"),
    }
    for key, value in values.items():
        page = page.replace("{{" + key + "}}", value)
    if "{{" in page:
        sys.exit("templates/index.html has an unknown {{placeholder}}")
    (OUT / "index.html").write_text(page, encoding="utf-8")

    def jsonable(e):
        out = {k: v for k, v in e.items() if k not in ("year", "domain")}
        out["added"] = e["added"].isoformat()
        if isinstance(e["published"], dt.date):
            out["published"] = e["published"].isoformat()
        return out

    (OUT / "readings.json").write_text(
        json.dumps([jsonable(e) for e in entries], ensure_ascii=False, indent=1), encoding="utf-8"
    )
    (OUT / "feed.xml").write_text(render_feed(entries, updated), encoding="utf-8")
    (OUT / ".nojekyll").touch()
    print(f"Built {len(entries)} readings into {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    build()

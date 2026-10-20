"""Build the reading-list site from data/readings.yaml into _site/.

    python build.py                      # validate and build
    python -m http.server -d _site       # preview at http://localhost:8000

data/to-read.yaml is validated too, but never published.
"""

import datetime as dt
import hashlib
import html
import json
import shutil
import sys
from pathlib import Path
from urllib.parse import urlencode, urlparse
from xml.sax.saxutils import escape as xml_escape

import yaml

ROOT = Path(__file__).parent
DATA = ROOT / "data" / "readings.yaml"
TO_READ = ROOT / "data" / "to-read.yaml"
TEMPLATE = ROOT / "templates" / "index.html"
STATIC = ROOT / "static"
OUT = ROOT / "_site"

SITE_URL = "https://reading.nataliebhogg.com/"
REPO_URL = "https://github.com/nataliehogg/ai_reading_list"

TYPES = ("paper", "essay", "news", "interview", "resource")

REQUIRED = {"title", "url", "type", "added"}
OPTIONAL = {"authors", "sort_as", "published", "field", "tags", "start_here", "note"}


# --- loading and validation -------------------------------------------------

def as_list(value):
    if value is None:
        return []
    return [value] if isinstance(value, str) else value


def load(path):
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or []
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
            if not all(isinstance(v, str) and v.strip() and "|" not in v for v in values):
                errors.append(f"{where}: `{name}` must be a list of words (no `|`)")
        if not isinstance(e.get("start_here", False), bool):
            errors.append(f"{where}: `start_here` must be true or false")

        entries.append({
            "title": str(e["title"]).strip(),
            "url": url,
            "type": e["type"],
            "added": e["added"],
            "authors": str(e.get("authors") or "").strip(),
            "published": published,
            "year": published.year if isinstance(published, dt.date) else published,
            "sort_as": str(e.get("sort_as") or "").strip(),
            "field": [str(v).strip() for v in field],
            "tags": [str(v).strip() for v in tags],
            "start_here": bool(e.get("start_here", False)),
            "note": str(e.get("note") or "").strip(),
            "domain": parsed.netloc.removeprefix("www."),
        })

    if errors:
        print(f"{path.relative_to(ROOT)} has {len(errors)} problem(s):", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)
    return entries


# --- rendering ---------------------------------------------------------------

def esc(s):
    return html.escape(str(s), quote=True)


def fmt_date(d):
    return f"{d.day} {d:%b %Y}"


def sort_key(e):
    """First author's surname (or `sort_as`), then title; entries without authors go last."""
    title = e["title"].lstrip("‘’'\"“”").lower()
    name = e["sort_as"] or e["authors"].split(",")[0].removesuffix("et al.").strip()
    if not name:
        return (1, "", title)
    surname = name if e["sort_as"] else name.split()[-1]
    return (0, surname.lower().removeprefix("d’").removeprefix("d'"), title)


def filter_link(kind, value, text, cls="", title=""):
    """A link that filters the list; works as a plain shareable URL too."""
    attrs = f' class="{cls}"' if cls else ""
    attrs += f' title="{esc(title)}"' if title else ""
    return (f'<a href="?{esc(urlencode({kind: value}))}" data-kind="{kind}" '
            f'data-value="{esc(value)}"{attrs}>{esc(text)}</a>')


def render_item(e):
    meta = filter_link("type", e["type"], e["type"], "meta-link")

    byline = [f'<span class="authors">{esc(e["authors"])}</span>'] if e["authors"] else []
    if e["year"]:
        byline.append(f'<span>{e["year"]}</span>')
    byline.append(f'<span class="domain">{esc(e["domain"])}</span>')

    tags = []
    if e["start_here"]:
        tags.append(filter_link("start", "yes", "start here", "tag tag-start"))
    tags += [filter_link("field", f, f, "tag tag-field", "Field of origin") for f in e["field"]]
    tags += [filter_link("tag", t, t, "tag") for t in e["tags"]]

    sep = ' <span class="sep" aria-hidden="true">·</span> '
    note = f'\n  <p class="note">{esc(e["note"])}</p>' if e["note"] else ""
    tag_line = f'\n  <p class="tags">{sep.join(tags)}</p>' if tags else ""

    data = {
        "type": e["type"],
        "field": "|".join(e["field"]),
        "tag": "|".join(e["tags"]),
        "start": "yes" if e["start_here"] else "",
    }
    data_attrs = " ".join(f'data-{k}="{esc(v)}"' for k, v in data.items())

    return f"""<li class="item" {data_attrs}>
  <p class="meta">{meta}</p>
  <h2 class="item-title"><a href="{esc(e['url'])}">{esc(e['title'])}</a></h2>
  <p class="byline">{sep.join(byline)}</p>{note}{tag_line}
</li>"""


def render_tag_index(entries):
    def counted(kind, values):
        counts = {}
        for v in values:
            counts[v] = counts.get(v, 0) + 1
        links = [filter_link(kind, v, v, "tag" + (" tag-field" if kind == "field" else ""))
                 + f'<span class="n">{n}</span>'
                 for v, n in sorted(counts.items(), key=lambda kv: kv[0].lower())]
        return " ".join(f'<span class="index-entry">{link}</span>' for link in links)

    groups = [
        ("Field of origin", counted("field", [f for e in entries for f in e["field"]])),
        ("Themes", counted("tag", [t for e in entries for t in e["tags"]])),
        ("Type", counted("type", [e["type"] for e in entries])),
    ]
    return "\n".join(f'<div class="index-group"><h3>{title}</h3><p>{body}</p></div>' for title, body in groups if body)


def render_feed(entries, updated):
    latest = sorted(entries, key=lambda e: (e["added"], e["title"]), reverse=True)[:40]
    items = []
    for e in latest:
        summary = " · ".join(filter(None, [e["type"], e["authors"], e["note"]]))
        categories = "".join(f'\n    <category term="{xml_escape(t)}"/>' for t in e["field"] + e["tags"])
        items.append(f"""  <entry>
    <title>{xml_escape(e['title'])}</title>
    <link href="{xml_escape(e['url'])}"/>
    <id>{xml_escape(e['url'])}</id>
    <updated>{e['added'].isoformat()}T00:00:00Z</updated>
    <summary>{xml_escape(summary)}</summary>{categories}
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
    entries = load(DATA)
    if TO_READ.exists():
        to_read = load(TO_READ)
        overlap = {e["url"] for e in entries} & {e["url"] for e in to_read}
        if overlap:
            sys.exit("In both readings.yaml and to-read.yaml (remove from to-read):\n  " + "\n  ".join(sorted(overlap)))

    entries.sort(key=sort_key)
    updated = max(e["added"] for e in entries)

    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(STATIC, OUT / "static")

    page = TEMPLATE.read_text(encoding="utf-8")
    values = {
        "count": str(len(entries)),
        "items": "\n".join(render_item(e) for e in entries),
        "tag_index": render_tag_index(entries),
        "updated": fmt_date(updated),
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
        out = {k: v for k, v in e.items() if k not in ("year", "domain", "sort_as")}
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

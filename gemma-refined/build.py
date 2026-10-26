#!/usr/bin/env python3
"""Build the static site: content/*.md and content/posts/*.md -> dist/.

Usage:
    python3 build.py            # build into dist/
    python3 build.py --serve    # build + serve dist/ at http://localhost:8000

Workflow:
    1. Edit Markdown files in content/ and content/posts/.
    2. Drop a square photo at assets/profile.jpg (optional, .png/.webp also ok).
    3. Run `python3 build.py`.
    4. Deploy the dist/ folder (Netlify / Vercel / Cloudflare Pages / GitHub Pages).

No third-party dependencies — only the Python standard library.
"""

import html
import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from datetime import date
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
TEMPLATES = ROOT / "templates"
ASSETS = ROOT / "assets"
OUT = ROOT / "dist"

LINK_KEYS = {
    "github": "GitHub",
    "demo": "Demo",
    "paper": "Paper",
    "slides": "Slides",
    "video": "Video",
    "post": "Post",
    "link": "Link",
    "website": "Website",
    "pdf": "PDF",
    "file": "File",
    "attachment": "Attachment",
}
TAG_KEYS = {"tags", "tag", "keywords"}
# Link keys in priority order: the first one present becomes the entry's
# primary link (the clickable title); the rest render as small text links.
LINK_PRIORITY = [
    "github", "demo", "paper", "website", "link",
    "slides", "video", "post", "pdf", "file", "attachment",
]
# Keys that hold a preview image (rendered as <img>, nothing else).
IMAGE_KEYS = ("image", "figure", "poster", "thumbnail", "cover")
IMG_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg")
DOCUMENT_EXTS = (".pdf", ".ppt", ".pptx", ".odp", ".doc", ".docx")
FILE_EXTS = IMG_EXTS + DOCUMENT_EXTS
# Keys shown in the meta row (in this order when present), everything else
# unknown falls back to a generic "Key: value" span.
# ("date"/"period" are pulled out into the card header instead.)
META_ORDER = [
    "location", "role", "event",
    "degree", "status", "details",
]
DATE_KEYS = ("date", "period")

ICONS = {
    "email": ('<rect x="2" y="4" width="20" height="16" rx="2" ry="2"/>'
              '<path d="M22 6l-10 7L2 6"/>'),
    "github": ('<path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61'
               'c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 '
               '19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1'
               'A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 '
               '6.44 7A3.37 3.37 0 0 0 9 18.13V22"/>'),
    "linkedin": ('<path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 '
                 '2v7h-4v-7a6 6 0 0 1 6-6z"/><rect x="2" y="9" width="4" '
                 'height="12"/><circle cx="4" cy="4" r="2"/>'),
}


def icon(name: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
            f'fill="none" stroke="currentColor" stroke-width="2" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
            f'{ICONS[name]}</svg>')


def strip_comments(text: str) -> str:
    """Remove <!-- ... --> blocks (used for in-file instructions/examples)."""
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)


def parse_frontmatter(text: str):
    """Parse a --- key: value --- block at the top of the file."""
    meta: dict[str, str] = {}
    body = text
    m = re.match(r"\s*---\s*\n(.*?)\n---\s*\n?", text, flags=re.S)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                k = k.strip().lower()
                v = v.strip().strip("\"'")
                if k:
                    meta[k] = v
        body = text[m.end():]
    return meta, body


META_LINE = re.compile(r"^-\s*([\w\-/ ]+?)\s*:\s*(.+?)\s*$")


def parse_entries(text: str):
    """Split a section file into [{title, meta, md}] by '## Title' blocks."""
    text = strip_comments(text)
    lines = text.splitlines()
    # Drop the file-level "# Title" heading if present.
    idx = 0
    while idx < len(lines) and not lines[idx].strip():
        idx += 1
    if idx < len(lines) and re.match(r"^#(?!#)\s+", lines[idx]):
        idx += 1
    lines = lines[idx:]

    blocks: list[tuple[str, list[str]]] = []
    cur_title: str | None = None
    cur_lines: list[str] = []
    for line in lines:
        m = re.match(r"^##(?!#)\s+(.*)", line)
        if m:
            if cur_title is not None:
                blocks.append((cur_title, cur_lines))
            cur_title = m.group(1).strip()
            cur_lines = []
        elif cur_title is not None:
            cur_lines.append(line)
    if cur_title is not None:
        blocks.append((cur_title, cur_lines))

    entries = []
    for title, blines in blocks:
        # Leading "- key: value" lines are metadata.
        meta: dict[str, str] = {}
        i = 0
        while i < len(blines) and not blines[i].strip():
            i += 1
        while i < len(blines):
            if not blines[i].strip():
                i += 1
                continue
            mm = META_LINE.match(blines[i])
            if not mm:
                break
            meta[mm.group(1).strip().lower()] = mm.group(2).strip()
            i += 1
        entries.append({"title": title, "meta": meta,
                        "md": "\n".join(blines[i:]).strip()})
    return entries


def md_inline(s: str) -> str:
    """Inline Markdown: `code`, **bold**, *italic*, images, links, bare URLs."""
    codes: list[str] = []

    def stash(m):
        codes.append(m.group(1))
        return "\x00CODE%d\x00" % (len(codes) - 1)

    s = re.sub(r"`([^`\n]+?)`", stash, s)
    s = html.escape(s, quote=False)
    s = re.sub(r"!\[([^\]]*?)\]\(([^)\s]+?)(?:\s+\"[^\"]*\")?\)",
               r'<img alt="\1" src="\2" loading="lazy">', s)
    s = re.sub(r"\[([^\]]+?)\]\(([^)\s]+?)(?:\s+\"[^\"]*\")?\)",
               r'<a href="\2">\1</a>', s)
    s = re.sub(r"\*\*([^*]+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\w)\*([^*\n]+?)\*(?!\w)", r"<em>\1</em>", s)

    def autolink(m):
        url = m.group(1)
        trail = ""
        while url and url[-1] in ".,;:!?":
            trail = url[-1] + trail
            url = url[:-1]
        return f'<a href="{url}">{url}</a>{trail}'

    s = re.sub(r'(?<![="\'>])(?<![a-zA-Z>])\b(https?://[^\s<>()]+)',
               autolink, s)
    for i, code in enumerate(codes):
        s = s.replace("\x00CODE%d\x00" % i,
                      "<code>" + html.escape(code, quote=False) + "</code>")
    return s


def article_outline(md: str) -> list[dict]:
    """Headings and stable anchors for a post's on-page navigation."""
    headings = []
    counts: dict[str, int] = {}
    in_code = False
    for line in md.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        match = re.match(r"^(#{1,6})\s+(.+)", stripped)
        if not match:
            continue
        label = match.group(2).strip()
        plain = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", label)
        plain = re.sub(r"[*_`]", "", plain)
        ascii_text = unicodedata.normalize("NFKD", plain).encode("ascii", "ignore").decode().lower()
        base = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-") or "section"
        counts[base] = counts.get(base, 0) + 1
        anchor = base if counts[base] == 1 else f"{base}-{counts[base]}"
        headings.append({"id": anchor, "label": plain, "level": min(6, max(2, len(match.group(1))))})
    return headings


def render_comparison(lines: list[str]) -> str:
    """Render an authored comparison directive as escaped, selectable text."""
    context = lines[0].removeprefix(":::comparison").strip()
    fields: dict[str, list[str]] = {"prompt": [], "normal": [], "steered": []}
    current = None
    for line in lines[1:]:
        match = re.match(r"^(Prompt|Normal|Steered):\s*(.*)$", line)
        if match:
            current = match.group(1).lower()
            fields[current].append(match.group(2))
        elif current is not None:
            fields[current].append(line)
        elif line.strip():
            raise ValueError("Comparison text must follow Prompt:, Normal:, or Steered:.")
    if not all("\n".join(value).strip() for value in fields.values()):
        raise ValueError("A comparison requires a prompt and both answers.")

    def paragraphs(value: list[str]) -> str:
        return "".join("<p>" + md_inline(" ".join(part.splitlines())) + "</p>"
                       for part in re.split(r"\n\s*\n", "\n".join(value).strip()))

    panels = "".join(
        f'<section class="answer-panel answer-panel--{key}" aria-label="{label}">'
        f'<p class="answer-label"><span class="answer-indicator" aria-hidden="true"></span>{label}</p>'
        f'<blockquote>{paragraphs(fields[key])}</blockquote></section>'
        for key, label in [("normal", "Normal answer"), ("steered", "Steered answer")]
    )
    return (
        '<figure class="answer-comparison">'
        f'<figcaption class="answer-context">{md_inline(context)}</figcaption>'
        '<div class="answer-prompt"><span>Same prompt</span>'
        f'<p>{md_inline(" ".join(fields["prompt"]).strip())}</p></div>'
        f'<div class="answer-grid">{panels}</div></figure>'
    )


def md_blocks(md: str, article: bool = False) -> str:
    """Block Markdown: headings, quotes, lists, fenced code, hr, paragraphs."""
    out: list[str] = []
    lines = md.splitlines()
    i = 0
    n = len(lines)
    headings = iter(article_outline(md)) if article else iter(())

    def flush_para(buf: list[str]):
        if buf:
            out.append("<p>" + md_inline(" ".join(buf)) + "</p>")
            buf.clear()

    para: list[str] = []
    while i < n:
        line = lines[i]
        s = line.strip()

        if not s:
            flush_para(para)
            i += 1
            continue

        if s.startswith(":::comparison") and re.match(r"^:::comparison(?:\s|$)", s):
            flush_para(para)
            end = i + 1
            while end < n and lines[end].strip() != ":::":
                end += 1
            if end == n:
                raise ValueError("Unclosed comparison block.")
            out.append(render_comparison(lines[i:end]))
            i = end + 1
            continue

        if s.startswith("```"):
            flush_para(para)
            i += 1
            code: list[str] = []
            while i < n and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            i += 1  # skip closing fence
            out.append("<pre><code>" +
                       html.escape("\n".join(code), quote=False) +
                       "</code></pre>")
            continue

        if re.match(r"^---+\s*$", s):
            flush_para(para)
            out.append("<hr>")
            i += 1
            continue

        m = re.match(r"^(#{1,6})\s+(.*)", s)
        if m:
            flush_para(para)
            level = len(m.group(1))
            tag = f"h{min(6, max(2, level))}" if article else (
                "h4" if level <= 2 else ("h5" if level == 3 else "h6"))
            anchor = f' id="{next(headings)["id"]}"' if article else ""
            out.append(f"<{tag}{anchor}>" + md_inline(m.group(2).strip()) +
                       f"</{tag}>")
            i += 1
            continue

        if s.startswith(">"):
            flush_para(para)
            quote: list[str] = []
            while i < n and lines[i].strip().startswith(">"):
                quote.append(lines[i].strip()[1:].strip())
                i += 1
            out.append("<blockquote>" + md_inline(" ".join(quote)) +
                       "</blockquote>")
            continue

        if re.match(r"^([-*+])\s+\S", s):
            flush_para(para)
            items: list[str] = []
            while i < n and re.match(r"^([-*+])\s+\S", lines[i].strip()):
                items.append(md_inline(
                    re.sub(r"^([-*+])\s+", "", lines[i].strip())))
                i += 1
            out.append("<ul>" + "".join(f"<li>{t}</li>" for t in items) +
                       "</ul>")
            continue

        if re.match(r"^\d+[.)]\s+\S", s):
            flush_para(para)
            items = []
            while i < n and re.match(r"^\d+[.)]\s+\S", lines[i].strip()):
                items.append(md_inline(
                    re.sub(r"^\d+[.)]\s+", "", lines[i].strip())))
                i += 1
            out.append("<ol>" + "".join(f"<li>{t}</li>" for t in items) +
                       "</ol>")
            continue

        para.append(s)
        i += 1
    flush_para(para)
    return "\n".join(out)


def split_links(meta: dict) -> tuple[str | None, list[str]]:
    """First present link key = primary (title link); rest = secondary."""
    present = [k for k in LINK_PRIORITY if k in meta]
    if not present:
        return None, []
    return present[0], present[1:]


def is_img(url: str) -> bool:
    return url.split("?")[0].lower().endswith(IMG_EXTS)


def local_asset(url: str) -> Path | None:
    """Resolve a published asset without letting content escape assets/."""
    parsed = urlsplit(url)
    if parsed.scheme or parsed.netloc or parsed.path.startswith("/"):
        return None
    rel = unquote(parsed.path).removeprefix("assets/")
    path = (ASSETS / rel).resolve()
    if path.is_file() and path.is_relative_to(ASSETS.resolve()):
        return path
    return None


def file_links(entry: dict) -> list[tuple[str, str]]:
    """Find linked files in metadata and ordinary Markdown links."""
    links: list[tuple[str, str]] = []
    for key in LINK_PRIORITY:
        url = entry["meta"].get(key)
        if url and urlsplit(url).path.lower().endswith(FILE_EXTS):
            links.append((url, LINK_KEYS[key]))
    for label, url in re.findall(r"(?<!!)\[([^\]]+)\]\(([^)\s]+)", entry["md"]):
        if urlsplit(url).path.lower().endswith(FILE_EXTS):
            links.append((url, label))
    return list(dict.fromkeys(links))


def make_preview(url: str) -> str | None:
    """Render the first page locally when a system PDF renderer is available."""
    source = local_asset(url)
    if source is None:
        return None
    if source.suffix.lower() in IMG_EXTS:
        return source.relative_to(ASSETS).as_posix()
    digest = hashlib.sha256(str(source.relative_to(ASSETS)).encode()).hexdigest()[:12]
    output_png = OUT / "previews" / f"{digest}.png"
    output_jpg = OUT / "previews" / f"{digest}.jpg"
    output_png.parent.mkdir(parents=True, exist_ok=True)
    if output_png.exists():
        return output_png.relative_to(OUT).as_posix()
    if output_jpg.exists():
        return output_jpg.relative_to(OUT).as_posix()
    pdf = source
    with tempfile.TemporaryDirectory(prefix="site-preview-") as temporary:
        if source.suffix.lower() != ".pdf":
            office = shutil.which("libreoffice") or shutil.which("soffice")
            if not office:
                quicklook = shutil.which("qlmanage")
                if quicklook:
                    try:
                        subprocess.run([quicklook, "-t", "-s", "1200", "-o", temporary,
                                        str(source)], capture_output=True, timeout=30, check=False)
                        thumbnails = list(Path(temporary).glob("*.png"))
                        if thumbnails:
                            shutil.copyfile(thumbnails[0], output_png)
                            return output_png.relative_to(OUT).as_posix()
                    except (OSError, subprocess.TimeoutExpired):
                        pass
                return None
            try:
                result = subprocess.run(
                    [office, "-env:UserInstallation=file:///tmp/site-preview-lo", "--headless",
                     "--convert-to", "pdf", "--outdir", temporary, str(source)],
                    capture_output=True, timeout=60, check=False)
            except (OSError, subprocess.TimeoutExpired):
                return None
            pdf = Path(temporary) / (source.stem + ".pdf")
            if result.returncode or not pdf.exists():
                return None
        commands = []
        if shutil.which("pdftoppm"):
            prefix = output_png.with_suffix("")
            commands.append((["pdftoppm", "-f", "1", "-singlefile", "-scale-to", "1200",
                              "-png", str(pdf), str(prefix)], output_png))
        if shutil.which("sips"):
            # sips can make transparent PDF pages black in PNG; JPEG flattens them.
            commands.append((["sips", "-s", "format", "jpeg", str(pdf), "--out",
                              str(output_jpg)], output_jpg))
        for command, target in commands:
            try:
                result = subprocess.run(command, capture_output=True, timeout=30, check=False)
                if result.returncode == 0 and target.exists():
                    return target.relative_to(OUT).as_posix()
            except (OSError, subprocess.TimeoutExpired):
                pass
    return None


def render_attachments(entry: dict, asset_prefix: str = "") -> str:
    """A compact first-page preview for each locally linked document or image."""
    meta = entry["meta"]
    explicit = next((meta[k] for k in IMAGE_KEYS if k in meta), None)
    links = file_links(entry)
    # A supplied image is usually a hand-picked cover for the first document.
    if explicit:
        target = links[0][0] if links else explicit
        links = [(target, links[0][1] if links else "Image")] + [
            item for item in links[1:] if item[0] != target]
    seen: set[str] = set()
    parts: list[str] = []
    for url, label in links:
        if url in seen:
            continue
        seen.add(url)
        preview = (explicit if explicit and len(parts) == 0 and local_asset(explicit)
                   else make_preview(url))
        target = post_asset_url(url, asset_prefix)
        if not preview:
            # Browser PDF viewers can still show page one on hosts without a renderer.
            if urlsplit(url).path.lower().endswith(".pdf"):
                preview_html = (f'<iframe src="{html.escape(target, quote=True)}#page=1&amp;view=Fit" '
                                'title="First page preview" loading="lazy"></iframe>')
            elif is_img(url):
                preview_html = (f'<img src="{html.escape(target, quote=True)}" '
                                f'alt="Preview of {html.escape(entry["title"], quote=True)}" '
                                'loading="lazy">')
            else:
                preview_html = (f'<span class="file-fallback" aria-hidden="true">'
                                f'{html.escape(Path(urlsplit(url).path).suffix.lstrip(".").upper() or "FILE")}'
                                '</span>')
        else:
            src = asset_prefix + preview.removeprefix("assets/")
            preview_html = (f'<img src="{html.escape(src, quote=True)}" '
                            f'alt="First page or slide of {html.escape(entry["title"], quote=True)}" '
                            'loading="lazy">')
        suffix = Path(urlsplit(url).path).suffix.lstrip(".").upper()
        parts.append(
            '<div class="preview">'
            f'<a href="{html.escape(target, quote=True)}" aria-label="Open {html.escape(label, quote=True)}">'
            f'{preview_html}<span class="preview-caption"><span>{html.escape(label)}</span>'
            f'<span>{suffix or "FILE"} ↗</span></span></a></div>')
    return "\n".join(parts)


def render_mini_links(keys: list[str], meta: dict) -> str:
    if not keys:
        return ""
    items = " · ".join(
        f'<a class="mini-link" href="{html.escape(meta[k], quote=True)}">'
        f"{LINK_KEYS[k]}</a>" for k in keys)
    return f'<div class="mini-links">{items}</div>'
def display_date(value: str) -> str:
    """Use compact month names so date ranges stay readable on narrow screens."""
    months = ("January", "February", "March", "April", "May", "June", "July",
              "August", "September", "October", "November", "December")
    for month in months:
        value = re.sub(rf"\b{month}\b", month[:3], value)
    return md_inline(value)


def render_entry(entry: dict) -> str:
    """Card layout (Projects): clickable title, tag pills, file previews."""
    title = html.escape(entry["title"])
    meta = entry["meta"]

    tags: list[str] = []
    for k in TAG_KEYS:
        if k in meta:
            tags = [t.strip() for t in re.split(r"[,;]", meta[k]) if t.strip()]
            break

    meta_spans: list[str] = []
    for k in META_ORDER:
        if k in meta and k not in TAG_KEYS and k not in LINK_KEYS and k != "status":
            meta_spans.append(
                f'<span><span class="k">{html.escape(k.capitalize())}:</span> '
                f"{md_inline(meta[k])}</span>")
    # Any other non-link, non-tag, non-date, non-image keys render generically.
    for k, v in meta.items():
        if (k not in META_ORDER and k not in DATE_KEYS and k not in TAG_KEYS
                and k not in LINK_KEYS and k not in IMAGE_KEYS and k != "summary"):
            meta_spans.append(
                f'<span><span class="k">{html.escape(k.capitalize())}:</span> '
                f"{md_inline(v)}</span>")

    primary, secondary = split_links(meta)
    if primary is not None:
        title_html = (f'<a href="{html.escape(meta[primary], quote=True)}">'
                      f"{title}</a>")
    else:
        title_html = title

    when = meta.get("date") or meta.get("period") or ""
    date_span = (f'<span class="card-date">{display_date(when)}</span>'
                 if when else "")
    status = meta.get("status", "")
    status_class = " status-active" if status.lower() == "in progress" else ""
    status_html = (f'<span class="project-status{status_class}">{html.escape(status)}</span>'
                   if status else "")

    parts = ['<article class="card">']
    attachments = render_attachments(entry)
    if attachments:
        parts.append(f'<div class="card-media">{attachments}</div>')
    parts.append('<div class="card-content">')
    parts.append(f'<div class="card-topline">{date_span}{status_html}</div>')
    parts.append(f'<div class="card-head"><h3>{title_html}</h3></div>')
    if meta_spans:
        parts.append('<div class="meta">' + "\n".join(meta_spans) + "</div>")
    if meta.get("summary"):
        parts.append(f'<p class="project-summary">{md_inline(meta["summary"])}</p>')
        if entry["md"]:
            parts.append('<details class="project-details"><summary>Read more</summary>'
                         f'<div class="body">{md_blocks(entry["md"])}</div></details>')
    elif entry["md"]:
        parts.append(f'<div class="body">\n{md_blocks(entry["md"])}\n</div>')
    if tags:
        parts.append('<div class="tags">' + "".join(
            f'<span class="tag">{html.escape(t)}</span>' for t in tags) +
            "</div>")
    mini = render_mini_links(secondary, meta)
    if mini:
        parts.append(mini)
    parts.append("</div></article>")
    return "\n".join(parts)


def render_news_row(entry: dict) -> str:
    """Date-led editorial row for News, Education, Honors, Events, and Talks."""
    meta = entry["meta"]
    when = meta.get("date") or meta.get("period") or ""
    title = html.escape(entry["title"])

    primary, secondary = split_links(meta)
    if primary is not None:
        title = (f'<a href="{html.escape(meta[primary], quote=True)}">'
                 f"{title}</a>")

    extras = []
    for k in ("role", "event", "location", "details", "degree"):
        if k in meta:
            extras.append(md_inline(meta[k]))
    # Any other non-link, non-tag, non-date, non-image keys, appended.
    for k, v in meta.items():
        if (k not in ("role", "event", "location", "details", "degree")
                and k not in DATE_KEYS and k not in TAG_KEYS
                and k not in LINK_KEYS and k not in IMAGE_KEYS and k != "grade"):
            extras.append(
                f'<span class="k">{html.escape(k.capitalize())}:</span> '
                f"{md_inline(v)}")
    separator = ' <span aria-hidden="true">·</span> '
    sub = f'<div class="inline-meta">{separator.join(extras)}</div>' if extras else ""
    grade = (f'<p class="education-grade"><span>Grade</span> <strong>{md_inline(meta["grade"])}</strong></p>'
             if meta.get("grade") else "")

    body = (f'<div class="news-body">\n{md_blocks(entry["md"])}\n</div>'
            if entry["md"] else "")
    attachments = render_attachments(entry)
    mini = render_mini_links(secondary, meta)

    preview_column = f'<div class="entry-previews">{attachments}</div>' if attachments else ""
    undated = not when
    date_content = title if undated else display_date(when)
    heading = "" if undated else f'<h3 class="news-title">{title}</h3>'
    row_class = "entry-row no-date" if undated else "entry-row"
    return (f'<article class="{row_class}"><div class="entry-date">{date_content}</div>'
            f'<div class="entry-main">{heading}{grade}{sub}'
            f'{body}{mini}</div>{preview_column}</article>')


def render_section(section_id: str, heading: str, entries: list[dict],
                   source_file: str, style: str = "cards") -> tuple[str, str]:
    """Return (nav_link, section_html). Style is 'cards' or 'news'."""
    nav = f'<a href="#{section_id}">{heading}</a>'
    if entries:
        if style == "news":
            rows = "\n".join(render_news_row(e) for e in entries)
            body = f'<div class="entry-list">\n{rows}\n</div>'
        else:
            body = '<div class="project-grid">\n' + "\n".join(render_entry(e) for e in entries) + '\n</div>'
    else:
        body = ('<div class="empty-note">Nothing here yet. '
                f"To add entries, edit <code>{source_file}</code>; "
                "see the format notes inside that file.</div>")
    section = (f'<section id="{section_id}" class="section">\n'
               f'<div class="section-heading"><h2>{heading}</h2></div>\n'
               f'{body}\n</section>')
    return nav, section


def find_photo() -> Path | None:
    for ext in ("jpg", "jpeg", "png", "webp"):
        p = ASSETS / f"profile.{ext}"
        if p.exists():
            return p
    return None


def photo_html(name: str, photo: Path | None) -> str:
    if photo is not None:
        # The file itself is published by the generic assets/ copy in main().
        return (f'<img src="{photo.name}" alt="Photo of {html.escape(name)}" '
                f"loading=\"eager\">")
    initials = "".join(w[0] for w in name.split() if w[:1].isalpha())[:2].upper()
    return f'<div class="profile-initials" aria-hidden="true">{html.escape(initials)}</div>'


def social_html(email: str, github: str, linkedin: str) -> str:
    items = []
    if email:
        items.append((f"mailto:{email}", "email", icon("email")))
    if github:
        items.append((github, "GitHub", icon("github")))
    if linkedin:
        items.append((linkedin, "LinkedIn", icon("linkedin")))
    return "\n".join(
        f'<a href="{html.escape(href, quote=True)}" aria-label="{title}">{svg}<span>{title}</span></a>'
        for href, title, svg in items)


def read(name: str) -> str:
    p = CONTENT / name
    return p.read_text(encoding="utf-8") if p.exists() else ""


def load_posts() -> list[dict]:
    """One Markdown file per post; the filename is its permanent URL slug."""
    posts = []
    for path in (CONTENT / "posts").glob("*.md"):
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", path.stem):
            raise ValueError(f"Invalid post filename: {path.name} (use lowercase words and hyphens)")
        meta, body = parse_frontmatter(strip_comments(path.read_text(encoding="utf-8")))
        if meta.get("draft", "false").lower() in ("true", "yes", "1"):
            continue
        for key in ("title", "date", "summary"):
            if not meta.get(key):
                raise ValueError(f"{path}: missing '{key}' in frontmatter")
        try:
            published = date.fromisoformat(meta["date"])
        except ValueError as exc:
            raise ValueError(f"{path}: date must be YYYY-MM-DD") from exc
        cover = meta.get("cover", "")
        if cover and not urlsplit(cover).scheme and local_asset(cover) is None:
            raise ValueError(f"{path}: cover '{cover}' was not found in assets/")
        posts.append({
            "slug": path.stem,
            "title": meta["title"],
            "date": published,
            "summary": meta["summary"],
            "category": meta.get("category", "Notes"),
            "cover": cover,
            "body": body.strip(),
        })
    return sorted(posts, key=lambda post: (post["date"], post["slug"]), reverse=True)


def post_date(post: dict) -> str:
    day = post["date"]
    return f'{day.strftime("%B")} {day.day}, {day.year}'


def post_asset_url(url: str, root: str) -> str:
    source = local_asset(url)
    if source:
        return root + source.relative_to(ASSETS).as_posix()
    return url


def post_body_html(body: str) -> str:
    """Make asset filenames in an article work two directories below dist/."""
    def rewrite(match):
        return (match.group(1) + post_asset_url(match.group(2), "../../")
                + (match.group(3) or "") + match.group(4))
    body = re.sub(r'(!?\[[^\]\n]*\]\()([^\s)]+)(\s+"[^"]*")?(\))', rewrite, body)
    return md_blocks(body, article=True)


def post_card(post: dict, href: str, root: str) -> str:
    title = html.escape(post["title"])
    summary = html.escape(post["summary"])
    category = html.escape(post["category"])
    cover = post["cover"]
    if cover:
        src = html.escape(post_asset_url(cover, root), quote=True)
        media = f'<img src="{src}" alt="" loading="lazy">'
    else:
        media = '<span class="journal-art" aria-hidden="true"></span>'
    return (
        '<article class="journal-card">'
        f'<a href="{html.escape(href, quote=True)}" class="journal-card-link">'
        f'<div class="journal-card-media">{media}</div>'
        '<div class="journal-card-copy">'
        f'<div class="journal-meta"><span>{category}</span><time datetime="{post["date"].isoformat()}">{post_date(post)}</time></div>'
        f'<h3>{title}</h3><p>{summary}</p>'
        '<span class="journal-arrow" aria-hidden="true">↗</span>'
        '</div></a></article>'
    )


def home_journal(posts: list[dict]) -> str:
    cards = ("\n".join(post_card(post, f'blog/{post["slug"]}/index.html', "") for post in posts[:2])
             if posts else '<p class="journal-empty">The first note is on its way.</p>')
    return (
        '<section id="journal" class="section journal-home">'
        '<div class="journal-home-heading"><div><p class="eyebrow">From the notebook</p>'
        '<h2>Articles</h2></div>'
        '<a class="journal-all" href="blog/index.html">All posts <span aria-hidden="true">↗</span></a></div>'
        '<p class="journal-home-intro">Short notes on experiments, prototypes, and what I learn along the way.</p>'
        f'<div class="journal-home-grid">{cards}</div></section>'
    )


def blog_page(template: str, *, title: str, description: str, content: str,
              root: str, blog_home: str, name: str, first: str,
              page_type: str = "website") -> str:
    replacements = {
        "PAGE_TITLE": title,
        "META_DESCRIPTION": description,
        "OG_TYPE": page_type,
        "ROOT": root,
        "BLOG_HOME": blog_home,
        "SITE_NAME": name,
        "FAVICON_LETTER": first[:1] or "A",
        "BUILD_DATE": date.today().strftime("%B %d, %Y"),
    }
    page = template
    for key, value in replacements.items():
        page = page.replace("{{" + key + "}}", html.escape(value, quote=True))
    return page.replace("{{CONTENT}}", content)


def build_blog(posts: list[dict], name: str, first: str) -> None:
    blog_dir = OUT / "blog"
    if blog_dir.exists():
        shutil.rmtree(blog_dir)
    blog_dir.mkdir()
    template = (TEMPLATES / "blog.html").read_text(encoding="utf-8")

    if posts:
        cards = "\n".join(post_card(post, f'{post["slug"]}/index.html', "../") for post in posts)
    else:
        cards = '<p class="journal-empty">No posts yet. New notes will appear here.</p>'
    listing = (
        '<header class="blog-hero"><p class="eyebrow">Journal / small projects</p>'
        '<h1>Notes from the workbench.</h1>'
        '<p>Small projects, rough ideas, and the details worth remembering.</p></header>'
        f'<section class="blog-list" aria-label="All posts"><div class="journal-grid">{cards}</div></section>'
    )
    (blog_dir / "index.html").write_text(blog_page(
        template, title=f"Journal | {name}", description="Short project notes and experiments.",
        content=listing, root="../", blog_home="./", name=name, first=first), encoding="utf-8")

    for index, post in enumerate(posts):
        category = html.escape(post["category"])
        title = html.escape(post["title"])
        read_minutes = max(1, (len(re.findall(r"\b[\w'-]+\b", post["body"])) + 199) // 200)
        cover = post["cover"]
        cover_html = (f'<figure class="article-cover"><img src="{html.escape(post_asset_url(cover, "../../"), quote=True)}" '
                      f'alt="" loading="eager"></figure>') if cover else ""
        outline = [heading for heading in article_outline(post["body"]) if heading["level"] <= 3]
        toc_items = "".join(
            f'<li class="level-{heading["level"]}"><a href="#{heading["id"]}">{html.escape(heading["label"])}</a></li>'
            for heading in outline)
        toc = (f'<aside class="article-sidebar"><nav aria-label="On this page">'
               f'<p>On this page</p><ol>{toc_items}</ol></nav></aside>') if toc_items else ""
        reading_class = "article-reading-layout" if toc_items else "article-reading-layout no-outline"
        related = ""
        if len(posts) > 1:
            next_post = posts[(index + 1) % len(posts)]
            related = ('<aside class="article-next"><div class="article-next-heading">'
                       '<h2>Continue reading</h2><a href="../index.html">View all ↗</a></div>'
                       f'<a class="article-next-link" href="../{next_post["slug"]}/index.html">'
                       f'<span class="article-next-meta">{html.escape(next_post["category"])} '
                       f'<span aria-hidden="true">·</span> {post_date(next_post)}</span>'
                       f'<strong>{html.escape(next_post["title"])}</strong>'
                       '<span class="article-next-arrow" aria-hidden="true">↗</span></a></aside>')
        attachments = render_attachments({"title": post["title"], "meta": {}, "md": post["body"]},
                                         asset_prefix="../../")
        files_html = (f'<aside class="article-attachments"><h2>Files</h2><div>{attachments}</div></aside>'
                      if attachments else "")
        article = (
            '<article class="article-page">'
            '<header class="article-header">'
            '<a class="article-back" href="../index.html">← Journal</a>'
            f'<div class="article-topline"><time datetime="{post["date"].isoformat()}">{post_date(post)}</time>'
            f'<span>{category}</span></div>'
            f'<h1>{title}</h1>'
            f'<div class="article-tools"><span class="article-read-time">{read_minutes} min read</span>'
            '<button class="article-share" type="button" data-share aria-label="Copy a link to this article">'
            '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" '
            'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
            '<path d="M10 13a5 5 0 0 0 7.07 0l2-2A5 5 0 0 0 12 3.93l-1.14 1.14"/>'
            '<path d="M14 11a5 5 0 0 0-7.07 0l-2 2A5 5 0 0 0 12 20.07l1.14-1.14"/>'
            '</svg>Share</button></div>'
            '</header>'
            f'{cover_html}<div class="{reading_class}">{toc}'
            f'<div class="article-body">{post_body_html(post["body"])}</div></div>'
            f'{files_html}'
            f'<div class="article-author"><span>Author</span><strong>{html.escape(name)}</strong></div>'
            '<div class="article-bottom"><a href="../index.html">← Back to all posts</a></div>'
            f'{related}</article>'
        )
        dest = blog_dir / post["slug"]
        dest.mkdir()
        (dest / "index.html").write_text(blog_page(
            template, title=f'{post["title"]} | {name}', description=post["summary"],
            content=article, root="../../", blog_home="../", name=name, first=first,
            page_type="article"), encoding="utf-8")


def main() -> int:
    OUT.mkdir(exist_ok=True)
    preview_dir = OUT / "previews"
    if preview_dir.exists():
        shutil.rmtree(preview_dir)
    about_meta, about_body = parse_frontmatter(strip_comments(read("about.md")))
    about_html = md_blocks(about_body.strip()) or "<p>Write your bio in <code>content/about.md</code>.</p>"

    name = about_meta.get("name", "Your Name")
    tagline = about_meta.get("tagline", "")
    email = about_meta.get("email", "")
    github = about_meta.get("github", "")
    linkedin = about_meta.get("linkedin", "")
    posts = load_posts()

    parts = name.split(None, 1)
    first, rest = (parts[0], parts[1]) if len(parts) == 2 else (name, "")

    sections = [
        ("education", "Education", parse_entries(read("education.md")),
         "content/education.md", "news"),
        ("talks", "Talks", parse_entries(read("talks.md")),
         "content/talks.md", "news"),
        ("projects", "Projects", parse_entries(read("projects.md")),
         "content/projects.md", "cards"),
        ("events", "Events", parse_entries(read("events.md")),
         "content/events.md", "news"),
        ("general", "General Information", parse_entries(read("general.md")),
         "content/general.md", "news"),
        ("honors", "Honors and Awards", parse_entries(read("honors.md")),
         "content/honors.md", "news"),
    ]

    nav_links: list[str] = ['<a href="#about">About</a>', '<a href="#journal">Articles</a>']
    rendered: dict[str, str] = {}
    for sid, heading, entries, src, style in sections:
        nav, html_section = render_section(sid, heading, entries, src, style)
        nav_links.append(nav)
        rendered[sid.upper() + "_SECTION"] = html_section
    rendered["JOURNAL_SECTION"] = home_journal(posts)

    template = (TEMPLATES / "layout.html").read_text(encoding="utf-8")
    page = template
    page = page.replace("{{PAGE_TITLE}}", html.escape(f"{name} | {tagline}" if tagline else name))
    page = page.replace("{{META_DESCRIPTION}}",
                        html.escape(f"{name}, {tagline}".strip(", ")))
    page = page.replace("{{FAVICON_LETTER}}", html.escape(first[:1] or "A"))
    page = page.replace("{{SITE_NAME}}", html.escape(name))
    page = page.replace("{{FIRST_NAME}}", html.escape(first))
    page = page.replace("{{REST_NAME}}", html.escape(rest))
    page = page.replace("{{TAGLINE}}", html.escape(tagline))
    page = page.replace("{{LOCATION}}", html.escape(about_meta.get("location", "")))
    page = page.replace("{{NAV_LINKS}}", "\n".join("        " + l for l in nav_links))
    page = page.replace("{{PHOTO_HTML}}", photo_html(name, find_photo()))
    page = page.replace("{{BIO_HTML}}", about_html)
    page = page.replace("{{SOCIAL_HTML}}", social_html(email, github, linkedin))
    for key, val in rendered.items():
        page = page.replace("{{" + key + "}}", val)
    page = page.replace("{{BUILD_DATE}}", date.today().strftime("%B %d, %Y"))

    (OUT / "index.html").write_text(page, encoding="utf-8")
    build_blog(posts, name, first)
    # Publish everything in assets/ (style, script, photo, plus any images
    # or files referenced from entries, e.g. ![caption](fig.png),
    # [slides](slides.pdf), or `- slides: slides.pdf`).
    for item in ASSETS.rglob("*"):
        if item.is_file():
            dest = OUT / item.relative_to(ASSETS)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(item, dest)

    counts = ", ".join(f"{sid}: {len(entries)}" for sid, _, entries, _, _ in sections)
    print(f"Built dist/index.html and {len(posts)} journal post(s) ({counts})")
    return 0


if __name__ == "__main__":
    if "--serve" in sys.argv:
        import http.server
        import functools
        sys.exit(main() or
                 http.server.test(
                     HandlerClass=functools.partial(
                         http.server.SimpleHTTPRequestHandler, directory=str(OUT)),
                     port=8000))
    sys.exit(main())

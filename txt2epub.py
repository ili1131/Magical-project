#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
txt2epub.py — Convert TXT novel/book to EPUB, UTF-8 in/out.

Repo layout suggestion:
  txt2epub.py
  README.md
  LICENSE
  examples/
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import os
import re
import sys
import zipfile
from pathlib import Path

EPUB_VERSION = "2.0"
MIME_EPUB = "application/epub+zip"
MIME_CONTAINER = "application/oebps-package+xml"
MIME_NCX = "application/x-dtbncx+xml"
MIME_XHTML = "application/xhtml+xml"
MIME_CSS = "text/css"

# Put UTF-8 first; include common CJK encodings for auto-detection.
AUTO_ENCODINGS = [
    "utf-8-sig",
    "utf-8",
    "gb18030",
    "gbk",
    "gb2312",
    "big5",
    "big5hkscs",
    "cp950",
    "cp936",
    "shift_jis",
    "euc_jp",
    "euc_kr",
    "latin-1",
]

DEFAULT_CHAPTER_RE = r"^\s*(第[0-9零一二三四五六七八九十百千万两]+[章节回卷部集]\s*[^\n\r]*|Chapter\s+\d+[^\n\r]*)\s*$"

CSS = """
body { font-family: serif; line-height: 1.65; margin: 1em; }
h1 { font-size: 1.35em; margin: 0.8em 0 0.4em; }
p { text-indent: 2em; margin: 0.55em 0; }
""".strip()


def read_text(path: Path, encoding: str) -> tuple[str, str]:
    raw = path.read_bytes()
    tried: list[str] = []

    if encoding != "auto":
        tried = [encoding]
    else:
        tried = AUTO_ENCODINGS

    last_err: Exception | None = None
    for enc in tried:
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError as e:
            last_err = e
        except LookupError:
            raise SystemExit(f"Unknown encoding: {enc}")

    raise SystemExit(
        f"Cannot decode {path}. Tried: {', '.join(tried)}. Last error: {last_err}"
    )


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Remove BOM/control chars except tab/newline.
    text = "".join(ch for ch in text if ch == "\n" or ch == "\t" or ord(ch) >= 32)
    # Collapse trailing spaces on each line and excess blank lines.
    lines = [re.sub(r"[ \t]+$", "", line) for line in text.split("\n")]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_into_paragraphs(block: str) -> list[str]:
    paras = [p.strip() for p in re.split(r"\n\s*\n", block.strip()) if p.strip()]
    if not paras and block.strip():
        paras = [p.strip() for p in block.split("\n") if p.strip()]
    return paras


def split_chapters(
    text: str,
    chapter_regex: str,
    split_every: int,
) -> list[tuple[str, str]]:
    """
    Return list of (chapter_title, chapter_body).
    If no chapter markers are found and split_every <= 0: one chapter.
    """
    if split_every > 0:
        paras = split_into_paragraphs(text)
        chapters: list[tuple[str, str]] = []
        for i in range(0, len(paras), split_every):
            chunk = "\n\n".join(paras[i : i + split_every])
            chapters.append((f"第 {i // split_every + 1} 部分", chunk))
        return chapters or [("正文", text)]

    pattern = re.compile(chapter_regex, re.IGNORECASE | re.MULTILINE)
    matches = list(pattern.finditer(text))
    if not matches:
        return [("正文", text)]

    chapters: list[tuple[str, str]] = []
    for idx, m in enumerate(matches):
        start = m.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        title = m.group(0).strip()
        body = text[start:end].strip("\n")
        chapters.append((title, body))

    # Anything before the first marker becomes a front-matter chapter.
    prefix = text[: matches[0].start()].strip()
    if prefix:
        chapters.insert(0, ("前言", prefix))
    return chapters


def xhtml_escape(s: str) -> str:
    return html.escape(s, quote=True)


def chapter_filename(index: int) -> str:
    return f"chapter-{index:03d}.xhtml"


def build_xhtml(title: str, body: str, lang: str) -> str:
    paras = split_into_paragraphs(body)
    if not paras:
        paras = [""]
    p_html = "\n".join(f"    <p>{xhtml_escape(p).replace(chr(10), '<br/>')}</p>" for p in paras)
    return f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="{xhtml_escape(lang)}" lang="{xhtml_escape(lang)}">
<head>
  <meta charset="utf-8"/>
  <title>{xhtml_escape(title)}</title>
  <link rel="stylesheet" type="text/css" href="style.css"/>
</head>
<body>
  <h1>{xhtml_escape(title)}</h1>
{p_html}
</body>
</html>
"""


def build_container() -> str:
    return """<?xml version="1.0" encoding="utf-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""


def build_opf(
    uid: str,
    title: str,
    author: str,
    lang: str,
    chapter_files: list[str],
    chapter_titles: list[str],
) -> str:
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    manifest_items = [
        '    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>',
        '    <item id="css" href="style.css" media-type="text/css"/>',
    ]
    spine_items: list[str] = []
    for i, (fname, ctitle) in enumerate(zip(chapter_files, chapter_titles), start=1):
        manifest_items.append(
            f'    <item id="chap{i}" href="{fname}" media-type="application/xhtml+xml"/>'
        )
        spine_items.append(f'    <itemref idref="chap{i}"/>')

    manifest = "\n".join(manifest_items)
    spine = "\n".join(spine_items)
    return f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="uid" version="{EPUB_VERSION}">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="uid">{xhtml_escape(uid)}</dc:identifier>
    <dc:title>{xhtml_escape(title)}</dc:title>
    <dc:creator>{xhtml_escape(author)}</dc:creator>
    <dc:language>{xhtml_escape(lang)}</dc:language>
    <dc:date>{now}</dc:date>
    <meta name="generator" content="txt2epub.py"/>
  </metadata>
  <manifest>
{manifest}
  </manifest>
  <spine toc="ncx">
{spine}
  </spine>
</package>
"""


def build_ncx(uid: str, title: str, author: str, chapter_files: list[str], chapter_titles: list[str]) -> str:
    navs: list[str] = []
    for i, (fname, ctitle) in enumerate(zip(chapter_files, chapter_titles), start=1):
        navs.append(
            f"""  <navPoint id="nav{i}" playOrder="{i}">
    <navLabel><text>{xhtml_escape(ctitle)}</text></navLabel>
    <content src="{fname}"/>
  </navPoint>"""
        )
    nav_map = "\n".join(navs)
    return f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN" "http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="{xhtml_escape(uid)}"/>
    <meta name="dtb:depth" content="1"/>
    <meta name="dtb:totalPageCount" content="0"/>
    <meta name="dtb:maxPageNumber" content="0"/>
  </head>
  <docTitle><text>{xhtml_escape(title)}</text></docTitle>
  <docAuthor><text>{xhtml_escape(author)}</text></docAuthor>
  <navMap>
{nav_map}
  </navMap>
</ncx>
"""


def safe_stem(path: Path) -> str:
    stem = re.sub(r"[^\w\-.\u4e00-\u9fff]+", "_", path.stem, flags=re.UNICODE)
    return stem.strip("_") or "book"


def convert(
    input_txt: Path,
    output_epub: Path,
    title: str | None,
    author: str,
    lang: str,
    encoding: str,
    chapter_regex: str,
    split_every: int,
) -> None:
    text, used_encoding = read_text(input_txt, encoding)
    text = normalize_text(text)
    if not text:
        raise SystemExit(f"Input file is empty after decoding: {input_txt}")

    book_title = title or input_txt.stem
    chapters = split_chapters(text, chapter_regex, split_every)
    if not chapters:
        chapters = [("正文", text)]

    uid = f"urn:uuid:txt2epub-{safe_stem(input_txt)}-{abs(hash((str(input_txt), text[:4096], dt.datetime.now().isoformat()))) & 0xffffffffffffffff:x}"
    chapter_files = [chapter_filename(i) for i in range(1, len(chapters) + 1)]
    chapter_titles = [c[0] for c in chapters]

    output_epub.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_epub, "w") as zf:
        # EPUB requires mimetype as first entry and stored (not compressed).
        info = zipfile.ZipInfo("mimetype", date_time=(1980, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_STORED
        info.external_attr = 0o644 << 16
        zf.writestr(info, MIME_EPUB)

        files: dict[str, str] = {
            "META-INF/container.xml": build_container(),
            "OEBPS/content.opf": build_opf(uid, book_title, author, lang, chapter_files, chapter_titles),
            "OEBPS/toc.ncx": build_ncx(uid, book_title, author, chapter_files, chapter_titles),
            "OEBPS/style.css": CSS,
        }
        for (ctitle, body), fname in zip(chapters, chapter_files):
            files[f"OEBPS/{fname}"] = build_xhtml(ctitle, body, lang)

        for arcname, data in files.items():
            zi = zipfile.ZipInfo(arcname, date_time=(1980, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            zf.writestr(zi, data.encode("utf-8"))

    print(f"OK: {output_epub}")
    print(f"Input encoding detected/used: {used_encoding}")
    print(f"Chapters: {len(chapters)}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Convert TXT to EPUB with UTF-8 output.")
    p.add_argument("input", type=Path, help="input .txt file")
    p.add_argument("-o", "--output", type=Path, help="output .epub file")
    p.add_argument("--title", help="book title; default: input filename")
    p.add_argument("--author", default="Unknown", help="author name")
    p.add_argument("--lang", default="zh-TW", help="language code")
    p.add_argument(
        "--encoding",
        default="auto",
        help="input encoding, or 'auto'. Examples: utf-8, utf-8-sig, gb18030, big5",
    )
    p.add_argument(
        "--chapter-regex",
        default=DEFAULT_CHAPTER_RE,
        help="regex whose matched line starts a new chapter",
    )
    p.add_argument(
        "--split-every",
        type=int,
        default=0,
        metavar="N",
        help="if no chapter titles, split every N paragraphs",
    )
    args = p.parse_args(argv)

    output = args.output or args.input.with_suffix(".epub")
    convert(
        input_txt=args.input,
        output_epub=output,
        title=args.title,
        author=args.author,
        lang=args.lang,
        encoding=args.encoding,
        chapter_regex=args.chapter_regex,
        split_every=args.split_every,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
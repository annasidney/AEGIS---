"""
AEGIS Web Archiver Action Module
Downloads and converts web pages into clean, structured Markdown archives
using BeautifulSoup4 for offline reference, intelligence logs, and knowledge synthesis.
"""

import os
import sys
import re
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

# Ensure root package is in sys.path when executed directly as a script
_CURRENT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _CURRENT_DIR.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import requests
from bs4 import BeautifulSoup, NavigableString, Tag, Comment

from aegis.config import WORKSPACE_DIR, BASE_DIR


class WebArchiver:
    """Downloads web pages and converts them to clean Markdown archives."""

    def __init__(self, archives_dir: Optional[Path] = None):
        """Initializes WebArchiver with a target archive storage directory."""
        if archives_dir is None:
            self.archives_dir = WORKSPACE_DIR / "archives"
        else:
            self.archives_dir = Path(archives_dir)

        self.archives_dir.mkdir(parents=True, exist_ok=True)
        self.default_headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36 AEGIS-Archiver/1.0"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

    def _extract_domain(self, url: str) -> str:
        """Extracts and sanitizes domain name for filename generation."""
        try:
            parsed = urllib.parse.urlparse(url)
            domain = parsed.netloc or parsed.path.split("/")[0]
            if domain.startswith("www."):
                domain = domain[4:]
            # Remove port if present
            if ":" in domain:
                domain = domain.split(":")[0]
            # Replace invalid filename characters (especially on Windows)
            clean_domain = re.sub(r"[<>:\"/\\|?*^]+", "_", domain).strip("._")
            return clean_domain or "web_archive"
        except Exception:
            return "web_archive"

    def _convert_node(self, node: Any, base_url: str, depth: int = 0) -> str:
        """Recursively converts a BeautifulSoup node (Tag or NavigableString) into Markdown."""
        # Ignore comments
        if isinstance(node, Comment):
            return ""

        if isinstance(node, NavigableString):
            text = str(node)
            if node.parent and node.parent.name.lower() in ["pre", "code"]:
                return text
            # Normalize internal whitespace
            return re.sub(r"[ \t\r\n]+", " ", text)

        if not isinstance(node, Tag):
            return ""

        tag = node.name.lower()

        # Headings
        if tag in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            level = int(tag[1])
            inner = "".join(self._convert_node(c, base_url, depth) for c in node.children).strip()
            return f"\n\n{'#' * level} {inner}\n\n" if inner else ""

        # Paragraphs
        if tag == "p":
            inner = "".join(self._convert_node(c, base_url, depth) for c in node.children).strip()
            return f"\n\n{inner}\n\n" if inner else ""

        # Line breaks & Horizontal Dividers
        if tag == "br":
            return "\n"
        if tag == "hr":
            return "\n\n---\n\n"

        # Text Formatting
        if tag in ["strong", "b"]:
            inner = "".join(self._convert_node(c, base_url, depth) for c in node.children).strip()
            return f"**{inner}**" if inner else ""

        if tag in ["em", "i"]:
            inner = "".join(self._convert_node(c, base_url, depth) for c in node.children).strip()
            return f"*{inner}*" if inner else ""

        if tag in ["s", "del", "strike"]:
            inner = "".join(self._convert_node(c, base_url, depth) for c in node.children).strip()
            return f"~~{inner}~~" if inner else ""

        # Inline & Block Code
        if tag == "code":
            if node.parent and node.parent.name.lower() == "pre":
                return node.get_text()
            inner = node.get_text().strip()
            return f"`{inner}`" if inner else ""

        if tag == "pre":
            code_tag = node.find("code")
            lang = ""
            if code_tag and code_tag.get("class"):
                for cls in code_tag["class"]:
                    if cls.startswith("language-"):
                        lang = cls.replace("language-", "")
                        break
                    elif cls.startswith("lang-"):
                        lang = cls.replace("lang-", "")
                        break
            code_text = node.get_text().strip()
            return f"\n\n```{lang}\n{code_text}\n```\n\n" if code_text else ""

        # Blockquotes
        if tag == "blockquote":
            inner = "".join(self._convert_node(c, base_url, depth) for c in node.children).strip()
            lines = [f"> {line}" for line in inner.splitlines() if line.strip()]
            return "\n\n" + "\n".join(lines) + "\n\n" if lines else ""

        # Hyperlinks
        if tag == "a":
            href = node.get("href", "").strip()
            inner = "".join(self._convert_node(c, base_url, depth) for c in node.children).strip()
            if href and not href.startswith(("javascript:", "#")):
                full_url = urllib.parse.urljoin(base_url, href)
                return f"[{inner or full_url}]({full_url})"
            return inner

        # Images
        if tag == "img":
            src = node.get("src", "").strip()
            alt = node.get("alt", "").strip() or "Image"
            if src:
                full_src = urllib.parse.urljoin(base_url, src)
                return f"\n\n![{alt}]({full_src})\n\n"
            return ""

        # Lists (Unordered & Ordered)
        if tag in ["ul", "ol"]:
            items = []
            is_ordered = (tag == "ol")
            idx = 1
            indent = "  " * depth

            for child in node.children:
                if isinstance(child, Tag) and child.name.lower() == "li":
                    li_content = ""
                    sub_lists = []
                    for li_child in child.children:
                        if isinstance(li_child, Tag) and li_child.name.lower() in ["ul", "ol"]:
                            sub_lists.append(self._convert_node(li_child, base_url, depth + 1))
                        else:
                            li_content += self._convert_node(li_child, base_url, depth)
                    li_text = li_content.strip()
                    prefix = f"{indent}{idx}. " if is_ordered else f"{indent}- "
                    item_str = f"{prefix}{li_text}"
                    if sub_lists:
                        item_str += "\n" + "\n".join(sub_lists)
                    items.append(item_str)
                    idx += 1

            return "\n\n" + "\n".join(items) + "\n\n" if items else ""

        # Tables
        if tag == "table":
            rows = []
            for tr in node.find_all("tr"):
                cells = [
                    re.sub(r"[ \t\r\n]+", " ", td.get_text().strip())
                    for td in tr.find_all(["th", "td"])
                ]
                if cells:
                    rows.append(cells)
            if rows:
                max_cols = max(len(r) for r in rows)
                normalized_rows = [r + [""] * (max_cols - len(r)) for r in rows]
                header = normalized_rows[0]
                divider = ["---"] * max_cols
                table_lines = [
                    "| " + " | ".join(header) + " |",
                    "| " + " | ".join(divider) + " |"
                ]
                for row in normalized_rows[1:]:
                    table_lines.append("| " + " | ".join(row) + " |")
                return "\n\n" + "\n".join(table_lines) + "\n\n"
            return ""

        # Default recursive traversal for containers (div, section, article, main, span, body, etc.)
        return "".join(self._convert_node(c, base_url, depth) for c in node.children)

    def _html_to_markdown(self, html_content: str, base_url: str) -> Tuple[str, str]:
        """
        Strips unnecessary HTML tags and converts body content to clean Markdown.
        Returns a tuple of (title, markdown_content).
        """
        soup = BeautifulSoup(html_content, "html.parser")

        # 1. Extract Title
        title = ""
        title_tag = soup.find("title")
        if title_tag and title_tag.get_text():
            title = re.sub(r"[ \t\r\n]+", " ", title_tag.get_text()).strip()

        if not title:
            h1_tag = soup.find("h1")
            if h1_tag and h1_tag.get_text():
                title = re.sub(r"[ \t\r\n]+", " ", h1_tag.get_text()).strip()

        if not title:
            title = self._extract_domain(base_url)

        # 2. Strip scripts, styles, navigation, and extraneous structural elements
        strip_tags = [
            "script", "style", "nav", "header", "footer", "aside",
            "noscript", "iframe", "svg", "button", "input", "select",
            "textarea", "form", "meta", "link", "canvas", "dialog", "template"
        ]
        for tag_name in strip_tags:
            for element in soup.find_all(tag_name):
                element.decompose()

        # 3. Convert target root element
        target_root = soup.body or soup
        raw_markdown = self._convert_node(target_root, base_url=base_url, depth=0)

        # 4. Clean whitespace and consecutive newlines
        clean_lines = [line.rstrip() for line in raw_markdown.splitlines()]
        clean_markdown = "\n".join(clean_lines)
        clean_markdown = re.sub(r"\n{3,}", "\n\n", clean_markdown).strip()

        return title, clean_markdown

    def archive(self, url: str) -> Dict[str, Any]:
        """
        Downloads HTML from the specified URL, converts it to clean Markdown,
        and saves it to data/workspace/archives/<domain>_<timestamp>.md.

        Returns:
            Dict containing:
                - success (bool): True if archived and saved successfully.
                - title (str): Extracted page title.
                - content_preview (str): First 300 characters preview of markdown content.
                - saved_path (str): Relative path to the saved markdown file.
                - word_count (int): Word count of the archived document.
        """
        clean_url = url.strip()
        if not clean_url.startswith(("http://", "https://")):
            clean_url = "https://" + clean_url

        try:
            # 1. Fetch HTML
            response = requests.get(clean_url, headers=self.default_headers, timeout=15)
            response.raise_for_status()
            html_content = response.text

            # 2. Convert HTML to Markdown
            title, body_markdown = self._html_to_markdown(html_content, base_url=clean_url)

            # 3. Format complete archive document
            timestamp_human = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            timestamp_file = datetime.now().strftime("%Y%m%d_%H%M%S")
            domain_name = self._extract_domain(clean_url)

            full_markdown = (
                f"# {title}\n\n"
                f"- **Source URL:** {clean_url}\n"
                f"- **Archived At:** {timestamp_human}\n\n"
                f"---\n\n"
                f"{body_markdown}\n"
            )

            # 4. Save to archive file
            filename = f"{domain_name}_{timestamp_file}.md"
            file_path = self.archives_dir / filename

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(full_markdown)

            # Calculate relative path
            try:
                rel_path = file_path.relative_to(BASE_DIR).as_posix()
            except ValueError:
                rel_path = f"data/workspace/archives/{filename}"

            word_count = len(full_markdown.split())
            preview = body_markdown[:300].strip()
            if len(body_markdown) > 300:
                preview += "..."

            return {
                "success": True,
                "title": title,
                "content_preview": preview,
                "saved_path": rel_path,
                "word_count": word_count,
            }

        except Exception as e:
            print(f"[WebArchiver Error] Failed to archive '{url}': {e}")
            return {
                "success": False,
                "title": "",
                "content_preview": "",
                "saved_path": "",
                "word_count": 0,
                "error": str(e)
            }


if __name__ == "__main__":
    print("=" * 60)
    print("Testing AEGIS WebArchiver on https://example.com")
    print("=" * 60)

    archiver = WebArchiver()
    result = archiver.archive("https://example.com")

    print("\nArchival Result:")
    for k, v in result.items():
        print(f"  {k}: {v}")

    if result.get("success"):
        saved_file = BASE_DIR / result["saved_path"]
        if saved_file.exists():
            print(f"\n--- File Contents ({saved_file}) ---")
            with open(saved_file, "r", encoding="utf-8") as f:
                print(f.read())

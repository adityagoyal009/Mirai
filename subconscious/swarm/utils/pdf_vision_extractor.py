"""
PDF Extractor — routes through OpenClaw gateway for native PDF + vision analysis.

Two-pass approach for maximum extraction:
1. Sub-agent reads the PDF natively (sees text, layout, embedded vectors)
2. Sub-agent also reads rendered page images (catches scanned text, raster charts,
   infographics stored as images, complex visual layouts)

The agent cross-references both to ensure nothing is missed.
No PyMuPDF required for the primary path, but uses it for image rendering when available.
Falls back to PDF-only if image rendering isn't possible.
"""

import json
import logging
import os
import re
import time
from typing import Dict, Any, Optional, List

import requests

logger = logging.getLogger(__name__)

# Minimum text characters on a page before we consider it text-heavy
TEXT_THRESHOLD = 50

# Hard limit on file size (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024

# Max pages
MAX_PAGES = 4

# OpenClaw gateway
_OPENCLAW_URL = "http://127.0.0.1:18789"
_OPENCLAW_TOKEN = None


def _get_token() -> str:
    """Lazy-load OpenClaw gateway auth token."""
    global _OPENCLAW_TOKEN
    if _OPENCLAW_TOKEN:
        return _OPENCLAW_TOKEN
    try:
        config_path = os.path.expanduser("~/.openclaw/openclaw.json")
        with open(config_path) as f:
            cfg = json.load(f)
        _OPENCLAW_TOKEN = cfg["gateway"]["auth"]["token"]
    except Exception as e:
        logger.warning(f"[PDFExtractor] Could not load OpenClaw auth token: {e}. Authenticated requests will fail with 401.")
        _OPENCLAW_TOKEN = ""
    return _OPENCLAW_TOKEN


def _invoke_tool(tool: str, args: dict, timeout: int = 120) -> Optional[dict]:
    """Call an OpenClaw gateway tool via HTTP."""
    token = _get_token()
    try:
        resp = requests.post(
            f"{_OPENCLAW_URL}/tools/invoke",
            json={"tool": tool, "args": args},
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )
        if resp.status_code != 200:
            logger.warning(f"[PDFExtractor] tools/invoke {tool} HTTP {resp.status_code}")
            return None
        return resp.json()
    except Exception as e:
        logger.warning(f"[PDFExtractor] tools/invoke {tool} failed: {e}")
        return None


def _render_pages_as_images(file_path: str, output_dir: str) -> List[str]:
    """Render each PDF page as a high-res PNG image for vision analysis.

    Returns list of image file paths. Empty list if rendering not available.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.info("[PDFExtractor] PyMuPDF not installed — skipping image rendering, using PDF-only mode")
        return []

    image_paths = []
    try:
        doc = fitz.open(file_path)
        for page_num in range(min(len(doc), MAX_PAGES)):
            page = doc[page_num]
            # 2x zoom for high-res rendering — catches fine text in images
            zoom = 2.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            img_path = os.path.join(output_dir, f"page_{page_num + 1}.png")
            pix.save(img_path)
            image_paths.append(img_path)
        doc.close()
        logger.info(f"[PDFExtractor] Rendered {len(image_paths)} pages as images")
    except Exception as e:
        logger.warning(f"[PDFExtractor] Image rendering failed: {e}")

    return image_paths


def _count_pdf_pages(file_path: str) -> int:
    """Count PDF pages."""
    try:
        import fitz
        doc = fitz.open(file_path)
        count = len(doc)
        doc.close()
        return count
    except ImportError:
        pass

    # Fallback: parse PDF binary
    try:
        with open(file_path, "rb") as f:
            content = f.read()
        pages = re.findall(rb'/Type\s*/Page[^s]', content)
        return max(len(pages), 1)
    except Exception:
        return 1


def extract_pdf_with_vision(
    file_path: str,
    llm_client=None,  # ignored, kept for backward compat
    standardize: bool = True,
) -> Dict[str, Any]:
    """
    Extract content from a PDF. Uses a fast path for text-heavy PDFs
    and falls back to vision agent for image-heavy pages.

    Fast path (~5s): PyMuPDF text extraction + LLM standardization via chatCompletions
    Slow path (~50s): OpenClaw sub-agent with vision for image-heavy/scanned PDFs

    Args:
        file_path: Path to the PDF file
        llm_client: Ignored (backward compat)
        standardize: If True, runs LLM standardization pass

    Returns:
        {
            "raw_text": str,
            "pages": int,
            "text_pages": int,
            "vision_pages": int,
            "standardized": str | None
        }
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF not found: {file_path}")

    file_size = os.path.getsize(file_path)
    if file_size > MAX_FILE_SIZE:
        raise ValueError(f"File too large ({file_size // 1024}KB). Maximum is {MAX_FILE_SIZE // (1024*1024)}MB.")

    total_pages = _count_pdf_pages(file_path)
    if total_pages > MAX_PAGES:
        raise ValueError(f"PDF has {total_pages} pages. Maximum is {MAX_PAGES}.")

    # ── FAST PATH: Try text extraction first ──
    text_content, text_pages, image_pages = _try_text_extraction(file_path, total_pages)

    if text_content and image_pages == 0:
        # All pages are text-heavy — fast path, no agent needed
        logger.info(f"[PDFExtractor] Fast path: {text_pages} text pages, {len(text_content)} chars")
        standardized = None
        if standardize and text_content.strip():
            standardized = _standardize_via_chatcompletions(text_content)
        return {
            "raw_text": text_content,
            "pages": total_pages,
            "text_pages": text_pages,
            "vision_pages": 0,
            "standardized": standardized,
        }

    # ── SLOW PATH: Image-heavy pages need vision agent ──
    logger.info(f"[PDFExtractor] Vision path: {text_pages} text + {image_pages} image pages")
    return _extract_with_agent(file_path, total_pages, text_content, standardize)


def _try_text_extraction(file_path: str, total_pages: int):
    """Try extracting text from all pages via PyMuPDF. Returns (text, text_pages, image_pages)."""
    try:
        import fitz
    except ImportError:
        # No PyMuPDF — try pdftotext as fallback
        return _try_pdftotext(file_path, total_pages)

    doc = fitz.open(file_path)
    page_texts = []
    text_pages = 0
    image_pages = 0

    for page_num in range(min(len(doc), MAX_PAGES)):
        page = doc[page_num]
        text = page.get_text().strip()
        if len(text) >= TEXT_THRESHOLD:
            page_texts.append(f"--- Page {page_num + 1} ---\n{text}")
            text_pages += 1
        else:
            image_pages += 1

    doc.close()
    raw_text = "\n\n".join(page_texts)
    return raw_text, text_pages, image_pages


def _try_pdftotext(file_path: str, total_pages: int):
    """Fallback: extract text via pdftotext CLI."""
    import subprocess
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", file_path, "-"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and len(result.stdout.strip()) >= TEXT_THRESHOLD:
            return result.stdout.strip(), total_pages, 0
    except Exception:
        pass
    return "", 0, total_pages


def _standardize_via_chatcompletions(raw_text: str) -> Optional[str]:
    """Fast standardization via OpenClaw chatCompletions (no agent spawn)."""
    if len(raw_text) > 15000:
        raw_text = raw_text[:15000] + "\n\n[... truncated ...]"

    token = _get_token()
    try:
        resp = requests.post(
            f"{_OPENCLAW_URL}/v1/chat/completions",
            json={
                "model": "claude-sonnet-4-6",
                "messages": [
                    {"role": "system", "content": (
                        "Reorganize this startup executive summary into a structured format.\n"
                        "Output these sections (skip any with no data):\n"
                        "- Company: Name and one-line description\n"
                        "- Industry: Sector and sub-sector\n"
                        "- Product: What they build/sell\n"
                        "- Target Market: Who they sell to, TAM/SAM if available\n"
                        "- Business Model: How they make money\n"
                        "- Stage: Pre-seed/Seed/Series A/etc.\n"
                        "- Funding Raised: Amount raised and from whom\n"
                        "- Traction: Revenue, users, growth metrics\n"
                        "- Team: Key founders and their backgrounds\n"
                        "- Competitive Advantage: Moat, differentiation\n"
                        "- Ask: Funding amount and use of proceeds\n\n"
                        "Keep ALL numbers and data points. Do not invent information."
                    )},
                    {"role": "user", "content": f"Raw extracted text:\n\n{raw_text}"},
                ],
                "temperature": 0.2,
                "max_tokens": 3000,
            },
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            timeout=60,
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.warning(f"[PDFExtractor] chatCompletions standardization failed: {e}")

    # Return None to signal failure explicitly — callers must handle this.
    # Returning raw_text here would cause the LLM to receive unstructured data
    # and produce incorrect field extractions (company, industry, etc.).
    logger.warning("[PDFExtractor] Standardization failed — returning None. Caller must handle extraction failure.")
    return None


def _extract_with_agent(file_path: str, total_pages: int, text_so_far: str, standardize: bool) -> Dict[str, Any]:
    """Slow path: spawn OpenClaw agent for image-heavy pages with vision."""
    job_id = f"pdf_{int(time.time())}_{os.getpid()}"
    img_dir = f"/tmp/mirai/pdf_pages/{job_id}"
    result_path = f"/tmp/mirai/pdf_results/{job_id}.json"
    os.makedirs(img_dir, exist_ok=True)
    os.makedirs("/tmp/mirai/pdf_results", exist_ok=True)

    image_paths = _render_pages_as_images(file_path, img_dir)
    vision_pages = len(image_paths)

    image_instructions = ""
    if image_paths:
        image_list = "\n".join(f"  - Page {i+1}: {path}" for i, path in enumerate(image_paths))
        image_instructions = f"\n\nRead each page image for visual content (charts, infographics, embedded text):\n{image_list}"

    text_context = ""
    if text_so_far:
        text_context = f"\n\nText already extracted from text-heavy pages:\n{text_so_far[:3000]}"

    standardize_instruction = ""
    if standardize:
        standardize_instruction = ("\n\nStandardize into: Company, Industry, Product, Target Market, "
                                   "Business Model, Stage, Funding Raised, Traction, Team, Competitive Advantage, Ask.")

    task = f"""Extract content from this PDF's image-heavy pages.{text_context}{image_instructions}{standardize_instruction}

Write JSON to {result_path}: {{"raw_text": "...", "standardized": "...", "pages": {total_pages}}}"""

    spawn_result = _invoke_tool("sessions_spawn", {
        "task": task,
        "label": f"pdf-extract-{job_id}",
        "model": "claude-sonnet-4-6",
        "runTimeoutSeconds": 90,
        "cleanup": "delete",
    })

    if not spawn_result or not spawn_result.get("ok"):
        raise RuntimeError(f"Failed to spawn PDF extraction agent: {spawn_result}")

    for _ in range(180):
        time.sleep(0.5)
        if os.path.exists(result_path):
            try:
                with open(result_path, "r") as f:
                    content = f.read().strip()
                if not content:
                    continue
                data = _parse_result(content)
                if data:
                    _safe_remove(result_path)
                    _safe_remove_dir(img_dir)
                    return {
                        "raw_text": data.get("raw_text", content),
                        "pages": total_pages,
                        "text_pages": total_pages - vision_pages,
                        "vision_pages": vision_pages,
                        "standardized": data.get("standardized") if standardize else None,
                    }
            except Exception:
                pass

    _safe_remove(result_path)
    _safe_remove_dir(img_dir)
    raise RuntimeError("PDF extraction timed out")


def _parse_result(content: str) -> Optional[dict]:
    """Try to parse the agent's result as JSON."""
    # Strip markdown fences
    content = re.sub(r'^```(?:json)?\s*', '', content.strip())
    content = re.sub(r'\s*```$', '', content.strip())

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Find JSON object in text
    match = re.search(r'\{[\s\S]*\}', content)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # Raw text fallback
    if len(content) > 50:
        return {"raw_text": content, "standardized": content}

    return None


def _safe_remove(path: str) -> None:
    """Remove a file, ignoring errors."""
    try:
        os.unlink(path)
    except OSError:
        pass


def _safe_remove_dir(path: str) -> None:
    """Remove a directory tree, ignoring errors."""
    import shutil
    try:
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass

"""
PDF extraction module using PyMuPDF (fitz).
Extracts text, page counts, document SHA-256 hash, and page-level text blocks.
"""

import os
import hashlib
from typing import Dict, Any, List
import pymupdf

class PDFExtractor:
    @staticmethod
    def compute_sha256(filepath: str) -> str:
        if not os.path.exists(filepath):
            return ""
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    @classmethod
    def extract_document(cls, filepath: str) -> Dict[str, Any]:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")

        doc_hash = cls.compute_sha256(filepath)
        doc = pymupdf.open(filepath)
        page_count = len(doc)
        
        pages_text: List[str] = []
        full_text_parts: List[str] = []
        page_blocks: List[List[Dict[str, Any]]] = []

        for pno in range(page_count):
            page = doc[pno]
            text = page.get_text("text")
            pages_text.append(text)
            full_text_parts.append(text)
            
            # Extract structured text blocks for precise evidence location
            raw_blocks = page.get_text("blocks")
            blocks = []
            for b in raw_blocks:
                if len(b) >= 5 and b[4].strip():
                    blocks.append({
                        "bbox": (b[0], b[1], b[2], b[3]),
                        "text": b[4].strip(),
                        "page": pno + 1
                    })
            page_blocks.append(blocks)

        doc.close()
        return {
            "filepath": filepath,
            "filename": os.path.basename(filepath),
            "doc_hash": doc_hash,
            "page_count": page_count,
            "pages_text": pages_text,
            "full_text": "\n".join(full_text_parts),
            "page_blocks": page_blocks,
            "extraction_method": "PyMuPDF"
        }

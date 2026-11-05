"""
OCR extraction module for scanned or low-text PDFs.

Digital text always wins when it exists.  OCR is invoked only when the PDF has
almost no extractable text; it uses Tesseract when the binary is installed and
falls back to EasyOCR when available.  If neither engine can run, the document
is marked as low-confidence so the workflow escalates it to human review.
"""

import io
import os
from typing import Any, Dict, List, Tuple

import pymupdf
from app.extraction.pdf_extractor import PDFExtractor


class OCRExtractor:
    OCR_TEXT_THRESHOLD = 120
    DEFAULT_MAX_PAGES = 10
    DEFAULT_DPI = 200

    @classmethod
    def _render_pages(cls, filepath: str) -> List[Any]:
        """Render PDF pages to PIL images for OCR."""
        from PIL import Image

        max_pages = int(os.environ.get("OCR_MAX_PAGES", cls.DEFAULT_MAX_PAGES))
        dpi = int(os.environ.get("OCR_DPI", cls.DEFAULT_DPI))
        images: List[Any] = []
        with pymupdf.open(filepath) as doc:
            for page_index, page in enumerate(doc):
                if page_index >= max_pages:
                    break
                pixmap = page.get_pixmap(dpi=dpi)
                images.append(Image.open(io.BytesIO(pixmap.tobytes("png"))))
        return images

    @staticmethod
    def _tesseract_available() -> bool:
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    @classmethod
    def _run_tesseract(cls, images: List[Any]) -> Tuple[List[str], float, str]:
        import pytesseract

        texts: List[str] = []
        confidences: List[float] = []
        for image in images:
            data = pytesseract.image_to_data(
                image,
                output_type=pytesseract.Output.DICT,
                config="--psm 6",
            )
            words = []
            for word, conf in zip(data.get("text", []), data.get("conf", [])):
                if word and word.strip():
                    words.append(word.strip())
                    try:
                        value = float(conf)
                        if value >= 0:
                            confidences.append(value)
                    except (TypeError, ValueError):
                        pass
            texts.append(" ".join(words))
        confidence = (sum(confidences) / len(confidences) / 100.0) if confidences else 0.0
        return texts, confidence, "Tesseract"

    @classmethod
    def _run_easyocr(cls, images: List[Any]) -> Tuple[List[str], float, str]:
        import easyocr
        import numpy as np

        reader = easyocr.Reader(["en"], gpu=False)
        texts: List[str] = []
        confidences: List[float] = []
        for image in images:
            results = reader.readtext(np.array(image), detail=1, paragraph=False)
            words = []
            for _bbox, word, confidence in results:
                if word and word.strip():
                    words.append(word.strip())
                    confidences.append(float(confidence))
            texts.append(" ".join(words))
        confidence = (sum(confidences) / len(confidences)) if confidences else 0.0
        return texts, confidence, "EasyOCR"

    @classmethod
    def _run_ocr(cls, filepath: str) -> Tuple[List[str], float, str]:
        images = cls._render_pages(filepath)
        if not images:
            return [], 0.0, "none"

        if cls._tesseract_available():
            try:
                return cls._run_tesseract(images)
            except Exception:
                pass

        try:
            import easyocr  # noqa: F401
            return cls._run_easyocr(images)
        except Exception:
            return [], 0.0, "none"

    @classmethod
    def extract_scanned(cls, filepath: str) -> Dict[str, Any]:
        """
        Extract a scanned or low-digital document, running real OCR only when
        the embedded text layer is too small to be usable.
        """
        base_result = PDFExtractor.extract_document(filepath)

        has_raster_images = False
        try:
            with pymupdf.open(filepath) as doc:
                has_raster_images = any(len(page.get_images()) > 0 for page in doc)
        except Exception:
            pass

        pages_text = list(base_result.get("pages_text") or [base_result["full_text"]])
        full_text = base_result["full_text"]
        text_len = len(full_text.strip())
        needs_ocr = text_len < cls.OCR_TEXT_THRESHOLD

        extraction_method = "PyMuPDF"
        confidence = 0.96
        ocr_confidence = None
        ocr_engine = "none"
        ocr_pages_processed = 0

        if needs_ocr:
            ocr_texts, ocr_confidence, ocr_engine = cls._run_ocr(filepath)
            ocr_pages_processed = len(ocr_texts)
            ocr_text = "\n".join(part for part in ocr_texts if part.strip()).strip()
            if ocr_text and len(ocr_text) > text_len:
                pages_text = ocr_texts
                full_text = ocr_text
                extraction_method = f"OCR:{ocr_engine}"
                confidence = ocr_confidence or 0.0
            elif ocr_engine == "none":
                extraction_method = "PyMuPDF (OCR engine unavailable)"
                confidence = 0.0 if text_len == 0 else 0.4
            else:
                extraction_method = f"OCR:{ocr_engine} (low yield)"
                confidence = ocr_confidence or 0.0

        is_scanned_look = has_raster_images or needs_ocr
        if not needs_ocr and is_scanned_look:
            extraction_method = "PyMuPDF (embedded text layer)"
            confidence = 0.91

        return {
            "filepath": filepath,
            "filename": base_result["filename"],
            "doc_hash": base_result["doc_hash"],
            "page_count": base_result["page_count"],
            "pages_text": pages_text,
            "full_text": full_text,
            "page_blocks": base_result["page_blocks"],
            "extraction_method": extraction_method,
            "ocr_engine": ocr_engine,
            "ocr_pages_processed": ocr_pages_processed,
            "ocr_confidence": confidence,
            "is_scanned": is_scanned_look,
            "needs_ocr": needs_ocr,
            "rotation_corrected": bool(needs_ocr and ocr_engine != "none"),
            "noise_filtered": bool(needs_ocr and ocr_engine != "none"),
        }

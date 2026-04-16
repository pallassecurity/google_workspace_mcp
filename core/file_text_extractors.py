import io
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def extract_pdf_text(file_bytes: bytes) -> Optional[str]:
    """
    Extract plain text from a PDF document.

    Returns plain text when the PDF contains extractable text, else None.
    If the PDF parser is unavailable or the PDF has no extractable text,
    returns None so callers can fall back gracefully.
    """
    try:
        from pypdf import PdfReader
    except Exception as e:
        logger.warning(f"PDF text extraction unavailable: {e}")
        return None

    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        page_text_parts: List[str] = []

        for page_number, page in enumerate(reader.pages, start=1):
            try:
                extracted_text = page.extract_text()
            except Exception as e:
                logger.warning(
                    f"Failed to extract text from PDF page {page_number}: {e}"
                )
                continue

            if extracted_text:
                cleaned_text = extracted_text.strip()
                if cleaned_text:
                    page_text_parts.append(cleaned_text)

        if not page_text_parts:
            return None

        return "\n\n".join(page_text_parts)
    except Exception as e:
        logger.error(f"Failed to extract PDF text: {e}", exc_info=True)
        return None

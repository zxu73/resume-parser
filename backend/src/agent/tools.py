import os
import io
from typing import Dict, Any
import fitz  # pymupdf
import docx
from docx.oxml.ns import qn


def extract_text_from_pdf(content: bytes) -> str:
    try:
        doc = fitz.open(stream=content, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text() + "\n"
        return text.strip()
    except Exception as e:
        return f"Error extracting PDF text: {str(e)}"


def extract_text_from_docx(content: bytes) -> str:
    try:
        doc = docx.Document(io.BytesIO(content))
        lines = []
        for block in doc.element.body:
            if block.tag == qn("w:p"):
                text = "".join(t.text or "" for t in block.iter(qn("w:t")))
                if text.strip():
                    lines.append(text)
            elif block.tag == qn("w:tbl"):
                for row in block.iter(qn("w:tr")):
                    cells = []
                    for cell in row.iter(qn("w:tc")):
                        cell_text = "".join(t.text or "" for t in cell.iter(qn("w:t")))
                        if cell_text.strip():
                            cells.append(cell_text.strip())
                    if cells:
                        lines.append("  ".join(cells))
        return "\n".join(lines).strip()
    except Exception as e:
        return f"Error extracting DOCX text: {str(e)}"


def analyze_resume_file(content: bytes, file_extension: str) -> Dict[str, Any]:
    try:
        if file_extension.lower() == "pdf":
            text = extract_text_from_pdf(content)
        elif file_extension.lower() in ["doc", "docx"]:
            text = extract_text_from_docx(content)
        elif file_extension.lower() == "txt":
            text = content.decode("utf-8")
        else:
            return {"success": False, "error": f"Unsupported file type: {file_extension}"}

        if not text or text.startswith("Error"):
            return {"success": False, "error": f"Failed to extract text from file: {text}"}

        return {"success": True, "analysis": "", "extracted_text": text}

    except Exception as e:
        return {"success": False, "error": f"Resume analysis failed: {str(e)}"}

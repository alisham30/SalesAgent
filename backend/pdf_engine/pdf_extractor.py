"""
PDF extractor module
Extracts text from PDFs using multiple methods with fallback
"""
from pathlib import Path
from typing import Optional
from backend import config
from backend.utils.logger import logger
from backend.utils.text_cleaner import clean_text

class PDFExtractor:
    """Extracts text from PDF files using multiple methods"""
    
    def __init__(self):
        self.extraction_methods = config.PDF_EXTRACTION_METHODS
        self.ocr_enabled = config.ENABLE_OCR
    
    def extract_text(self, pdf_path: Path) -> str:
        """
        Extract text from PDF using fallback methods
        
        Args:
            pdf_path: Path to PDF file
        
        Returns:
            Extracted text
        """
        if not pdf_path.exists():
            logger.error(f"PDF file not found: {pdf_path}")
            return ""
        
        logger.info(f"Extracting text from: {pdf_path}")
        
        for method in self.extraction_methods:
            try:
                if method == "pypdf2":
                    text = self._extract_with_pypdf2(pdf_path)
                    if text and len(text.strip()) > 50:  # Minimum text threshold
                        logger.info(f"Successfully extracted text using PyPDF2")
                        return clean_text(text)
                
                elif method == "pdfminer":
                    text = self._extract_with_pdfminer(pdf_path)
                    if text and len(text.strip()) > 50:
                        logger.info(f"Successfully extracted text using pdfminer")
                        return clean_text(text)
                
                elif method == "pdfplumber":
                    text = self._extract_with_pdfplumber(pdf_path)
                    if text and len(text.strip()) > 50:
                        logger.info(f"Successfully extracted text using pdfplumber")
                        return clean_text(text)
                
                elif method == "ocr" and self.ocr_enabled:
                    text = self._extract_with_ocr(pdf_path)
                    if text and len(text.strip()) > 50:
                        logger.info(f"Successfully extracted text using OCR")
                        return clean_text(text)
                        
            except Exception as e:
                logger.warning(f"Method {method} failed: {e}")
                continue
        
        logger.error(f"All extraction methods failed for: {pdf_path}")
        return ""
    
    def _extract_with_pypdf2(self, pdf_path: Path) -> str:
        """Extract text using PyPDF2"""
        try:
            import PyPDF2
            text = ""
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            return text
        except ImportError:
            logger.warning("PyPDF2 not installed")
            return ""
        except Exception as e:
            logger.warning(f"PyPDF2 extraction error: {e}")
            return ""
    
    def _extract_with_pdfminer(self, pdf_path: Path) -> str:
        """Extract text using pdfminer"""
        try:
            from pdfminer.high_level import extract_text
            text = extract_text(str(pdf_path))
            return text
        except ImportError:
            logger.warning("pdfminer not installed")
            return ""
        except Exception as e:
            logger.warning(f"pdfminer extraction error: {e}")
            return ""
    
    def _extract_with_pdfplumber(self, pdf_path: Path) -> str:
        """Extract text using pdfplumber"""
        try:
            import pdfplumber
            text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            return text
        except ImportError:
            logger.warning("pdfplumber not installed")
            return ""
        except Exception as e:
            logger.warning(f"pdfplumber extraction error: {e}")
            return ""
    
    def _extract_with_ocr(self, pdf_path: Path) -> str:
        """Extract text using OCR (Tesseract)"""
        try:
            from pdf2image import convert_from_path
            import pytesseract
            
            # Convert PDF to images
            images = convert_from_path(str(pdf_path))
            text = ""
            
            for image in images:
                page_text = pytesseract.image_to_string(image, lang=config.OCR_LANGUAGE)
                text += page_text + "\n"
            
            return text
        except ImportError:
            logger.warning("OCR dependencies (pdf2image, pytesseract) not installed")
            return ""
        except Exception as e:
            logger.warning(f"OCR extraction error: {e}")
            return ""


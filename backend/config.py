"""
Configuration file for tender agent
Contains Gmail API credentials, folder paths, and API keys
"""
import os
from pathlib import Path

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, use environment variables directly

# Base directory
BASE_DIR = Path(__file__).parent.parent

# Gmail API Configuration
GMAIL_CREDENTIALS_FILE = os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json")
GMAIL_TOKEN_FILE = os.getenv("GMAIL_TOKEN_FILE", "token.json")
GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Folder paths
PDFS_DIR = BASE_DIR / "pdfs"
MAIL_PDFS_DIR = PDFS_DIR / "mail_pdfs"
PORTAL_PDFS_DIR = PDFS_DIR / "portal_pdfs"
LINKED_PDFS_DIR = PDFS_DIR / "linked_pdfs"

OUTPUT_DIR = BASE_DIR / "backend" / "output"
EXTRACTED_DIR = OUTPUT_DIR / "extracted"
RAW_TEXT_DIR = OUTPUT_DIR / "raw_text"

MODELS_DIR = BASE_DIR / "models"

# LLM Configuration
# Support both OPENAI_API_KEY (standard) and LLM_API_KEY (custom)
LLM_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY", "")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")  # openai, anthropic, etc.
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")  # Default model
LLM_BASE_URL = os.getenv("LLM_BASE_URL", None)  # For custom endpoints

# Tender ID Configuration
TENDER_ID_PREFIX = "TDR"
TENDER_ID_YEAR = 2025
TENDER_ID_COUNTER_START = 1

# PDF Processing Configuration
PDF_EXTRACTION_METHODS = ["pypdf2", "pdfminer", "pdfplumber", "ocr"]  # Fallback order
ENABLE_OCR = True
OCR_LANGUAGE = "eng"

# Email Classification
TENDER_KEYWORDS = [
    "tender", "bid", "bidding", "rfq", "rfp", "request for quotation",
    "request for proposal", "procurement", "supply", "delivery",
    "technical specification", "boq", "bill of quantities",
    "warranty", "delivery deadline", "submission date"
]

# Technical Specification Keywords
TECH_SPEC_KEYWORDS = [
    "specification", "technical", "standard", "grade", "voltage",
    "conductor", "insulation", "sheath", "compliance", "conforms to",
    "as per", "IS", "IEC", "IEEE", "BS", "ASTM"
]

# Important Info Keywords
IMPORTANT_INFO_KEYWORDS = {
    "delivery": ["delivery", "delivery period", "delivery time", "lead time"],
    "deadline": ["deadline", "submission date", "closing date", "last date"],
    "warranty": ["warranty", "guarantee", "guaranteed"],
    "quantity": ["quantity", "qty", "qty.", "amount", "meters", "pieces"],
    "voltage": ["voltage", "voltage grade", "voltage rating", "V"],
    "standards": ["IS", "IEC", "IEEE", "BS", "ASTM", "standard", "specification"]
}

# Create directories if they don't exist
for directory in [PDFS_DIR, MAIL_PDFS_DIR, PORTAL_PDFS_DIR, LINKED_PDFS_DIR,
                  OUTPUT_DIR, EXTRACTED_DIR, RAW_TEXT_DIR, MODELS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)


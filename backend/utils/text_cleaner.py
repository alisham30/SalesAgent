"""
Text cleaning utility module
Cleans extracted text from PDFs and emails
"""
import re
from typing import List

def clean_text(text: str) -> str:
    """
    Clean extracted text by removing extra whitespace and normalizing
    
    Args:
        text: Raw text to clean
    
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove special characters that might be artifacts
    text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f]', '', text)
    
    # Normalize line breaks
    text = re.sub(r'\n\s*\n', '\n\n', text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text

def split_into_paragraphs(text: str) -> List[str]:
    """
    Split text into paragraphs
    
    Args:
        text: Text to split
    
    Returns:
        List of paragraphs
    """
    paragraphs = re.split(r'\n\s*\n', text)
    return [clean_text(p) for p in paragraphs if clean_text(p)]

def extract_sentences(text: str) -> List[str]:
    """
    Extract sentences from text
    
    Args:
        text: Text to extract sentences from
    
    Returns:
        List of sentences
    """
    # Simple sentence splitting
    sentences = re.split(r'[.!?]+\s+', text)
    return [clean_text(s) for s in sentences if clean_text(s)]

def normalize_whitespace(text: str) -> str:
    """
    Normalize whitespace in text
    
    Args:
        text: Text to normalize
    
    Returns:
        Normalized text
    """
    # Replace multiple spaces with single space
    text = re.sub(r' +', ' ', text)
    # Replace multiple newlines with double newline
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    return text.strip()


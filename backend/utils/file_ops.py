"""
File operations utility module
Handles saving PDFs, creating folders, listing files
"""
import shutil
from pathlib import Path
from typing import List, Optional
from backend.utils.logger import logger

def ensure_directory(path: Path) -> Path:
    """
    Ensure directory exists, create if it doesn't
    
    Args:
        path: Directory path
    
    Returns:
        Path object
    """
    path.mkdir(parents=True, exist_ok=True)
    return path

def save_pdf(file_path: Path, destination_dir: Path, filename: Optional[str] = None) -> Path:
    """
    Save PDF file to destination directory
    
    Args:
        file_path: Source file path
        destination_dir: Destination directory
        filename: Optional custom filename
    
    Returns:
        Path to saved file
    """
    ensure_directory(destination_dir)
    
    if filename is None:
        filename = file_path.name
    
    destination = destination_dir / filename
    
    # Handle duplicate filenames
    counter = 1
    original_destination = destination
    while destination.exists():
        stem = original_destination.stem
        suffix = original_destination.suffix
        destination = destination_dir / f"{stem}_{counter}{suffix}"
        counter += 1
    
    shutil.copy2(file_path, destination)
    logger.info(f"Saved PDF: {destination}")
    return destination

def list_pdf_files(directory: Path) -> List[Path]:
    """
    List all PDF files in a directory
    
    Args:
        directory: Directory to search
    
    Returns:
        List of PDF file paths
    """
    if not directory.exists():
        logger.warning(f"Directory does not exist: {directory}")
        return []
    
    pdf_files = list(directory.glob("*.pdf"))
    logger.info(f"Found {len(pdf_files)} PDF files in {directory}")
    return pdf_files

def save_text_file(content: str, destination_dir: Path, filename: str) -> Path:
    """
    Save text content to a file
    
    Args:
        content: Text content to save
        destination_dir: Destination directory
        filename: Filename
    
    Returns:
        Path to saved file
    """
    ensure_directory(destination_dir)
    file_path = destination_dir / filename
    file_path.write_text(content, encoding='utf-8')
    logger.info(f"Saved text file: {file_path}")
    return file_path

def save_json_file(data: dict, destination_dir: Path, filename: str) -> Path:
    """
    Save JSON data to a file
    
    Args:
        data: Dictionary to save as JSON
        destination_dir: Destination directory
        filename: Filename (should include .json extension)
    
    Returns:
        Path to saved file
    """
    import json
    ensure_directory(destination_dir)
    file_path = destination_dir / filename
    file_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    logger.info(f"Saved JSON file: {file_path}")
    return file_path


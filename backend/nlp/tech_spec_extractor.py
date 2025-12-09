"""
Technical specification extractor module
Uses rules and LLM to extract product specifications
"""
from typing import List, Dict
from backend import config
from backend.utils.logger import logger
from backend.pdf_engine.spec_classifier import SpecClassifier
from backend.pdf_engine.paragraph_parser import ParagraphParser
from backend.nlp.llm_agent import LLMAgent

class TechSpecExtractor:
    """Extracts technical specifications from text"""
    
    def __init__(self):
        self.spec_classifier = SpecClassifier()
        self.paragraph_parser = ParagraphParser()
        self.llm_agent = LLMAgent()
    
    def extract_specs(self, text: str, use_llm: bool = True) -> Dict:
        """
        Extract technical specifications from text
        
        Args:
            text: Text to extract from
            use_llm: Whether to use LLM for formatting
        
        Returns:
            Dictionary with formatted specifications
        """
        # Parse into paragraphs and sentences
        paragraphs = self.paragraph_parser.parse_paragraphs(text)
        sentences = self.paragraph_parser.parse_sentences(text)
        
        # Classify technical specifications
        spec_paragraphs = []
        spec_sentences = []
        
        for para in paragraphs:
            if self.spec_classifier.is_technical_spec(para):
                spec_paragraphs.append(para)
        
        for sent in sentences:
            if self.spec_classifier.is_technical_spec(sent):
                spec_sentences.append(sent)
        
        # Combine all specs
        all_specs = spec_paragraphs + spec_sentences
        
        # Remove duplicates while preserving order
        seen = set()
        unique_specs = []
        for spec in all_specs:
            spec_lower = spec.lower().strip()
            if spec_lower and spec_lower not in seen:
                seen.add(spec_lower)
                unique_specs.append(spec)
        
        # Format using LLM if available
        formatted_specs = ""
        if use_llm and unique_specs:
            formatted_specs = self.llm_agent.format_technical_specs(unique_specs)
        
        if not formatted_specs:
            # Fallback formatting
            formatted_specs = "\n".join(f"• {spec}" for spec in unique_specs)
        
        return {
            'raw_specs': unique_specs,
            'formatted_specs': formatted_specs,
            'count': len(unique_specs)
        }


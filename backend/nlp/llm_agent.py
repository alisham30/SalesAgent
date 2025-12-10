"""
LLM agent module
Wrapper for LLM API calls for formatting and refining outputs
"""
import json
import re
from typing import Dict, List, Optional
from backend import config
from backend.utils.logger import logger

class LLMAgent:
    """LLM wrapper for formatting and extracting information"""
    
    def __init__(self):
        self.api_key = config.LLM_API_KEY
        self.provider = config.LLM_PROVIDER
        self.model = config.LLM_MODEL
        self.base_url = config.LLM_BASE_URL
        
        if not self.api_key:
            logger.warning("LLM API key not set. LLM features will be disabled.")
    
    def _call_openai(self, prompt: str, system_prompt: str = None) -> Optional[str]:
        """Call OpenAI API"""
        try:
            import openai
            
            if self.base_url:
                client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)
            else:
                client = openai.OpenAI(api_key=self.api_key)
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3
            )
            
            return response.choices[0].message.content
            
        except ImportError:
            logger.error("OpenAI library not installed")
            return None
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return None
    
    def _call_anthropic(self, prompt: str, system_prompt: str = None) -> Optional[str]:
        """Call Anthropic API"""
        try:
            import anthropic
            
            client = anthropic.Anthropic(api_key=self.api_key)
            
            messages = [{"role": "user", "content": prompt}]
            
            response = client.messages.create(
                model=self.model,
                max_tokens=4000,
                system=system_prompt or "",
                messages=messages
            )
            
            return response.content[0].text
            
        except ImportError:
            logger.error("Anthropic library not installed")
            return None
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            return None
    
    def call_llm(self, prompt: str, system_prompt: str = None) -> Optional[str]:
        """
        Call LLM with prompt
        
        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)
        
        Returns:
            LLM response or None if failed
        """
        if not self.api_key:
            return None
        
        if self.provider.lower() == "openai":
            return self._call_openai(prompt, system_prompt)
        elif self.provider.lower() == "anthropic":
            return self._call_anthropic(prompt, system_prompt)
        else:
            logger.error(f"Unknown LLM provider: {self.provider}")
            return None
    
    def format_technical_specs(self, raw_specs: List[str]) -> str:
        """
        Format technical specifications into clean structure
        
        Args:
            raw_specs: List of raw specification strings
        
        Returns:
            Formatted specifications
        """
        if not raw_specs:
            return ""
        
        system_prompt = """You are a technical specification formatter. 
        Format technical specifications into clean, structured bullet points.
        Remove redundancy and organize information clearly."""
        
        prompt = f"""Format the following technical specifications into clean bullet points:

{chr(10).join(raw_specs)}

Output format:
- Each specification as a clear bullet point
- Remove redundant information
- Organize by category if applicable
- Keep technical details precise"""
        
        result = self.call_llm(prompt, system_prompt)
        
        if result:
            return result
        
        # Fallback to simple formatting
        return "\n".join(f"• {spec}" for spec in raw_specs if spec.strip())
    
    def extract_structured_info(self, text: str) -> Dict:
        """
        Extract structured information from text using LLM
        
        Args:
            text: Text to extract from
        
        Returns:
            Dictionary with structured information
        """
        system_prompt = """You are a tender information extraction expert.
        Extract technical specifications, delivery deadlines, quantities, warranty, and other important information from tender documents.
        Return structured JSON format."""
        
        prompt = f"""Extract the following information from this tender document text:

{text[:5000]}  # Limit text length

Extract ONLY these fields:
1. Technical specifications (detailed, if present in document)
2. Delivery deadline/period
3. Project name (the name/title of the project/tender)
4. Ministry (the ministry or department issuing the tender)

Return as JSON with these keys: technical_specs, delivery, project_name, ministry"""
        
        result = self.call_llm(prompt, system_prompt)
        
        if result:
            try:
                # Try to extract JSON from response
                json_match = re.search(r'\{.*\}', result, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            except Exception as e:
                logger.warning(f"Failed to parse LLM JSON response: {e}")
        
        return {}


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
        Only extracts actual product specifications (like Category, Type, Nominal, etc.)
        Excludes terms/conditions, delivery, compliance, etc.
        
        Args:
            text: Text to extract from
            use_llm: Whether to use LLM for formatting
        
        Returns:
            Dictionary with formatted specifications
        """
        # First, extract only the Technical Specification section
        tech_spec_text = self._extract_tech_spec_section_only(text)
        
        if not tech_spec_text:
            logger.debug("No Technical Specification section found")
            return {
                'raw_specs': [],
                'formatted_specs': '',
                'count': 0
            }
        
        # Extract actual product specifications (key-value pairs)
        product_specs = self._extract_product_specifications(tech_spec_text)
        
        if not product_specs:
            logger.debug("No product specifications found in Technical Specification section")
            return {
                'raw_specs': [],
                'formatted_specs': '',
                'count': 0
            }
        
        # Format specifications in concise vertical format
        formatted_specs = self._format_specs_concise(product_specs)
        
        return {
            'raw_specs': product_specs,
            'formatted_specs': formatted_specs,
            'count': len(product_specs)
        }
    
    def _format_specs_concise(self, specs: List[str]) -> str:
        """
        Format specifications in concise vertical format (one per line)
        
        Args:
            specs: List of specification strings
        
        Returns:
            Concise formatted string
        """
        if not specs:
            return ""
        
        # Clean and format each spec
        formatted = []
        for spec in specs:
            # Remove extra whitespace and clean up
            spec = ' '.join(spec.split())
            # Remove redundant prefixes
            spec = spec.replace('•', '').strip()
            if spec and len(spec) < 200:  # Keep concise
                formatted.append(spec)
        
        # Return one spec per line (vertical format)
        return "\n".join(formatted)
    
    def _extract_product_specifications(self, text: str) -> List[str]:
        """
        Extract actual product specifications from tables or text
        Handles both table format and key-value format
        
        Args:
            text: Technical specification section text
        
        Returns:
            List of specification strings in format "Key: Value"
        """
        import re
        
        lines = text.split('\n')
        specs = []
        
        # Keywords that indicate actual product specs (expanded list)
        product_spec_keywords = [
            'category', 'type', 'nominal', 'conductor', 'insulation', 'sheath',
            'cable', 'core', 'area', 'voltage', 'grade', 'material', 'colour', 'color',
            'construction', 'standard', 'conform', 'comply', 'specification name',
            'allowed values', 'bid requirement', 'classification', 'armouring', 'armoring',
            'outer sheath', 'inner sheath', 'marking', 'packing', 'certification',
            'conformity', 'suitable for', 'wound on', 'length', 'drum', 'item category',
            'product category', 'polymer', 'insulator', 'disc', 'pin', 'acsr', 'conductor',
            'lattice tower', 'guard wire', 'stay wire', 'distribution panel', 'pvc cable',
            'casing capping', 'transmission line', 'switchgear', 'busbar', 'mcb', 'mccb',
            'as per', 'is:', 'iec', 'ieee', 'conforming to', 'per is'
        ]
        
        # Keywords that indicate terms/conditions (exclude these)
        exclude_keywords = [
            'delivery', 'period', 'days', 'weeks', 'months', 'validity',
            'bid end', 'bid opening', 'submission', 'deadline',
            'terms and conditions', 'compliance', 'laws', 'grievance',
            'exemption', 'preference', 'evaluation', 'payment', 'invoice',
            'consignee', 'inspection', 'warranty', 'guarantee', 'option clause',
            'purchaser reserves', 'must be raised', 'must comply', 'eligible micro'
        ]
        
        # Extract from table format (Specification Name | Allowed Values)
        table_specs = self._extract_table_format_specs(text)
        specs.extend(table_specs)
        
        # Extract item categories and product lists
        item_categories = self._extract_item_categories(text)
        specs.extend(item_categories)
        
        # Extract key-value pairs from text
        for i, line in enumerate(lines):
            line = line.strip()
            if not line or len(line) < 5:
                continue
            
            line_lower = line.lower()
            
            # Skip if it's clearly terms/conditions
            if any(exclude in line_lower for exclude in exclude_keywords):
                continue
            
            # Skip headers and separators
            if line.isupper() and len(line) < 50:
                continue
            if line in ['|', '-', '_', '---', '==='] or len(line) < 3:
                continue
            
            # Look for key-value patterns
            if ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    
                    # Check if key contains product spec keywords
                    if any(keyword in key.lower() for keyword in product_spec_keywords):
                        if value and len(value) < 150:
                            spec = f"{key}: {value}"
                            specs.append(spec)
            
            # Also check for patterns like "Key - Value" or "Key Value"
            elif any(keyword in line_lower for keyword in product_spec_keywords):
                # Try to find value in next line
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if next_line and len(next_line) < 150:
                        if not any(exclude in next_line.lower() for exclude in exclude_keywords):
                            spec = f"{line}: {next_line}"
                            specs.append(spec)
        
        # Remove duplicates and clean
        seen = set()
        unique_specs = []
        for spec in specs:
            spec_clean = ' '.join(spec.split())  # Normalize whitespace
            spec_lower = spec_clean.lower().strip()
            if spec_lower and spec_lower not in seen and len(spec_clean) < 200:
                seen.add(spec_lower)
                unique_specs.append(spec_clean)
        
        return unique_specs
    
    def _extract_table_format_specs(self, text: str) -> List[str]:
        """
        Extract specifications from table format
        Handles tables with columns like "Specification Name" and "Allowed Values"
        
        Args:
            text: Text containing table
        
        Returns:
            List of "Key: Value" specification strings
        """
        import re
        
        specs = []
        lines = text.split('\n')
        
        # Look for table rows - typically have multiple columns separated by spaces/tabs
        # Pattern: Specification Name followed by value(s)
        
        # Common specification field patterns
        spec_fields = {
            'category of cable': r'category\s+of\s+cable',
            'type of insulation': r'type\s+of\s+insulation',
            'cable construction type': r'cable\s+construction\s+type',
            'nominal area of conductor': r'nominal\s+(?:area\s+of\s+conductor|cross\s+sectional\s+area)',
            'number of core': r'number\s+of\s+core|no\s+of\s+core',
            'sheath type': r'sheath\s+type',
            'colour of sheath': r'colour?\s+of\s+sheath',
            'material of conductor': r'material\s+of\s+conductor',
            'type of cable': r'type\s+of\s+cable',
            'material of armouring': r'material\s+of\s+armouring',
            'type of outer sheath': r'type\s+of\s+outer\s+sheath',
            'type of inner sheath': r'type\s+of\s+inner\s+sheath',
            'conformity': r'conformity\s+of\s+the\s+specification',
            'classification': r'classification\s+of\s+cables',
            'construction of conductor': r'construction\s+of\s+the\s+conductor',
            'type of armouring': r'type\s+of\s+armouring',
            'standard length': r'standard\s+length\s+of\s+cable',
            'cable wound on': r'cable\s+wound\s+on',
        }
        
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            
            # Check each spec field pattern
            for field_name, pattern in spec_fields.items():
                if re.search(pattern, line_lower, re.IGNORECASE):
                    # Try to extract value from same line or next lines
                    # Look for value after colon, dash, or in next column
                    value = None
                    
                    # Check same line for value
                    if ':' in line:
                        parts = line.split(':', 1)
                        if len(parts) == 2:
                            value = parts[1].strip()
                    elif '|' in line:
                        # Table format - value might be in next column
                        cols = [c.strip() for c in line.split('|')]
                        if len(cols) >= 3:  # Usually: Description | Spec Name | Value
                            value = cols[-1].strip()  # Last column is usually the value
                    
                    # If not found, check next 2 lines
                    if not value or len(value) < 2:
                        for j in range(i+1, min(i+3, len(lines))):
                            next_line = lines[j].strip()
                            if next_line and len(next_line) < 150:
                                # Check if it's a value (not another field name)
                                if not any(fn in next_line.lower() for fn in spec_fields.keys()):
                                    value = next_line
                                    break
                    
                    if value and len(value) < 150:
                        # Get original case for field name
                        orig_line = line.strip()
                        if ':' in orig_line:
                            key = orig_line.split(':', 1)[0].strip()
                        else:
                            key = field_name.title()
                        spec = f"{key}: {value}"
                        specs.append(spec)
                    break
        
        return specs
    
    def _extract_item_categories(self, text: str) -> List[str]:
        """
        Extract item categories and product lists from text
        e.g., "Item Category: polymer pin insulator, polymer Disc insulator, ACSR DOG conductor..."
        
        Args:
            text: Text to extract from
        
        Returns:
            List of item category strings
        """
        import re
        
        specs = []
        lines = text.split('\n')
        
        # Look for item category patterns
        item_category_patterns = [
            r'item\s+category[:\s]+([^\n]{10,500})',
            r'product\s+category[:\s]+([^\n]{10,500})',
            r'वस्तु\s+श्रेणी[:\s]+([^\n]{10,500})',
            r'item\s+description[:\s]+([^\n]{10,500})',
        ]
        
        for line in lines:
            line_lower = line.lower()
            for pattern in item_category_patterns:
                match = re.search(pattern, line_lower, re.IGNORECASE)
                if match:
                    category_text = match.group(1).strip()
                    # Clean up
                    category_text = re.sub(r'\s+', ' ', category_text)
                    if len(category_text) > 10 and len(category_text) < 500:
                        # Get original case
                        orig_line = line.strip()
                        if ':' in orig_line:
                            parts = orig_line.split(':', 1)
                            if len(parts) == 2:
                                key = parts[0].strip()
                                value = parts[1].strip()
                                specs.append(f"{key}: {value}")
                        else:
                            specs.append(f"Item Category: {category_text}")
                    break
        
        return specs
    
    def _extract_table_specifications_old(self, text: str) -> List[str]:
        """
        Extract specifications from table format
        Looks for patterns like "Category of cable: FR" or "Type of Insulation: Type C"
        
        Args:
            text: Text to extract from
        
        Returns:
            List of specification strings
        """
        import re
        
        specs = []
        lines = text.split('\n')
        
        # Common specification field names
        spec_field_names = [
            'category of cable', 'type of insulation', 'cable construction type',
            'no of core', 'number of cores', 'nominal cross sectional area',
            'nominal area of conductor', 'sheath type', 'colour of sheath',
            'color of sheath', 'conductor material', 'type of cable',
            'material of conductor', 'material of armouring', 'type of outer sheath',
            'standard length', 'conformity standards', 'specification name'
        ]
        
        # Look for lines that contain spec field names followed by values
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            
            # Check if line contains a spec field name
            for field_name in spec_field_names:
                if field_name in line_lower:
                    # Try to extract the value
                    # Pattern: field_name: value or field_name value
                    pattern = re.escape(field_name) + r'[:\s]+([^\n]{1,100})'
                    match = re.search(pattern, line_lower, re.IGNORECASE)
                    if match:
                        value = match.group(1).strip()
                        # Clean up value
                        value = re.sub(r'[^\w\s\.\-\/\(\)]+', '', value).strip()
                        if value and len(value) < 150:
                            # Get original case for field name
                            orig_line = line.strip()
                            if ':' in orig_line:
                                parts = orig_line.split(':', 1)
                                if len(parts) == 2:
                                    field = parts[0].strip()
                                    val = parts[1].strip()
                                    if val and len(val) < 150:
                                        specs.append(f"{field}: {val}")
                            else:
                                # Try to find the value in next lines
                                for j in range(i+1, min(i+3, len(lines))):
                                    next_line = lines[j].strip()
                                    if next_line and len(next_line) < 150:
                                        # Check if it looks like a value (not another field name)
                                        if not any(fn in next_line.lower() for fn in spec_field_names):
                                            specs.append(f"{field_name.title()}: {next_line}")
                                            break
                    break
        
        # Also look for simple key-value patterns in the text
        key_value_pattern = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:of|for|type|category|material|colour|color|area|number|no\.?))[:\s]+([^\n]{3,100})'
        matches = re.finditer(key_value_pattern, text, re.IGNORECASE)
        for match in matches:
            key = match.group(1).strip()
            value = match.group(2).strip()
            # Check if it's a real spec (not terms/conditions)
            if not self._is_excluded_content(f"{key} {value}"):
                if len(value) < 150 and any(kw in key.lower() for kw in ['category', 'type', 'nominal', 'conductor', 'insulation', 'sheath', 'cable', 'core', 'area', 'material', 'colour', 'color']):
                    specs.append(f"{key}: {value}")
        
        return specs
    
    def _extract_tech_spec_section_only(self, text: str) -> str:
        """
        Extract only the Technical Specification section, excluding other content
        
        Args:
            text: Full text
        
        Returns:
            Text from tech spec section only
        """
        import re
        
        lines = text.split('\n')
        tech_spec_patterns = [
            r'technical\s+specification[s]?[:\s]*',
            r'tech\s+spec[s]?[:\s]*',
            r'specification[s]?[:\s]*',
            r'technical\s+requirement[s]?[:\s]*',
            r'product\s+specification[s]?[:\s]*',
            r'item\s+specification[s]?[:\s]*',
        ]
        
        in_tech_spec_section = False
        tech_spec_lines = []
        section_end_keywords = [
            'terms and conditions', 'general terms', 'payment terms', 'delivery period',
            'delivery days', 'delivery quantity', 'warranty', 'evaluation', 'commercial',
            'bid end', 'bid opening', 'submission', 'annexure', 'appendix', 'schedule',
            'boq', 'bill of quantities', 'categories where', 'general terms and conditions',
            'conclusion', 'disclaimer', 'eligible micro', 'benefits for', 'grievance',
            'compliance with laws', 'must comply', 'option clause', 'purchaser reserves',
            'additional terms', 'compliance requirements', 'restrictions on procurement'
        ]
        
        # Keywords that indicate actual product specs (keep these)
        product_spec_indicators = [
            'category', 'type of', 'nominal', 'conductor', 'insulation', 'sheath',
            'cable', 'core', 'area', 'voltage', 'grade', 'material', 'colour', 'color',
            'construction', 'standard', 'conform', 'comply', 'specification name',
            'allowed values', 'bid requirement'
        ]
        
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            
            # Check if this line is a tech spec header
            is_tech_spec_header = any(
                re.search(pattern, line_lower, re.IGNORECASE) 
                for pattern in tech_spec_patterns
            )
            
            if is_tech_spec_header:
                in_tech_spec_section = True
                tech_spec_lines.append(line)
                continue
            
            # If we're in a tech spec section, collect text
            if in_tech_spec_section:
                # STRICT: If line contains terms/conditions keywords, stop immediately
                if any(keyword in line_lower for keyword in section_end_keywords):
                    # Only continue if it's clearly still part of specs (like "Technical Specifications - Delivery")
                    if not any(indicator in line_lower for indicator in product_spec_indicators):
                        # We've definitely left the tech spec section
                        break
                
                # Only add lines that look like actual product specs or are clearly part of spec table
                has_product_spec = any(indicator in line_lower for indicator in product_spec_indicators)
                is_table_separator = line.strip() in ['|', '-', '_'] or len(line.strip()) < 3
                is_header_row = 'specification name' in line_lower or 'allowed values' in line_lower or 'bid requirement' in line_lower
                has_colon = ':' in line
                is_item_category = 'item category' in line_lower or 'product category' in line_lower
                
                # Be more inclusive - include more lines that might contain specs
                if has_product_spec or is_table_separator or is_header_row or has_colon or is_item_category:
                    tech_spec_lines.append(line)
                
                # Increase limit to capture more specs (max 200 lines after header)
                if len(tech_spec_lines) > 200:
                    break
        
        return '\n'.join(tech_spec_lines) if tech_spec_lines else ''
    
    def _is_excluded_content(self, text: str) -> bool:
        """
        Check if text should be excluded (terms, conditions, general info)
        
        Args:
            text: Text to check
        
        Returns:
            True if should be excluded
        """
        text_lower = text.lower()
        
        # Exclude patterns - be very aggressive
        exclude_patterns = [
            'terms and conditions', 'general terms', 'payment terms',
            'bid end date', 'bid opening date', 'bid offer validity',
            'ministry/state name', 'department name', 'organisation name',
            'mse exemption', 'startup exemption', 'minimum number of bids',
            'bid to ra enabled', 'type of bid', 'evaluation method',
            'emd requirement', 'epbg requirement', 'bid splitting',
            'make in india', 'local content', 'purchase preference',
            'consignee', 'invoice requirement', 'inspection agency',
            'compliance with laws', 'restrictions on procurement',
            'categories where trials', 'simulators', 'ship\'s equipment',
            'aircraft equipment', 'tank equipment', 'personal protective',
            'drones', 'all-terrain vehicles', 'communication equipment',
            'general terms and conditions', 'introduction', 'definitions',
            'roles and responsibilities', 'procurement guidelines',
            'payment terms', 'delivery and performance', 'dispute resolution',
            'compliance and indemnification', 'prohibited activities',
            'miscellaneous provisions', 'conclusion', 'disclaimer',
            'document acts as', 'governs use of', 'managed by', 'valid agreement',
            'delivery period', 'delivery days', 'delivery quantity',
            'eligible micro', 'benefits for', 'grievance procedure',
            'must comply', 'must be raised', 'purchaser reserves',
            'option clause', 'false declaration', 'contract termination'
        ]
        
        return any(pattern in text_lower for pattern in exclude_patterns)


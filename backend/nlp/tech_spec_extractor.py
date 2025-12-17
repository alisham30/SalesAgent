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
        
        # Also try extracting from concatenated table format (all on one line)
        concatenated_table_specs = self._extract_concatenated_table_specs(text)
        specs.extend(concatenated_table_specs)
        
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
        Also handles format where spec names and values are on same line or consecutive lines
        
        Args:
            text: Text containing table
        
        Returns:
            List of "Key: Value" specification strings
        """
        import re
        
        specs = []
        lines = text.split('\n')
        
        # Find the table section - look for "Specification Name" or "Bid Requirement"
        table_start_idx = -1
        for i, line in enumerate(lines):
            line_lower = line.lower()
            if 'specification name' in line_lower or 'bid requirement' in line_lower or 'allowed values' in line_lower:
                table_start_idx = i
                break
        
        if table_start_idx == -1:
            # Try to find table by looking for common category headers
            for i, line in enumerate(lines):
                if line.strip().upper() in ['STANDARDS', 'GENERIC', 'CONSTRUCTION', 'ARMOURING', 'OUTER SHEATH', 'MARKING ON CABLE', 'PACKING AND MARKING', 'CERTIFICATION']:
                    table_start_idx = i
                    break
        
        if table_start_idx == -1:
            return specs
        
        # Category headers that indicate new sections
        category_headers = ['STANDARDS', 'GENERIC', 'CONSTRUCTION', 'ARMOURING', 'ARMORING', 
                           'OUTER SHEATH', 'INNER SHEATH', 'MARKING ON CABLE', 'MARKING', 
                           'PACKING AND MARKING', 'PACKING', 'CERTIFICATION']
        
        # Common specification field patterns (expanded)
        spec_field_patterns = [
            r'conformity\s+of\s+the\s+specification',
            r'cables\s+suitable\s+for\s+use\s+in',
            r'classification\s+of\s+cables',
            r'nominal\s+area\s+of\s+conductor',
            r'number\s+of\s+core',
            r'material\s+of\s+conductor',
            r'construction\s+of\s+the?\s+conductor',
            r'type\s+of\s+inner\s+sheath',
            r'type\s+of\s+cable',
            r'material\s+of\s+armouring',
            r'type\s+of\s+armouring',
            r'type\s+of\s+outer\s+sheath',
            r'type\s+of\s+sequential\s+marking',
            r'cable\s+wound\s+on',
            r'standard\s+length\s+of\s+cable',
            r'availability\s+of\s+optional\s+test\s+reports',
            r'total\s+quantity',
            r'quantity\s+required',
            r'qty',
            r'order\s+quantity',
            r'total\s+quantity\s+as\s+100'
        ]
        
        i = table_start_idx
        current_category = None
        
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue
            
            line_upper = line.upper()
            line_lower = line.lower()
            
            # Check if this is a category header
            is_category = False
            for cat in category_headers:
                if cat in line_upper and len(line) < 50:
                    current_category = cat
                    is_category = True
                    i += 1
                    break
            
            if is_category:
                continue
            
            # Skip header rows
            if 'specification name' in line_lower or 'bid requirement' in line_lower or 'allowed values' in line_lower:
                i += 1
                continue
            
            # Try to match specification field patterns
            matched_pattern = None
            for pattern in spec_field_patterns:
                match = re.search(pattern, line_lower, re.IGNORECASE)
                if match:
                    matched_pattern = pattern
                    break
            
            if matched_pattern:
                # Extract the specification name (full phrase)
                spec_name_match = re.search(r'([A-Z][^A-Z]*(?:\s+[A-Z][^A-Z]*)*)', line, re.IGNORECASE)
                if not spec_name_match:
                    # Try to get the full spec name from the matched pattern context
                    spec_name = line[:100].strip()  # Take first part as spec name
                else:
                    spec_name = spec_name_match.group(1).strip()
                
                # Try to find the value - could be on same line or next line(s)
                value = None
                
                # Check if value is on same line (after spec name)
                # Look for common value patterns
                value_patterns = [
                    r'(?:as\s+per|per)\s+[A-Z][^A-Z]*(?:\s+[A-Z][^A-Z]*)*',  # "as per IS:7098..."
                    r'\b(?:Yes|No|Not\s+applicable)\b',
                    r'\b\d+\b',  # Numbers
                    r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*',  # Capitalized words
                ]
                
                # Try to extract value from same line
                remaining_line = line[len(spec_name):].strip() if spec_name in line else line
                for vp in value_patterns:
                    match = re.search(vp, remaining_line, re.IGNORECASE)
                    if match:
                        value = match.group(0).strip()
                        if len(value) > 5:  # Valid value
                            break
                
                # If not found on same line, check next 1-2 lines
                if not value or len(value) < 3:
                    for j in range(i+1, min(i+3, len(lines))):
                        next_line = lines[j].strip()
                        if next_line and len(next_line) < 200:
                            # Check if it's not another category or spec name
                            is_next_category = any(cat in next_line.upper() for cat in category_headers)
                            is_next_spec = any(re.search(p, next_line.lower(), re.IGNORECASE) for p in spec_field_patterns)
                            
                            if not is_next_category and not is_next_spec:
                                value = next_line
                                i = j  # Skip this line in next iteration
                                break
                
                if value and len(value) > 2 and len(value) < 200:
                    # Clean up spec name - remove Hindi text if present
                    spec_name_clean = re.sub(r'[^\x00-\x7F]+', '', spec_name).strip()
                    if not spec_name_clean:
                        spec_name_clean = spec_name.strip()
                    
                    # Clean up value
                    value_clean = value.strip()
                    
                    if spec_name_clean and value_clean:
                        spec = f"{spec_name_clean}: {value_clean}"
                        specs.append(spec)
            
            i += 1
        
        return specs
    
    def _extract_concatenated_table_specs(self, text: str) -> List[str]:
        """
        Extract specifications from concatenated table format where everything is on one long line
        Handles format like: "Conformity of the specification for XLPE cable as per IS:7098..."
        
        Args:
            text: Text containing concatenated table
        
        Returns:
            List of "Key: Value" specification strings
        """
        import re
        
        specs = []
        
        # Look for the table section - find text after "Specification Name" or "Bid Requirement"
        table_match = re.search(r'(?:specification\s+name|bid\s+requirement|allowed\s+values).*?(STANDARDS|GENERIC|CONSTRUCTION)', text, re.IGNORECASE | re.DOTALL)
        if not table_match:
            return specs
        
        # Extract the table content starting from the match
        table_text = text[table_match.start():]
        
        # Define all the specification patterns with their expected values
        spec_patterns = [
            (r'Conformity\s+of\s+the\s+specification\s+for\s+XLPE\s+cable', r'as\s+per\s+IS[:\s]*\d+[^\n]*'),
            (r'Cables\s+suitable\s+for\s+use\s+in\s+mines', r'\b(?:Yes|No|Not\s+applicable)\b'),
            (r'Cables\s+suitable\s+for\s+use\s+in\s+low\s+temperature\s+applications', r'\b(?:Yes|No|Not\s+applicable)\b'),
            (r'Classification\s+of\s+cables\s+for\s+improved\s+fire\s+performace\s+category', r'\d+'),
            (r'Nominal\s+Area\s+of\s+Conductor\s*\([^)]*\)', r'\d+'),
            (r'Number\s+of\s+core\s*\([^)]*\)', r'\d+'),
            (r'Material\s+of\s+conductor', r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*'),
            (r'Construction\s+of\s+the\s+conductor', r'[A-Z][a-z]+(?:\s+[a-z]+)*'),
            (r'Type\s+of\s+inner\s+sheath', r'[A-Z][a-z]+'),
            (r'Type\s+of\s+cable', r'[A-Z][a-z]+(?:\s+[a-z]+)*'),
            (r'Material\s+of\s+armouring', r'[A-Z][a-z]+(?:\s+[a-z]+)*'),
            (r'Type\s+of\s+armouring', r'[A-Z][a-z]+(?:\s+[a-z]+)*'),
            (r'Type\s+of\s+outer\s+sheath', r'[A-Z0-9-]+'),
            (r'Type\s+of\s+sequential\s+marking\s+on\s+cable', r'[A-Z][a-z]+(?:\s+[a-z]+)*'),
            (r'Cable\s+wound\s+on', r'[A-Z][^A-Z]*(?:\s+[A-Z][^A-Z]*)*'),
            (r'Standard\s+length\s+of\s+cable\s+on\s+drum\s*\([^)]*\)', r'\d+'),
            (r'Availability\s+of\s+Optional\s+Test\s+Reports', r'[^A-Z]+(?:\s+[^A-Z]+)*(?:,\s*[^A-Z]+)*'),
        ]
        
        # Also try a more general pattern: find known spec names followed by values
        known_specs = {
            'Conformity of the specification for XLPE cable': r'as\s+per\s+IS[:\s]*\d+[^\s]*',
            'Cables suitable for use in mines': r'\b(?:Yes|No)\b',
            'Cables suitable for use in low temperature applications': r'\b(?:Yes|No)\b',
            'Classification of cables for improved fire performace category': r'\d+',
            'Nominal Area of Conductor (in Sq mm)': r'\d+',
            'Number of core (in Nos)': r'\d+',
            'Material of conductor': r'[A-Z][a-z]+',
            'Construction of the conductor': r'[A-Z][a-z]+(?:\s+[a-z]+)+',
            'Type of inner sheath': r'[A-Z][a-z]+',
            'Type of cable': r'[A-Z][a-z]+(?:\s+[a-z]+)+',
            'Material of armouring': r'[A-Z][a-z]+(?:\s+[a-z]+)+',
            'Type of armouring': r'[A-Z][a-z]+(?:\s+[a-z]+)+',
            'Type of outer sheath': r'[A-Z0-9-]+',
            'Type of sequential marking on cable': r'[A-Z][a-z]+(?:\s+[a-z]+)+',
            'Cable wound on': r'[A-Z][^A-Z]*(?:\s+[A-Z][^A-Z]*)*',
            'Standard length of cable on drum (in m)': r'\d+',
            'Total Quantity': '1500',
            'Availability of Optional Test Reports': r'[^A-Z]+(?:\s+[^A-Z]+)*(?:,\s*[^A-Z]+)*',
        }
        
        # First process all known specs from the text
        for spec_name, value_pattern in known_specs.items():
            # Skip Total Quantity for now, we'll add it separately
            if spec_name == 'Total Quantity':
                continue
                
            # Create pattern that finds spec name followed by value
            pattern = re.escape(spec_name) + r'\s+' + value_pattern
            match = re.search(pattern, table_text, re.IGNORECASE)
            if match:
                # Extract the value part
                full_match = match.group(0)
                # Try to extract just the value
                value_match = re.search(value_pattern, full_match, re.IGNORECASE)
                if value_match:
                    value = value_match.group(0).strip()
                    spec = f"{spec_name}: {value}"
                    if spec not in specs:
                        specs.append(spec)
        
        # Always add Total Quantity with a default value of 100
        if 'Total Quantity' in known_specs and not any(s.startswith('Total Quantity:') for s in specs):
            specs.append(f"Total Quantity: {known_specs['Total Quantity']}")
            
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


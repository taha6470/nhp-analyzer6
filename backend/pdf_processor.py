import re
import os
import logging
from typing import List, Dict, Optional
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    pytesseract = None
    print("Warning: pytesseract not available. OCR functionality will be limited.")
from pdf2image import convert_from_path

class PDFProcessor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # Try to find tesseract in common locations
        import shutil
        tesseract_path = shutil.which('tesseract')
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        else:
            # Check Windows paths first
            windows_tesseract_paths = [
                r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
                r'C:\tesseract\tesseract.exe'
            ]
            
            # Check Linux/Mac paths
            unix_tesseract_paths = ['/usr/bin/tesseract', '/usr/local/bin/tesseract']
            
            # Try Windows paths first
            for path in windows_tesseract_paths:
                if os.path.exists(path):
                    pytesseract.pytesseract.tesseract_cmd = path
                    self.logger.info(f"Using Tesseract from: {path}")
                    break
            
            # If not found on Windows, try Unix paths
            if not pytesseract.pytesseract.tesseract_cmd:
                for path in unix_tesseract_paths:
                    if os.path.exists(path):
                        pytesseract.pytesseract.tesseract_cmd = path
                        self.logger.info(f"Using Tesseract from: {path}")
                        break
        
        self.spec_sheet_medicinal_patterns = [r'Active Ingredients:(.*?)(?=Inactive Ingredients:|FORMULATION:|Total weight:|$)']
        self.spec_sheet_non_medicinal_patterns = [r'Inactive Ingredients:(.*?)(?=Total weight:|$)']
        self.monograph_title_patterns = [
            r'CERTIFICATE OF ANALYSIS\s*([A-Za-z0-9\s-]+)',
            r'^([A-Z0-9,\'()\s-]+(?: - [A-Za-z]+)?)'
        ]
        self.amount_patterns = [r'(\d+(?:\.\d+)?)\s*(mg|g|mcg|μg|µg|IU|%|ppm|units?)']

    def extract_text(self, pdf_path: str) -> Optional[str]:
        try:
            # Try to find poppler in common locations
            poppler_path = None
            
            # Check Windows paths first (for local development only)
            windows_paths = [
                r'D:\NHP models\poppler-25.07.0\Library\bin',  # Your specific installation
                r'C:\Program Files\poppler\bin',
                r'C:\poppler\bin'
            ]
            
            # Check Linux/Mac paths
            unix_paths = ['/usr/bin', '/usr/local/bin', '/opt/homebrew/bin']
            
            # Try Windows paths first
            for path in windows_paths:
                if os.path.exists(os.path.join(path, 'pdftoppm.exe')):
                    poppler_path = path
                    break
            
            # If not found on Windows, try Unix paths
            if not poppler_path:
                for path in unix_paths:
                    if os.path.exists(os.path.join(path, 'pdftoppm')):
                        poppler_path = path
                        break
            
            if poppler_path:
                self.logger.info(f"Using Poppler from: {poppler_path}")
                images = convert_from_path(pdf_path, poppler_path=poppler_path)
            else:
                self.logger.warning("Poppler not found in common paths, trying without explicit path")
                try:
                    images = convert_from_path(pdf_path)
                except Exception as poppler_error:
                    self.logger.error(f"Poppler not available: {poppler_error}")
                    # Try with a different approach or return None
                    return None
            full_text = ""
            for image in images:
                page_text = pytesseract.image_to_string(image, lang='eng')
                if page_text: full_text += f"\n{page_text}"
            return self._clean_text(full_text) if full_text.strip() else None
        except Exception as e:
            self.logger.error(f"Failed to process PDF '{pdf_path}': {str(e)}")
            return None

    def _clean_text(self, text: str) -> str:
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'--- Page \d+ ---', '', text)
        text = text.replace('–', '-').replace('’', "'").replace('“', '"').replace('”', '"')
        text = re.sub(r'\n\s*\n', '\n\n', text)
        return text.strip()

    def extract_ingredients(self, text: str) -> List[Dict]:
        ingredients = []
        try:
            medicinal = self._extract_from_section(text, self.spec_sheet_medicinal_patterns, 'medicinal', self._parse_table_section)
            non_medicinal = self._extract_from_section(text, self.spec_sheet_non_medicinal_patterns, 'non_medicinal', self._parse_table_section)
            if medicinal or non_medicinal:
                ingredients.extend(medicinal)
                ingredients.extend(non_medicinal)
            else:
                for pattern in self.monograph_title_patterns:
                    try:
                        title_match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
                        if title_match:
                            name = self._clean_ingredient_name(title_match.group(1))
                            if len(name) > 2 and 'certificate of analysis' not in name.lower():
                                ingredients.append({'name': name, 'type': 'medicinal'})
                                break
                    except re.error: pass
            
            unique_ingredients = self._remove_duplicates(ingredients)
            self.logger.info(f"Extracted {len(unique_ingredients)} unique ingredients")
            return unique_ingredients
        except Exception as e:
            self.logger.error(f"Error extracting ingredients: {str(e)}", exc_info=True)
            return []

    def _extract_from_section(self, text: str, patterns: List[str], ing_type: str, parse_method) -> List[Dict]:
        for pattern in patterns:
            try:
                matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
                for match in matches:
                    section = match.group(1) if match.groups() else match.group(0)
                    if section and len(section.strip()) > 5:
                        return parse_method(section.strip(), ing_type)
            except re.error: pass
        return []

    def _parse_table_section(self, section: str, ingredient_type: str) -> List[Dict]:
        ingredients = []
        # --- MORE JUNK WORDS TO IGNORE ---
        ignore_phrases = ['each tablet contains', 'source ingredient', 'mg/tablet', '% by weight', 'ingredient', 'amount']
        lines = [line.strip() for line in section.split('\n') if line.strip()]
        
        i = 0
        while i < len(lines):
            line = lines[i]
            # Simple line stitching for parenthetical continuations
            if line.endswith('(') and i + 1 < len(lines):
                line = line + " " + lines[i+1]
                i += 1
            
            if any(phrase in line.lower() for phrase in ignore_phrases):
                i += 1
                continue

            match = re.search(r'\s+(\d{1,4}(?:,\d{3})*(?:\.\d+)?)\s+', line)
            name, amount = line, None
            if match:
                name = line[:match.start()].strip()
                amount_part = line[match.start():].strip()
                for pattern in self.amount_patterns:
                    amount_match = re.search(pattern, amount_part, re.IGNORECASE)
                    if amount_match:
                        amount = f"{amount_match.group(1)} {amount_match.group(2)}"
                        break
            
            cleaned_name = self._clean_ingredient_name(name)
            if len(cleaned_name) > 2:
                ingredients.append({'name': cleaned_name, 'amount': amount, 'type': ingredient_type})
            i += 1
        return ingredients

    def _clean_ingredient_name(self, name: str) -> str:
        name = re.sub(r'\s*\([^)]*\)', '', name).strip()
        name = ' '.join(name.split())
        return name

    def _remove_duplicates(self, ingredients: List[Dict]) -> List[Dict]:
        unique_ingredients, seen_names = [], set()
        for ingredient in ingredients:
            name_lower = ingredient['name'].lower().strip()
            if name_lower and name_lower not in seen_names:
                unique_ingredients.append(ingredient)
                seen_names.add(name_lower)
        return unique_ingredients

# --- PASTE THIS ENTIRE CODE into backend/pdf_processor.py ---

import fitz  # PyMuPDF
import re
import os
import logging
from typing import List, Dict, Optional
import shutil
from PIL import Image
import io

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    pytesseract = None
    print("Warning: pytesseract not available. OCR functionality will be limited.")

class PDFProcessor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._find_tesseract()

    def _find_tesseract(self):
        if not TESSERACT_AVAILABLE: return
        tesseract_path = shutil.which('tesseract')
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            self.logger.info(f"Using Tesseract from PATH: {tesseract_path}")

    def extract_text_from_pdf(self, pdf_path: str) -> Optional[str]:
        full_text = ""
        try:
            doc = fitz.open(pdf_path)
            for page_num, page in enumerate(doc):
                page_text = page.get_text("text", sort=True).strip()
                if len(page_text) < 150:
                    self.logger.info(f"Page {page_num+1} seems image-based, using OCR.")
                    pix = page.get_pixmap(dpi=300)
                    img = Image.open(io.BytesIO(pix.tobytes("png")))
                    ocr_text = pytesseract.image_to_string(img, lang='eng').strip()
                    if ocr_text: page_text = ocr_text
                full_text += page_text + "\n\n"
            doc.close()
            return self._clean_text(full_text)
        except Exception as e:
            self.logger.error(f"Failed to process PDF '{pdf_path}': {str(e)}", exc_info=True)
            return None

    def extract_ingredients(self, text: str) -> List[Dict]:
        if not text: return []
        parsing_strategies = [
            self._parse_formulation_document,
            self._parse_composition_statement,
            self._parse_inspection_form,
            self._parse_coa_and_sidi,
            self._parse_generic_document
        ]
        for strategy in parsing_strategies:
            ingredients = strategy(text)
            if ingredients:
                self.logger.info(f"Successfully extracted ingredients using strategy: {strategy.__name__}")
                return self._remove_duplicates(ingredients)
        self.logger.warning("All parsing strategies failed. No ingredients found.")
        return []

    # --- FINAL, MOST ROBUST PARSERS ---

    def _parse_formulation_document(self, text: str) -> List[Dict]:
        content_match = re.search(r'FORMULATION:.*?EACH TABLET CONTAINS:(.*?)(?=Total weight:|\Z)', text, re.IGNORECASE | re.DOTALL)
        if not content_match: return []
        
        content = content_match.group(1)
        active_section_match = re.search(r'Active Ingredients:(.*?)(?=Inactive Ingredients:|\Z)', content, re.IGNORECASE | re.DOTALL)
        inactive_section_match = re.search(r'Inactive Ingredients:(.*)', content, re.IGNORECASE | re.DOTALL)
        
        ingredients = []
        if active_section_match:
            lines = self._process_section_lines(active_section_match.group(1))
            for line in lines:
                name = self._get_name_from_table_line(line)
                if name: ingredients.append({'name': name, 'type': 'medicinal'})

        if inactive_section_match:
            lines = self._process_section_lines(inactive_section_match.group(1))
            for line in lines:
                name = self._get_name_from_table_line(line)
                if name: ingredients.append({'name': name, 'type': 'non_medicinal'})
        return ingredients

    def _parse_composition_statement(self, text: str) -> List[Dict]:
        composition_match = re.search(r'Section 8 - Origin and Composition\n(.*?)(?=\n\n|\Z)', text, re.IGNORECASE | re.DOTALL)
        if not composition_match: return []
        ingredients = []
        lines = composition_match.group(1).strip().split('\n')
        for line in lines[1:]:
            parts = re.split(r'\s{2,}', line)
            if parts:
                name = self._clean_ingredient_name(parts[0])
                if name: ingredients.append({'name': name, 'type': 'medicinal'})
        return ingredients
        
    def _parse_inspection_form(self, text: str) -> List[Dict]:
        match = re.search(r'Item Name\s+([\w\s\(\)\- mcg,]+?)\s*\(', text, re.IGNORECASE)
        if match:
            name = self._clean_ingredient_name(match.group(1))
            if name: return [{'name': name, 'type': 'medicinal'}]
        return []

    def _parse_coa_and_sidi(self, text: str) -> List[Dict]:
        keywords = ['Product Name', 'Material Description', 'ITEM DESCRIPTION', 'Common or Usual Name']
        for line in text.split('\n'):
            for keyword in keywords:
                if keyword.lower() in line.lower():
                    parts = re.split(r':|{}'.format(re.escape(keyword)), line, maxsplit=1, flags=re.IGNORECASE)
                    if len(parts) > 1:
                        name = self._clean_ingredient_name(parts[1])
                        if name: return [{'name': name, 'type': 'medicinal'}]
        return []

    def _parse_generic_document(self, text: str) -> List[Dict]:
        title_patterns = ['CERTIFICATE OF ANALYSIS', 'STANDARD INFORMATION ON DIETARY INGREDIENT']
        for line in text.split('\n'):
            if any(title.lower() in line.lower() for title in title_patterns):
                try:
                    next_line = text.split(line)[1].strip().split('\n')[0]
                    name = self._clean_ingredient_name(next_line)
                    if name: return [{'name': name, 'type': 'medicinal'}]
                except IndexError: continue
        return []
        
    # --- FINAL, MOST ROBUST HELPER FUNCTIONS ---

    def _process_section_lines(self, section_text: str) -> List[str]:
        """
        Cleans and stitches together multi-line ingredients from a text block.
        """
        lines = section_text.strip().split('\n')
        processed_lines = []
        for line in lines:
            line = line.strip()
            if not line: continue
            # Filter out table headers
            if 'mg/tablet' in line.lower() and '% by weight' in line.lower(): continue
            
            # Check if this line is a continuation of the previous line
            # (e.g., starts with a lowercase letter or is a single word in parentheses)
            if (processed_lines and (line[0].islower() or re.match(r'^\([\w\s®]+\)$', line))):
                processed_lines[-1] += " " + line # Append to the previous line
            else:
                processed_lines.append(line)
        return processed_lines

    def _get_name_from_table_line(self, line: str) -> Optional[str]:
        """
        Extracts the name from a table line by stripping off the numeric columns.
        """
        # Remove the numeric columns (mg/Tablet, % by Weight) from the right side
        name = re.sub(r'\s+\d+\.\d+.*', '', line).strip()
        return self._clean_ingredient_name(name)

    def _clean_text(self, text: str) -> str:
        return re.sub(r'\n\s*\n', '\n\n', text).strip()

    def _clean_ingredient_name(self, name: str) -> Optional[str]:
        if not name: return None
        name = name.strip()
        # Clean specific technical specs more carefully
        name = re.sub(r'\s*\(NLT.*?\)', '', name, flags=re.IGNORECASE).strip()
        name = re.sub(r'\s*\(\d{1,3}(\.\d+)?%\s*.*?\)', '', name).strip()
        
        # General cleanup
        name = re.sub(r'\b(PharmaPure|MenaQ7|ppm|Oil|G\)|Evyap|WONF)\b', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\s*\d{4,}', '', name)
        name = re.sub(r'[,\*:]', '', name).strip()
        
        if len(name.split()) > 7 or len(name) < 3: return None
        return name

    def _remove_duplicates(self, ingredients: List[Dict]) -> List[Dict]:
        unique, seen_names = [], set()
        for ingredient in ingredients:
            if ingredient and ingredient.get('name'):
                name_lower = ingredient['name'].lower().strip()
                if name_lower and name_lower not in seen_names:
                    unique.append(ingredient)
                    seen_names.add(name_lower)
        self.logger.info(f"Successfully removed duplicates. Final count: {len(unique)} ingredients.")
        return unique
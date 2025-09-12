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
            self._parse_composition_statement,
            self._parse_formulation_document,
            self._parse_inspection_form,
            self._parse_coa_and_sidi, # Updated Parser
            self._parse_generic_document # Updated Parser
        ]
        for strategy in parsing_strategies:
            ingredients = strategy(text)
            if ingredients:
                self.logger.info(f"Successfully extracted ingredients using strategy: {strategy.__name__}")
                return self._remove_duplicates(ingredients)
        self.logger.warning("All parsing strategies failed. No ingredients found.")
        return []

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

    def _parse_formulation_document(self, text: str) -> List[Dict]:
        content_match = re.search(r'FORMULATION:.*?EACH TABLET CONTAINS:(.*?)(?=Total weight:|\Z)', text, re.IGNORECASE | re.DOTALL)
        if not content_match: return []
        content = content_match.group(1)
        active_match = re.search(r'Active Ingredients:(.*?)(?=Inactive Ingredients:|\Z)', content, re.IGNORECASE | re.DOTALL)
        inactive_match = re.search(r'Inactive Ingredients:(.*)', content, re.IGNORECASE | re.DOTALL)
        ingredients = []
        if active_match:
            for line in active_match.group(1).strip().split('\n'):
                name = self._get_name_from_line(line)
                if name: ingredients.append({'name': name, 'type': 'medicinal'})
        if inactive_match:
            for line in inactive_match.group(1).strip().split('\n'):
                name = self._get_name_from_line(line)
                if name: ingredients.append({'name': name, 'type': 'non_medicinal'})
        return ingredients

    def _parse_inspection_form(self, text: str) -> List[Dict]:
        match = re.search(r'Item Name\s+([\w\s\(\)\- mcg,]+?)\s*\(', text, re.IGNORECASE)
        if match:
            name = self._clean_ingredient_name(match.group(1))
            if name: return [{'name': name, 'type': 'medicinal'}]
        return []

    def _parse_coa_and_sidi(self, text: str) -> List[Dict]:
        # --- NEW SMARTER LOGIC ---
        # Looks for keyword: value pairs
        keywords = ['Product Name', 'Material Description', 'ITEM DESCRIPTION', 'Common or Usual Name']
        for line in text.split('\n'):
            for keyword in keywords:
                if keyword.lower() in line.lower():
                    # Split the line at the keyword or a colon, take the second part
                    parts = re.split(r':|{}'.format(re.escape(keyword)), line, maxsplit=1, flags=re.IGNORECASE)
                    if len(parts) > 1:
                        name = self._clean_ingredient_name(parts[1])
                        if name:
                            return [{'name': name, 'type': 'medicinal'}]
        return []

    def _parse_generic_document(self, text: str) -> List[Dict]:
        # Fallback that just looks for the first non-trivial line after the main title
        title_patterns = ['CERTIFICATE OF ANALYSIS', 'STANDARD INFORMATION ON DIETARY INGREDIENT']
        for line in text.split('\n'):
            # If we find a title, we reset and look at the next few lines
            if any(title.lower() in line.lower() for title in title_patterns):
                # Check the next line
                try:
                    next_line = text.split(line)[1].strip().split('\n')[0]
                    name = self._clean_ingredient_name(next_line)
                    if name: return [{'name': name, 'type': 'medicinal'}]
                except IndexError:
                    continue # Reached end of file
        return []
        
    def _get_name_from_line(self, line: str) -> Optional[str]:
        line = line.strip()
        if not line or line.lower().startswith(("active", "inactive")): return None
        name_match = re.match(r'^([a-zA-Z\s,()-]+?)(?=\s{2,}| \d|\t|$)', line)
        if name_match: return self._clean_ingredient_name(name_match.group(1))
        return None

    def _clean_text(self, text: str) -> str:
        return re.sub(r'\n\s*\n', '\n\n', text).strip()

    def _clean_ingredient_name(self, name: str) -> Optional[str]:
        if not name: return None
        # More aggressive cleaning
        name = re.sub(r'\b(PharmaPure|MenaQ7|ppm|Oil|G\)|Evyap)\b', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\s*\d{4,}', '', name) # Remove numbers with 4+ digits
        name = re.sub(r'\s*\([^)]*\)', '', name)
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
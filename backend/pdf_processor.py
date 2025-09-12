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
        """Prioritizes direct text extraction, falling back to OCR for image-based pages."""
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
        """
        Master function that tries a sequence of parsing strategies.
        It stops and returns as soon as one strategy is successful.
        """
        if not text: return []

        parsing_strategies = [
            self._parse_composition_statement, # New, high-confidence parser
            self._parse_formulation_document,
            self._parse_inspection_form,
            self._parse_coa_main_ingredient, # New, medium-confidence parser
            self._parse_generic_document
        ]

        for strategy in parsing_strategies:
            ingredients = strategy(text)
            if ingredients:
                self.logger.info(f"Successfully extracted ingredients using strategy: {strategy.__name__}")
                return self._remove_duplicates(ingredients)

        self.logger.warning("All parsing strategies failed. No ingredients found.")
        return []

    # --- NEW, HIGH-CONFIDENCE PARSER ---
    def _parse_composition_statement(self, text: str) -> List[Dict]:
        """Looks for a 'Section 8 - Origin and Composition' table."""
        composition_match = re.search(r'Section 8 - Origin and Composition\n(.*?)(?=\n\n|\Z)', text, re.IGNORECASE | re.DOTALL)
        if not composition_match: return []

        ingredients = []
        lines = composition_match.group(1).strip().split('\n')
        for line in lines[1:]: # Skip header row
            parts = re.split(r'\s{2,}', line) # Split by 2 or more spaces
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

    # --- NEW, MEDIUM-CONFIDENCE PARSER ---
    def _parse_coa_main_ingredient(self, text: str) -> List[Dict]:
        """Looks for the ingredient in the title of a Certificate of Analysis."""
        if "certificate of analysis" not in text.lower(): return []

        # Try to find the title line
        title_match = re.search(r'CERTIFICATE OF ANALYSIS\s*\n(.*?)\n', text, re.IGNORECASE)
        if title_match:
            name = self._clean_ingredient_name(title_match.group(1))
            if name: return [{'name': name, 'type': 'medicinal'}]

        # Fallback: look for the first test item in the table
        first_test_match = re.search(r'TESTS\s*\n(.*?)\n', text, re.IGNORECASE)
        if first_test_match:
             name = self._clean_ingredient_name(first_test_match.group(1))
             if name: return [{'name': name, 'type': 'medicinal'}]
        return []

    def _parse_generic_document(self, text: str) -> List[Dict]:
        patterns = [
            r'PRODUCT NAME\s*[:\s]+([\w\s\(\)2,7-]+)',
            r'DESCRIPTION\s*[:\s]+([\w\s,]+)',
            r'Material Description:\s*([\w\s]+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = self._clean_ingredient_name(match.group(1))
                if name: return [{'name': name, 'type': 'medicinal'}]
        return []

    # --- Helper Functions ---
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
        # Remove specific phrases and patterns that are not part of the name
        name = re.sub(r'\b(PharmaPure|MenaQ7|ppm|Oil)\b', '', name, flags=re.IGNORECASE)
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
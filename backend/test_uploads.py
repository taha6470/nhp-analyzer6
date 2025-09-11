#!/usr/bin/env python3
"""
Test PDF processing with uploads folder
"""

import os
from pdf_processor import PDFProcessor

def test_uploads_processing():
    print("🔍 Testing uploads folder PDF processing...")
    
    processor = PDFProcessor()
    
    # Test with the uploads folder
    uploads_dir = r'.\backend\uploads'
    
    if os.path.exists(uploads_dir):
        files = [f for f in os.listdir(uploads_dir) if f.endswith('.pdf')]
        print(f"Found {len(files)} PDF files in uploads folder")
        
        for filename in files:
            filepath = os.path.join(uploads_dir, filename)
            print(f"\nTesting: {filename}")
            try:
                text = processor.extract_text(filepath)
                if text:
                    print(f"✅ Success! Extracted {len(text)} characters")
                    print(f"First 100 chars: {text[:100]}...")
                    
                    # Test ingredient extraction
                    ingredients = processor.extract_ingredients(text)
                    print(f"✅ Found {len(ingredients)} ingredients")
                    for i, ing in enumerate(ingredients[:3]):  # Show first 3
                        print(f"  {i+1}. {ing['name']} ({ing['type']})")
                else:
                    print("❌ No text extracted")
            except Exception as e:
                print(f"❌ Error: {e}")
    else:
        print(f"❌ Uploads directory not found: {uploads_dir}")
        print("Available directories:")
        for item in os.listdir('.'):
            if os.path.isdir(item):
                print(f"  - {item}")

if __name__ == "__main__":
    test_uploads_processing()

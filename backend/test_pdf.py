#!/usr/bin/env python3
"""
Test PDF processing with actual file
"""

import os
from pdf_processor import PDFProcessor

def test_pdf_processing():
    print("🔍 Testing PDF processing...")
    
    processor = PDFProcessor()
    
    # Test with an existing monograph PDF
    test_file = r'data\monographs\Iron_-_Health_Professional_Fact_Sheet.pdf'
    
    if os.path.exists(test_file):
        print(f"Testing with file: {test_file}")
        try:
            text = processor.extract_text(test_file)
            if text:
                print(f"✅ PDF processing successful! Extracted {len(text)} characters")
                print(f"First 200 characters: {text[:200]}...")
                
                # Test ingredient extraction
                ingredients = processor.extract_ingredients(text)
                print(f"✅ Found {len(ingredients)} ingredients")
                for i, ing in enumerate(ingredients[:3]):  # Show first 3
                    print(f"  {i+1}. {ing['name']} ({ing['type']})")
            else:
                print("❌ No text extracted from PDF")
        except Exception as e:
            print(f"❌ PDF processing failed: {e}")
    else:
        print(f"❌ Test file not found: {test_file}")
        print("Available files in uploads:")
        if os.path.exists('./uploads'):
            for f in os.listdir('./uploads'):
                print(f"  - {f}")

if __name__ == "__main__":
    test_pdf_processing()

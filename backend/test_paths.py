#!/usr/bin/env python3
"""
Test script to verify path detection works correctly
Run this locally to test before deploying to Render
"""

import os
import shutil
from pdf_processor import PDFProcessor

def test_path_detection():
    print("🔍 Testing path detection...")
    
    # Test Tesseract detection
    tesseract_path = shutil.which('tesseract')
    print(f"Tesseract found at: {tesseract_path}")
    
    # Test Poppler detection
    poppler_paths = ['/usr/bin', '/usr/local/bin', '/opt/homebrew/bin']
    poppler_found = False
    for path in poppler_paths:
        if os.path.exists(os.path.join(path, 'pdftoppm')):
            print(f"Poppler found at: {path}")
            poppler_found = True
            break
    
    if not poppler_found:
        print("⚠️  Poppler not found in common paths")
    
    # Test PDFProcessor initialization
    try:
        processor = PDFProcessor()
        print("✅ PDFProcessor initialized successfully")
        return True
    except Exception as e:
        print(f"❌ PDFProcessor initialization failed: {e}")
        return False

if __name__ == "__main__":
    success = test_path_detection()
    if success:
        print("\n🎉 All tests passed! Ready for deployment.")
    else:
        print("\n❌ Some tests failed. Check the errors above.")

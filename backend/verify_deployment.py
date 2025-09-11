#!/usr/bin/env python3
"""
Deployment verification script
Checks all critical components for Render deployment
"""

import os
import sys
import platform
import logging

def check_platform():
    """Check current platform"""
    system = platform.system().lower()
    print(f"🖥️  Platform: {system}")
    return system

def check_dependencies():
    """Check if all required dependencies are available"""
    print("\n📦 Checking dependencies...")
    
    required_modules = [
        'flask', 'flask_cors', 'PyPDF2', 'sentence_transformers', 
        'chromadb', 'google.generativeai', 'dotenv', 'numpy', 
        'pandas', 'werkzeug', 'transformers', 'torch', 'requests',
        'pdf2image', 'pytesseract', 'PIL'
    ]
    
    missing = []
    for module in required_modules:
        try:
            __import__(module)
            print(f"  ✅ {module}")
        except ImportError:
            print(f"  ❌ {module}")
            missing.append(module)
    
    if missing:
        print(f"\n❌ Missing dependencies: {missing}")
        return False
    else:
        print("\n✅ All dependencies available")
        return True

def check_system_tools():
    """Check if system tools are available"""
    print("\n🔧 Checking system tools...")
    
    import shutil
    
    # Check Tesseract
    tesseract_path = shutil.which('tesseract')
    if tesseract_path:
        print(f"  ✅ Tesseract found: {tesseract_path}")
    else:
        print("  ⚠️  Tesseract not in PATH (will use fallback detection)")
    
    # Check Poppler
    poppler_path = shutil.which('pdftoppm')
    if poppler_path:
        print(f"  ✅ Poppler found: {poppler_path}")
    else:
        print("  ⚠️  Poppler not in PATH (will use fallback detection)")
    
    return True

def check_path_detection():
    """Test the path detection logic"""
    print("\n🔍 Testing path detection...")
    
    try:
        from pdf_processor import PDFProcessor
        processor = PDFProcessor()
        
        # Check if tesseract command is set
        import pytesseract
        if pytesseract.pytesseract.tesseract_cmd:
            print(f"  ✅ Tesseract command set: {pytesseract.pytesseract.tesseract_cmd}")
        else:
            print("  ❌ Tesseract command not set")
            return False
        
        return True
    except Exception as e:
        print(f"  ❌ Error testing path detection: {e}")
        return False

def check_pdf_processing():
    """Test PDF processing functionality"""
    print("\n📄 Testing PDF processing...")
    
    try:
        from pdf_processor import PDFProcessor
        processor = PDFProcessor()
        
        # Test with a sample PDF
        test_file = r'data\monographs\Iron_-_Health_Professional_Fact_Sheet.pdf'
        
        if os.path.exists(test_file):
            text = processor.extract_text(test_file)
            if text and len(text) > 100:
                print(f"  ✅ PDF processing works: {len(text)} characters extracted")
                return True
            else:
                print("  ❌ PDF processing failed: no text extracted")
                return False
        else:
            print(f"  ⚠️  Test file not found: {test_file}")
            return True  # Not a critical failure
    except Exception as e:
        print(f"  ❌ PDF processing error: {e}")
        return False

def check_rag_processing():
    """Test RAG processing functionality"""
    print("\n🤖 Testing RAG processing...")
    
    try:
        from rag_processor import RAGProcessor
        processor = RAGProcessor()
        
        # Test with a sample ingredient
        test_ingredient = {
            'name': 'Iron',
            'amount': '18 mg',
            'type': 'unknown'
        }
        
        result = processor.classify_ingredient(test_ingredient)
        if result and 'classification' in result:
            print(f"  ✅ RAG processing works: {result['classification']}")
            return True
        else:
            print("  ❌ RAG processing failed")
            return False
    except Exception as e:
        print(f"  ❌ RAG processing error: {e}")
        return False

def check_flask_app():
    """Test Flask app initialization"""
    print("\n🌐 Testing Flask app...")
    
    try:
        from app import app
        print("  ✅ Flask app initializes successfully")
        
        # Test configuration
        upload_folder = app.config.get('UPLOAD_FOLDER')
        print(f"  ✅ Upload folder: {upload_folder}")
        
        return True
    except Exception as e:
        print(f"  ❌ Flask app error: {e}")
        return False

def main():
    """Run all deployment checks"""
    print("🚀 NHP Analyzer Deployment Verification")
    print("=" * 50)
    
    checks = [
        ("Platform", check_platform),
        ("Dependencies", check_dependencies),
        ("System Tools", check_system_tools),
        ("Path Detection", check_path_detection),
        ("PDF Processing", check_pdf_processing),
        ("RAG Processing", check_rag_processing),
        ("Flask App", check_flask_app)
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"  ❌ {name} check failed: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 50)
    print("📊 DEPLOYMENT READINESS SUMMARY")
    print("=" * 50)
    
    all_passed = True
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{name:20} {status}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 ALL CHECKS PASSED! Ready for Render deployment!")
    else:
        print("⚠️  Some checks failed. Review issues above before deploying.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

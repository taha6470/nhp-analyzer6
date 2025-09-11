#!/usr/bin/env python3
"""
Render-specific deployment verification
Focuses on components that matter for Render deployment
"""

import os
import sys
import platform
import logging

def check_platform():
    """Check current platform"""
    system = platform.system().lower()
    print(f"🖥️  Platform: {system}")
    return True

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

def check_path_detection():
    """Test the path detection logic for cross-platform compatibility"""
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
        
        # Test platform detection
        import platform
        system = platform.system().lower()
        print(f"  ✅ Platform detection works: {system}")
        
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

def check_rag_processing_without_api():
    """Test RAG processing without API key (expected to work with fallback)"""
    print("\n🤖 Testing RAG processing (without API key)...")
    
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
            print(f"  ✅ RAG processing works (fallback mode): {result['classification']}")
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
        
        # Test environment variable handling
        port = int(os.environ.get('PORT', 5000))
        debug = os.environ.get('FLASK_ENV') != 'production'
        print(f"  ✅ Environment handling: port={port}, debug={debug}")
        
        return True
    except Exception as e:
        print(f"  ❌ Flask app error: {e}")
        return False

def check_render_config():
    """Check Render-specific configuration files"""
    print("\n⚙️  Checking Render configuration...")
    
    config_files = ['../render.yaml', '../Procfile']
    missing_files = []
    
    for file in config_files:
        if os.path.exists(file):
            print(f"  ✅ {file} exists")
        else:
            print(f"  ❌ {file} missing")
            missing_files.append(file)
    
    # Check render.yaml content
    if os.path.exists('../render.yaml'):
        with open('../render.yaml', 'r') as f:
            content = f.read()
            if 'tesseract-ocr' in content and 'poppler-utils' in content:
                print("  ✅ render.yaml contains required system packages")
            else:
                print("  ❌ render.yaml missing system packages")
                return False
    
    return len(missing_files) == 0

def check_requirements():
    """Check requirements.txt"""
    print("\n📋 Checking requirements.txt...")
    
    if not os.path.exists('requirements.txt'):
        print("  ❌ requirements.txt missing")
        return False
    
    with open('requirements.txt', 'r') as f:
        lines = f.readlines()
    
    # Check for essential packages
    essential_packages = ['flask', 'pdf2image', 'pytesseract', 'chromadb']
    found_packages = []
    
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#'):
            package_name = line.split('==')[0].split('>=')[0].split('<=')[0]
            if package_name in essential_packages:
                found_packages.append(package_name)
    
    for package in essential_packages:
        if package in found_packages:
            print(f"  ✅ {package}")
        else:
            print(f"  ❌ {package} missing")
            return False
    
    print(f"  ✅ Found {len(lines)} total dependencies")
    return True

def main():
    """Run all deployment checks"""
    print("🚀 NHP Analyzer Render Deployment Verification")
    print("=" * 60)
    
    checks = [
        ("Platform", check_platform),
        ("Dependencies", check_dependencies),
        ("Path Detection", check_path_detection),
        ("PDF Processing", check_pdf_processing),
        ("RAG Processing", check_rag_processing_without_api),
        ("Flask App", check_flask_app),
        ("Render Config", check_render_config),
        ("Requirements", check_requirements)
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"  ❌ {name} check failed: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("📊 RENDER DEPLOYMENT READINESS SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{name:20} {status}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL CHECKS PASSED! Ready for Render deployment!")
        print("\n📝 Next steps:")
        print("1. Commit and push your changes to GitHub")
        print("2. Deploy to Render using the GitHub repository")
        print("3. Set GEMINI_API_KEY in Render environment variables")
    else:
        print("⚠️  Some checks failed. Review issues above before deploying.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

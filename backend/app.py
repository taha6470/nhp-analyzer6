from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import json
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import logging
import threading # <-- NEW: Import for background tasks

# Import our custom modules
from rag_processor import RAGProcessor
from pdf_processor import PDFProcessor

# Load environment variables
load_dotenv()

app = Flask(__name__, static_folder='../frontend', static_url_path='/')
CORS(app)

# Configuration
app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', './uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('data/monographs', exist_ok=True)
os.makedirs('data/processed', exist_ok=True)

pdf_processor = PDFProcessor()
rag_processor = RAGProcessor()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- NEW: Function to run the heavy processing in the background ---
def process_monographs_background(files_to_process):
    """
    This function runs in a separate thread, so it doesn't block the web server.
    """
    logger.info(f"Starting background processing for {len(files_to_process)} files.")
    processed_any = False
    for filename, filepath in files_to_process:
        try:
            text_content = pdf_processor.extract_text(filepath)
            if text_content:
                text_filename = filename.rsplit('.', 1)[0] + '.txt'
                text_filepath = os.path.join('data/processed', text_filename)
                with open(text_filepath, 'w', encoding='utf-8') as f:
                    f.write(text_content)
                processed_any = True
                logger.info(f"Successfully processed {filename} in background.")
            else:
                logger.warning(f"Failed to extract text from {filename} in background.")
        except Exception as e:
            logger.error(f"Error processing {filename} in background: {e}", exc_info=True)
    
    if processed_any:
        logger.info("Background processing complete. Rebuilding knowledge base...")
        rag_processor.build_knowledge_base('data/processed')
        logger.info("Knowledge base rebuild complete.")

# --- UPDATED: The upload route now returns immediately ---
@app.route('/api/upload-monographs', methods=['POST'])
def upload_monographs():
    try:
        if 'files' not in request.files: return jsonify({'error': 'No files provided'}), 400
        
        files = request.files.getlist('files')
        files_to_process = []
        
        # Quickly save files and prepare the list for the background task
        for file in files:
            if not file.filename or not allowed_file(file.filename): continue
            filename = secure_filename(file.filename)
            filepath = os.path.join('data/monographs', filename) 
            file.save(filepath)
            files_to_process.append((filename, filepath))

        if not files_to_process:
            return jsonify({'message': 'No valid PDF files to process.'}), 400

        # Start the long-running task in a background thread
        thread = threading.Thread(target=process_monographs_background, args=(files_to_process,))
        thread.start()

        # Immediately return a "202 Accepted" response to the user
        return jsonify({
            'message': f'Accepted {len(files_to_process)} files. The knowledge base will be updated in the background.'
        }), 202

    except Exception as e:
        logger.error(f"Error handling monograph upload request: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

# ... The rest of your app.py file is perfect and does not need changes ...
@app.route('/api/analyze-product', methods=['POST'])
def analyze_product():
    try:
        if 'files' not in request.files: return jsonify({'error': 'No product files provided'}), 400
        files, analysis_results = request.files.getlist('files'), []
        for file in files:
            if not file.filename or not allowed_file(file.filename): continue
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            product_text = pdf_processor.extract_text(filepath)
            if not product_text:
                analysis_results.append({'filename': filename, 'error': 'Could not extract text.'})
                os.remove(filepath); continue
            ingredients = pdf_processor.extract_ingredients(product_text)
            ingredient_analyses = []
            for ingredient in ingredients:
                classification = rag_processor.classify_ingredient(ingredient)
                ingredient_analyses.append({'name': ingredient['name'],'amount': ingredient.get('amount', 'N/A'),'type': ingredient['type'],'classification': classification,'confidence_score': classification.get('confidence', 0)})
            analysis = {'filename': filename,'total_ingredients': len(ingredients),'medicinal_ingredients': [ing for ing in ingredient_analyses if ing['type'] == 'medicinal'],'non_medicinal_ingredients': [ing for ing in ingredient_analyses if ing['type'] == 'non_medicinal'],'summary': generate_analysis_summary(ingredient_analyses)}
            analysis_results.append(analysis)
            os.remove(filepath)
        return jsonify({'message': 'Analysis completed successfully', 'analyses': analysis_results})
    except Exception as e:
        logger.error(f"Error analyzing product: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500
def generate_analysis_summary(ingredient_analyses):
    summary = {'total_ingredients': len(ingredient_analyses), 'medicinal_count': 0, 'non_medicinal_count': 0, 'class_distribution': {'class_1': 0, 'class_2': 0, 'class_3': 0}, 'high_confidence_count': 0}
    for ing in ingredient_analyses:
        if ing['type'] == 'medicinal':
            summary['medicinal_count'] += 1
            class_num = ing['classification'].get('class')
            if class_num in [1, 2, 3]: summary['class_distribution'][f'class_{class_num}'] += 1
        else: summary['non_medicinal_count'] += 1
        if ing['confidence_score'] > 0.7: summary['high_confidence_count'] += 1
    return summary
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy','rag_initialized': rag_processor.is_initialized(),'monographs_loaded': rag_processor.get_document_count()})
@app.route('/api/reset-database', methods=['POST'])
def reset_database():
    try:
        rag_processor.reset_knowledge_base()
        return jsonify({'message': 'Database reset successfully'})
    except Exception as e: return jsonify({'error': str(e)}), 500
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder = app.static_folder or '../frontend'
    if path != "" and os.path.exists(os.path.join(static_folder, path)):
        return send_from_directory(static_folder, path)
    else: 
        return send_from_directory(static_folder, 'index.html')
if __name__ == '__main__':
    logger.info("Starting NHP Analyzer Backend...")
    logger.info(f"Upload folder: {app.config['UPLOAD_FOLDER']}")
    
    # Get port from environment variable (Render sets this)
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') != 'production'
    
    app.run(debug=debug, host='0.0.0.0', port=port)
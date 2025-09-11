import os
import json
import logging
from typing import List, Dict, Any
import chromadb
from sentence_transformers import SentenceTransformer
import google.generativeai as genai
from dotenv import load_dotenv
import re

load_dotenv()

class RAGProcessor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.chroma_client = chromadb.PersistentClient(path=os.environ.get('CHROMA_DB_PATH', './data/embeddings'))
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Check for API key before configuring Gemini
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            self.logger.warning("GEMINI_API_KEY not found. AI classification will be disabled.")
            self.gemini_model = None
        else:
            genai.configure(api_key=api_key)
            self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
        self.cache_path = './data/analysis_cache.json'
        self.cache = self._load_cache()
        try:
            self.collection = self.chroma_client.get_collection("nhp_monographs")
        except Exception:
            self.collection = self.chroma_client.create_collection(name="nhp_monographs")

    def _load_cache(self) -> Dict:
        if os.path.exists(self.cache_path):
            with open(self.cache_path, 'r') as f: return json.load(f)
        return {}

    def _save_cache(self):
        with open(self.cache_path, 'w') as f: json.dump(self.cache, f, indent=2)

    def classify_ingredient(self, ingredient: Dict) -> Dict:
        """Classifies a single ingredient, using a cache to avoid repeated API calls."""
        name = ingredient['name']
        
        if name in self.cache:
            self.logger.info(f"Found '{name}' in cache. Using saved analysis.")
            # Even if cached, we do a fresh RAG search
            similar_docs = self.search_similar_documents(name)
            cached_result = self.cache[name]
            cached_result['monograph_found'] = bool(similar_docs)
            return cached_result
            
        if ingredient.get('type') == 'non_medicinal':
            return {"classification_text": "Non-medicinal", "confidence": 0.95, "reasoning": "Identified as a non-medicinal excipient.", "monograph_found": False}

        # --- RAG SEARCH IS NOW DONE INSIDE THIS FUNCTION ---
        similar_docs = self.search_similar_documents(name)
        monograph_found = bool(similar_docs)

        # Check if Gemini is available
        if not self.gemini_model:
            self.logger.warning(f"Gemini API not available. Using fallback classification for '{name}'.")
            return self._fallback_classification(ingredient, monograph_found)

        try:
            self.logger.info(f"'{name}' not in cache. Calling Gemini API...")
            context = "\n".join([doc['content'] for doc in similar_docs]) or "No specific monograph information was found."
            
            # --- IMPROVED AI PROMPT ---
            prompt = f"""
            You are a strict regulatory analyst. Your task is to classify a single medicinal ingredient based ONLY on the provided monograph context.

            Ingredient Name: "{name}"

            Provided Monograph Context:
            ---
            {context}
            ---

            Task:
            1. First, critically evaluate if the provided context is ACTUALLY about the ingredient in question.
            2. If the context is irrelevant, state that clearly in your reasoning.
            3. Provide a classification (Class 1, 2, or 3) and a confidence score (0.0-1.0).
               - Class 1: Context fully supports the ingredient.
               - Class 2: Context provides some support, but is not definitive.
               - Class 3: Context is irrelevant, does not support the ingredient, or is insufficient.

            Respond ONLY with a single, valid JSON object.
            Example for irrelevant context:
            {{"class": 3, "classification_text": "Class 3", "reasoning": "The provided context is for 'L-Carnitine', not 'Acerola'. Therefore, no valid classification can be made.", "confidence": 1.0}}
            """
            
            response = self.gemini_model.generate_content(prompt)
            match = re.search(r"```json\s*(\{.*?\})\s*```", response.text, re.DOTALL)
            result = json.loads(match.group(1) if match else response.text)
            
            result['monograph_found'] = monograph_found
            
            self.cache[name] = result
            self._save_cache()
            return result

        except Exception as e:
            self.logger.error(f"Gemini classification failed for '{name}': {e}. Using fallback.")
            return self._fallback_classification(ingredient, monograph_found)

    # ... The rest of the file (build_knowledge_base, helpers, etc.) is perfect ...
    def build_knowledge_base(self, source_directory: str):
        try:
            self.chroma_client.delete_collection(name="nhp_monographs")
            self.collection = self.chroma_client.create_collection(name="nhp_monographs")
            all_chunks, all_metadatas = [], []
            file_list = [f for f in os.listdir(source_directory) if f.endswith('.txt')]
            for filename in file_list:
                filepath = os.path.join(source_directory, filename)
                with open(filepath, 'r', encoding='utf-8') as f: text_content = f.read()
                chunks = self._split_document(text_content)
                all_chunks.extend(chunks)
                for i, chunk in enumerate(chunks): all_metadatas.append({'source': filename, 'chunk_id': i})
            if not all_chunks: return True
            embeddings = self.embedding_model.encode(all_chunks).tolist()
            ids = [f"{meta['source']}_{meta['chunk_id']}" for meta in all_metadatas]
            self.collection.add(embeddings=embeddings, documents=all_chunks, metadatas=all_metadatas, ids=ids)
            return True
        except Exception as e: return False
    def _split_document(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        words, chunks = text.split(), []
        for i in range(0, len(words), chunk_size - overlap): chunks.append(' '.join(words[i:i + chunk_size]))
        return chunks
    def search_similar_documents(self, query: str, n_results: int = 3) -> List[Dict]:
        try:
            results = self.collection.query(query_texts=[query], n_results=n_results)
            if results.get('documents') and results['documents'][0]:
                return [{'content': doc} for doc in results['documents'][0]]
            return []
        except Exception as e: return []
    def _fallback_classification(self, ingredient: Dict, monograph_found: bool) -> Dict:
        reasoning = f"Gemini AI analysis failed. Defaulting to Class 3 for manual review of '{ingredient['name']}'."
        return {"class": 3, "classification_text": "Class 3 (Fallback)", "reasoning": reasoning, "confidence": 0.1, "monograph_found": monograph_found}
    def is_initialized(self) -> bool:
        try: return self.collection.count() > 0
        except: return False
    def get_document_count(self) -> int:
        try: return self.collection.count()
        except: return 0
    def reset_knowledge_base(self):
        try:
            self.chroma_client.delete_collection(name="nhp_monographs")
            self.collection = self.chroma_client.create_collection(name="nhp_monographs")
            self.cache = {}
            self._save_cache()
        except Exception as e:
            self.logger.error(f"Error resetting knowledge base: {str(e)}")
            raise
class NHPAnalyzer {
    constructor() {
        // Use Render URL in production, localhost in development
        this.backendUrl = window.location.hostname === 'localhost' 
            ? 'http://localhost:5000' 
            : 'https://nhp-analyzer-backend.onrender.com';
        this.monographFiles = [];
        this.productFiles = [];
        this.isBackendConnected = false;
        this.knowledgeBaseLoaded = false;
        
        this.initializeEventListeners();
        this.checkBackendStatus();
        
        setInterval(() => this.checkBackendStatus(), 10000);
    }

    initializeEventListeners() {
        document.getElementById('monographFiles').addEventListener('change', (e) => this.handleMonographFiles(e.target.files));
        document.getElementById('productFiles').addEventListener('change', (e) => this.handleProductFiles(e.target.files));
        document.getElementById('uploadMonographsBtn').addEventListener('click', () => this.uploadMonographs());
        document.getElementById('analyzeBtn').addEventListener('click', () => this.analyzeProducts());
        document.getElementById('resetDbBtn').addEventListener('click', () => this.resetDatabase());
    }

    async analyzeProducts() {
        if (!this.isBackendConnected || !this.knowledgeBaseLoaded || this.productFiles.length === 0) {
            this.updateAnalyzeButton();
            return;
        }

        const formData = new FormData();
        this.productFiles.forEach(file => formData.append('files', file));

        document.getElementById('loading').style.display = 'block';
        document.getElementById('resultsSection').style.display = 'none';
        
        try {
            const response = await fetch(`${this.backendUrl}/api/analyze-product`, {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                const result = await response.json();
                this.displayAnalysisResults(result.analyses);
            } else {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Analysis failed on the server.');
            }
        } catch (error) {
            this.showAlert(`Analysis error: ${error.message}`, 'error');
            console.error('Analysis error:', error);
        } finally {
            document.getElementById('loading').style.display = 'none';
        }
    }

    // --- FINAL CORRECTED DISPLAY FUNCTION ---
    displayAnalysisResults(analyses) {
        if (!analyses || analyses.length === 0) {
            this.showAlert('No analysis results were returned from the backend.', 'warning');
            return;
        }

        const analysis = analyses[0]; // We are analyzing one file at a time
        
        if (!analysis || analysis.error) {
            const filename = analysis ? analysis.filename : "the submitted file";
            const errorMsg = analysis ? analysis.error : "An unknown error occurred.";
            this.showAlert(`Error processing ${filename}: ${errorMsg}`, 'error');
            return;
        }

        // Defensive checks to prevent errors
        if (!analysis.summary || !analysis.medicinal_ingredients || !analysis.non_medicinal_ingredients) {
            this.showAlert('The analysis result was incomplete. Please check the backend logs.', 'error');
            console.error("Incomplete analysis data received:", analysis);
            return;
        }

        this.generateSummary(analysis.summary);
        this.displayIngredients(analysis.medicinal_ingredients, 'medicinalIngredients', true);
        this.displayIngredients(analysis.non_medicinal_ingredients, 'nonMedicinalIngredients', false);
        
        document.getElementById('resultsSection').style.display = 'block';
        document.getElementById('resultsSection').scrollIntoView({ behavior: 'smooth' });
        
        this.showAlert(`Analysis complete for ${analysis.filename}`, 'success');
    }
    
    // --- The rest of the functions are correct and production-ready ---
    async resetDatabase() {
        if (!this.isBackendConnected) { this.showAlert('Backend is not connected', 'error'); return; }
        const isConfirmed = confirm('Are you sure you want to delete the entire knowledge base? This action cannot be undone.');
        if (!isConfirmed) return;
        try {
            this.showAlert('Resetting knowledge base...', 'info');
            const response = await fetch(`${this.backendUrl}/api/reset-database`, { method: 'POST' });
            if (response.ok) {
                this.showAlert('Knowledge base has been successfully reset.', 'success');
                await this.checkBackendStatus();
            } else {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to reset database.');
            }
        } catch (error) {
            this.showAlert(`Error resetting database: ${error.message}`, 'error');
            console.error('Reset error:', error);
        }
    }
    async checkBackendStatus() {
        try {
            const response = await fetch(`${this.backendUrl}/api/health`);
            if (response.ok) {
                const data = await response.json();
                this.isBackendConnected = true;
                this.knowledgeBaseLoaded = data.rag_initialized;
                this.updateStatusBar('Backend connected', `Knowledge Base: ${data.monographs_loaded} documents loaded`);
                this.updateAnalyzeButton();
            } else { throw new Error('Backend not responding'); }
        } catch (error) {
            this.isBackendConnected = false; this.knowledgeBaseLoaded = false;
            this.updateStatusBar('Backend disconnected', 'Knowledge Base: Not loaded');
            this.updateAnalyzeButton();
        }
    }
    updateStatusBar(statusText, knowledgeText) {
        document.getElementById('backendStatus').classList.toggle('connected', this.isBackendConnected);
        document.getElementById('statusText').textContent = statusText;
        document.getElementById('knowledgeBaseStatus').textContent = knowledgeText;
    }
    handleMonographFiles(files) {
        this.monographFiles = Array.from(files);
        this.displayFileList('monographFileList', this.monographFiles, 'monograph');
        document.getElementById('uploadMonographsBtn').style.display = this.monographFiles.length > 0 ? 'inline-block' : 'none';
        this.updateAnalyzeButton();
    }
    handleProductFiles(files) {
        this.productFiles = Array.from(files);
        this.displayFileList('productFileList', this.productFiles, 'product');
        this.updateAnalyzeButton();
    }
    displayFileList(containerId, files, type) {
        const container = document.getElementById(containerId);
        if (files.length === 0) { container.style.display = 'none'; return; }
        container.style.display = 'block';
        const existingList = container.querySelector('.file-list-content');
        if (existingList) existingList.remove();
        const fileListDiv = document.createElement('div');
        fileListDiv.className = 'file-list-content';
        files.forEach((file, index) => {
            const fileItem = document.createElement('div');
            fileItem.className = 'file-item';
            fileItem.innerHTML = `<div><strong>${file.name}</strong><span style="color: #6c757d; margin-left: 10px;">(${this.formatFileSize(file.size)})</span></div><button class="btn btn-danger btn-sm" onclick="app.removeFile('${type}', ${index})">Remove</button>`;
            fileListDiv.appendChild(fileItem);
        });
        container.appendChild(fileListDiv);
    }
    removeFile(type, index) {
        if (type === 'monograph') {
            this.monographFiles.splice(index, 1);
            this.displayFileList('monographFileList', this.monographFiles, 'monograph');
            document.getElementById('uploadMonographsBtn').style.display = this.monographFiles.length > 0 ? 'inline-block' : 'none';
        } else {
            this.productFiles.splice(index, 1);
            this.displayFileList('productFileList', this.productFiles, 'product');
        }
        this.updateAnalyzeButton();
    }
    updateAnalyzeButton() {
        const btn = document.getElementById('analyzeBtn');
        const canAnalyze = this.isBackendConnected && this.knowledgeBaseLoaded && this.productFiles.length > 0;
        btn.disabled = !canAnalyze;
        if (!this.isBackendConnected) { btn.textContent = '🔍 Backend Disconnected'; } 
        else if (!this.knowledgeBaseLoaded) { btn.textContent = '🔍 Upload Monographs First'; } 
        else if (this.productFiles.length === 0) { btn.textContent = '🔍 Select Product Documents'; } 
        else { btn.textContent = '🔍 Analyze Product with RAG'; }
    }
    async uploadMonographs() {
        if (!this.isBackendConnected) { this.showAlert('Backend is not connected', 'error'); return; }
        if (this.monographFiles.length === 0) { this.showAlert('Please select monograph files first', 'warning'); return; }
        const formData = new FormData();
        this.monographFiles.forEach(file => formData.append('files', file));
        const progressBar = document.getElementById('monographProgress');
        const progressFill = document.getElementById('monographProgressFill');
        const statusDiv = document.getElementById('monographStatus');
        progressBar.style.display = 'block';
        progressFill.style.width = '0%';
        statusDiv.innerHTML = '';
        try {
            this.showAlert('Uploading files... Processing will continue in the background.', 'info');
            const response = await fetch(`${this.backendUrl}/api/upload-monographs`, { method: 'POST', body: formData });
            progressFill.style.width = '100%';
            if (response.status === 202) {
                const result = await response.json();
                setTimeout(() => {
                    progressBar.style.display = 'none';
                    this.showAlert(result.message, 'success');
                    statusDiv.innerHTML = `<div class="alert alert-info" style="position: static;"><strong>Processing in Background:</strong> The knowledge base is updating. The document count will increase automatically when complete.</div>`;
                }, 500);
            } else {
                const errorData = await response.json();
                throw new Error(errorData.error || `Upload failed: ${response.statusText}`);
            }
        } catch (error) {
            progressBar.style.display = 'none';
            this.showAlert(`Error uploading monographs: ${error.message}`, 'error');
            console.error('Upload error:', error);
        }
    }
    generateSummary(summary) {
        const summaryContent = document.getElementById('summaryContent');
        summaryContent.innerHTML = `<div class="summary-card"><div class="summary-number">${summary.total_ingredients}</div><div class="summary-label">Total Ingredients</div></div><div class="summary-card"><div class="summary-number">${summary.medicinal_count}</div><div class="summary-label">Medicinal</div></div><div class="summary-card"><div class="summary-number">${summary.non_medicinal_count}</div><div class="summary-label">Non-Medicinal</div></div><div class="summary-card"><div class="summary-number">${summary.high_confidence_count}</div><div class="summary-label">High Confidence</div></div>`;
        if (summary.class_distribution) {
            const classInfo = document.createElement('div');
            classInfo.style.gridColumn = '1 / -1';
            classInfo.style.marginTop = '20px';
            classInfo.innerHTML = `<h4 style="margin-bottom: 15px;">Classification Distribution</h4><div style="display: flex; gap: 15px; justify-content: center; flex-wrap: wrap;"><span class="class-badge class-1">Class 1: ${summary.class_distribution.class_1}</span><span class="class-badge class-2">Class 2: ${summary.class_distribution.class_2}</span><span class="class-badge class-3">Class 3: ${summary.class_distribution.class_3}</span></div>`;
            summaryContent.appendChild(classInfo);
        }
    }
    displayIngredients(ingredients, containerId, isMedicinal) {
        const container = document.getElementById(containerId);
        if (!ingredients || ingredients.length === 0) {
            container.innerHTML = `<div class="alert alert-warning" style="position: static;">No ${isMedicinal ? 'medicinal' : 'non-medicinal'} ingredients found.</div>`;
            return;
        }
        container.innerHTML = ingredients.map(ingredient => {
            const classification = ingredient.classification || {};
            const confidenceClass = this.getConfidenceClass(ingredient.confidence_score || 0);
            return `<div class="ingredient-item"><div class="ingredient-name">${ingredient.name}</div><div class="ingredient-amount">Amount: ${ingredient.amount || 'Not specified'}</div><div style="margin: 10px 0;">${isMedicinal ? `<span class="class-badge class-${classification.class || 3}">${classification.classification_text || 'Class 3'}</span>` : `<span class="class-badge non-medicinal">Non-Medicinal</span>`} <span class="confidence-badge ${confidenceClass}">Confidence: ${Math.round((ingredient.confidence_score || 0) * 100)}%</span> ${classification.monograph_found ? `<span class="confidence-badge confidence-high">✓ Monograph Found</span>` : `<span class="confidence-badge confidence-low">⚠ No Monograph</span>`}</div><div class="reasoning"><strong>Analysis:</strong><br>${classification.reasoning || 'No detailed reasoning available.'}${classification.safety_notes ? `<br><br><strong>Safety Notes:</strong><br>${classification.safety_notes}` : ''}</div></div>`;
        }).join('');
    }
    getConfidenceClass(confidence) {
        if (confidence >= 0.7) return 'confidence-high';
        if (confidence >= 0.4) return 'confidence-medium';
        return 'confidence-low';
    }
    showAlert(message, type) {
        const alertContainer = document.getElementById('alertContainer');
        const alert = document.createElement('div');
        alert.className = `alert alert-${type}`;
        alert.innerHTML = `<strong>${type === 'error' ? '❌ Error' : type === 'success' ? '✅ Success:' : type === 'warning' ? '⚠️ Warning:' : 'ℹ️ Info:'}</strong> ${message}`;
        alertContainer.appendChild(alert);
        setTimeout(() => { if (alert.parentNode) { alert.remove(); } }, 5000);
    }
    formatFileSize(bytes) {
        if (!bytes || typeof bytes !== 'number' || bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
}

const app = new NHPAnalyzer();
window.app = app;

const fileInput = document.getElementById('fileInput');
const fileName = document.getElementById('fileName');
const uploadBtn = document.getElementById('uploadBtn');
const loading = document.getElementById('loading');
const loadingText = document.getElementById('loadingText');
const results = document.getElementById('results');
const error = document.getElementById('error');
const preview = document.getElementById('preview');
const previewContent = document.getElementById('previewContent');

let selectedFiles = [];
let fileContents = {};

fileInput.addEventListener('change', async (e) => {
    const files = Array.from(e.target.files);
    // Filter only .py files
    selectedFiles = files.filter(f => f.name.endsWith('.py'));
    fileContents = {};
    previewContent.innerHTML = '';
    preview.classList.add('hidden');
    
    if (selectedFiles.length > 0) {
        fileName.textContent = `${selectedFiles.length} Python file(s) selected`;
        uploadBtn.disabled = false;
        
        // Read and display file contents
        for (const file of selectedFiles) {
            const content = await file.text();
            fileContents[file.name] = content;
            
            const previewCard = document.createElement('div');
            previewCard.className = 'preview-card';
            previewCard.innerHTML = `
                <h3>${file.name}</h3>
                <pre>${escapeHtml(content)}</pre>
            `;
            previewContent.appendChild(previewCard);
        }
        preview.classList.remove('hidden');
    } else {
        fileName.textContent = 'Choose a folder';
        uploadBtn.disabled = true;
    }
});

uploadBtn.addEventListener('click', async () => {
    if (selectedFiles.length === 0) return;

    // Hide previous results/errors and preview
    results.classList.add('hidden');
    results.innerHTML = '';
    error.classList.add('hidden');
    preview.classList.add('hidden');
    
    // Show loading
    loadingText.textContent = `Analyzing ${selectedFiles.length} file(s)...`;
    loading.classList.remove('hidden');
    uploadBtn.disabled = true;

    try {
        const formData = new FormData();
        selectedFiles.forEach(file => {
            formData.append('files', file);
        });

        const response = await fetch('/analyze', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || 'Analysis failed');
        }

        const data = await response.json();

        // Display results for each file
        data.results.forEach(item => {
            const fileCard = document.createElement('div');
            fileCard.className = 'file-card';
            
            fileCard.innerHTML = `
                <h2 class="file-name">${item.filename}</h2>
                <div class="result-section">
                    <h3>Original Code</h3>
                    <pre>${escapeHtml(fileContents[item.filename] || '')}</pre>
                </div>
                <div class="result-section">
                    <h3>Audit Report</h3>
                    <pre>${escapeHtml(item.report)}</pre>
                </div>
                <div class="result-section">
                    <h3>Fixed Code</h3>
                    <pre>${escapeHtml(item.fixed_code)}</pre>
                </div>
            `;
            
            results.appendChild(fileCard);
        });
        
        results.classList.remove('hidden');
    } catch (err) {
        error.textContent = err.message;
        error.classList.remove('hidden');
    } finally {
        loading.classList.add('hidden');
        uploadBtn.disabled = false;
    }
});

// Helper function to escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

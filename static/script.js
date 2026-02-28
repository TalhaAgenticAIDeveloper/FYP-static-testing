const fileInput = document.getElementById('fileInput');
const fileName = document.getElementById('fileName');
const uploadBtn = document.getElementById('uploadBtn');
const loading = document.getElementById('loading');
const loadingText = document.getElementById('loadingText');
const results = document.getElementById('results');
const error = document.getElementById('error');
const preview = document.getElementById('preview');
const previewContent = document.getElementById('previewContent');
const skipInfo = document.getElementById('skipInfo');

let selectedFiles = [];
let fileContents = {};

// ── Folder-skip list ─────────────────────────────────────────────────
// Hardcoded default (kept in sync with scan_config.py).
// Overwritten by /skip-folders on page load when available.
let skipFolders = [
    'venv', '.venv', 'env', '.env', 'virtualenv', 'conda-env',
    '__pycache__', '.eggs', 'egg-info', 'dist', 'build', 'sdist',
    'site-packages', 'lib', 'scripts', 'include', 'share', 'lib64',
    'node_modules',
    '.git', '.svn', '.hg', '.idea', '.vscode',
    '.tox', '.nox', '.mypy_cache', '.pytest_cache', '.ruff_cache',
    'htmlcov', '.coverage',
    'migrations', '.terraform'
];

// Fetch the authoritative skip list from the backend on page load
fetch('/skip-folders')
    .then(res => res.json())
    .then(data => {
        if (data.skip_folders && data.skip_folders.length > 0) {
            skipFolders = data.skip_folders;
        }
        console.log('[SkipFolders] Loaded', skipFolders.length, 'skip patterns');
    })
    .catch(() => { console.log('[SkipFolders] Using hardcoded defaults'); });

/**
 * Returns true if the file's relative path passes through a skipped folder.
 * Checks every directory component (case-insensitive).
 */
function isInSkippedFolder(relativePath) {
    const parts = relativePath.replace(/\\/g, '/').split('/');
    // Check every directory component except the last (the filename)
    for (let i = 0; i < parts.length - 1; i++) {
        const part = parts[i].toLowerCase();
        if (skipFolders.includes(part)) return true;
        // Also catch "*.egg-info" style folder names
        for (const sf of skipFolders) {
            if ((sf.includes('-') || sf.includes('.')) && part.endsWith(sf)) return true;
        }
    }
    return false;
}

/**
 * Show/hide the skip-info banner with a summary message.
 */
function showSkipInfo(totalPy, accepted, skipped) {
    if (!skipInfo) return;
    if (skipped > 0) {
        skipInfo.innerHTML =
            `📁 Found <strong>${totalPy}</strong> Python file(s) total — ` +
            `<strong>${skipped}</strong> skipped (excluded folders) — ` +
            `<strong>${accepted}</strong> file(s) ready for analysis.`;
        skipInfo.classList.remove('hidden');
    } else {
        skipInfo.classList.add('hidden');
    }
}

fileInput.addEventListener('change', async (e) => {
    const allFiles = Array.from(e.target.files);

    // Step 1 — keep only .py files
    const pyFiles = allFiles.filter(f => f.name.endsWith('.py'));

    // Step 2 — filter out files inside skipped folders
    const accepted = [];
    let skippedCount = 0;

    for (const f of pyFiles) {
        const relPath = f.webkitRelativePath || f.name;
        if (isInSkippedFolder(relPath)) {
            skippedCount++;
        } else {
            accepted.push(f);
        }
    }

    console.log(`[Filter] ${allFiles.length} total → ${pyFiles.length} .py → ${accepted.length} accepted (${skippedCount} skipped)`);

    selectedFiles = accepted;
    fileContents = {};
    previewContent.innerHTML = '';
    preview.classList.add('hidden');

    // Show skip summary
    showSkipInfo(pyFiles.length, accepted.length, skippedCount);
    
    if (selectedFiles.length > 0) {
        fileName.textContent = `${selectedFiles.length} Python file(s) selected`;
        uploadBtn.disabled = false;
        
        // Read and display file contents
        for (const file of selectedFiles) {
            const content = await file.text();
            fileContents[file.webkitRelativePath || file.name] = content;
            
            const previewCard = document.createElement('div');
            previewCard.className = 'preview-card';
            previewCard.innerHTML = `
                <h3>${file.webkitRelativePath || file.name}</h3>
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
            
            // Try to find original content by filename or webkitRelativePath
            const originalCode = fileContents[item.filename] || '';

            fileCard.innerHTML = `
                <h2 class="file-name">${item.filename}</h2>
                <div class="result-section">
                    <h3>Original Code</h3>
                    <pre>${escapeHtml(originalCode)}</pre>
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

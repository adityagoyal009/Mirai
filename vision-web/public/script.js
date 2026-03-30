const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const preview = document.getElementById('preview');
const analyzeBtn = document.getElementById('analyze-btn');
const promptInput = document.getElementById('prompt');
const resultSection = document.getElementById('result-section');
const analysisText = document.getElementById('analysis-text');
const loader = document.getElementById('loader');

let selectedFile = null;

// Click to upload
dropZone.addEventListener('click', () => fileInput.click());

// Drag and drop
dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('drag-over');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    if (e.dataTransfer.files.length) {
        handleFile(e.dataTransfer.files[0]);
    }
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length) {
        handleFile(e.target.files[0]);
    }
});

function handleFile(file) {
    if (!file.type.startsWith('image/')) {
        alert('Please upload an image file.');
        return;
    }
    selectedFile = file;
    const reader = new FileReader();
    reader.onload = (e) => {
        preview.src = e.target.result;
        preview.classList.remove('hidden');
        dropZone.querySelector('p').classList.add('hidden');
        analyzeBtn.disabled = false;
    };
    reader.readAsDataURL(file);
}

analyzeBtn.addEventListener('click', async () => {
    if (!selectedFile) return;

    const formData = new FormData();
    formData.append('image', selectedFile);
    formData.append('prompt', promptInput.value);

    // Reset UI
    analyzeBtn.disabled = true;
    resultSection.classList.remove('hidden');
    analysisText.textContent = '';
    loader.classList.remove('hidden');

    try {
        const response = await fetch('/analyze', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Analysis failed');
        }

        analysisText.textContent = data.analysis;
    } catch (e) {
        analysisText.innerHTML = `<span style="color: #ef4444;">Error: ${e.message}</span>`;
    } finally {
        loader.classList.add('hidden');
        analyzeBtn.disabled = false;
    }
});

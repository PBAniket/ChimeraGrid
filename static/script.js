let accumulatedFilesArray = [];

function toggleInputMode(radio, dfId, colName) {
    const examplesDiv = document.getElementById(`examples-container-${dfId}-${colName}`);
    const promptDiv = document.getElementById(`prompt-container-${dfId}-${colName}`);
    
    const exampleInputs = examplesDiv ? examplesDiv.querySelectorAll('input[type="text"]') : [];
    const promptTextarea = promptDiv ? promptDiv.querySelector('textarea') : null;

    if (radio.value === 'examples') {
        if (examplesDiv) examplesDiv.classList.remove('hidden');
        if (promptDiv) promptDiv.classList.add('hidden');
        exampleInputs.forEach(input => input.required = true);
        if (promptTextarea) promptTextarea.required = false;
    } else {
        if (examplesDiv) examplesDiv.classList.add('hidden');
        if (promptDiv) promptDiv.classList.remove('hidden');
        exampleInputs.forEach(input => input.required = false);
        if (promptTextarea) promptTextarea.required = true;
    }
}

async function submitAccumulatedFiles() {
    const submitBtn = document.getElementById('submit-btn');
    const fileListDisplay = document.getElementById('file-list');

    if (accumulatedFilesArray.length === 0) {
        fileListDisplay.textContent = 'Please select at least one file to upload.';
        fileListDisplay.style.color = 'red';
        return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = 'Uploading...';
    submitBtn.classList.add('opacity-50', 'cursor-not-allowed');
    fileListDisplay.style.color = '';

    const formData = new FormData();
    for (const file of accumulatedFilesArray) {
        formData.append('file', file);
    }

    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData,
        });

        console.log('Fetch response status:', response.status);
        console.log('Fetch response ok:', response.ok);
        console.log('Fetch response URL (after redirects):', response.url);

        if (response.ok) {
            console.log('Upload successful! Navigating to:', response.url);
            window.location.href = response.url; 
        } else {
            const errorText = await response.text();
            fileListDisplay.textContent = `Upload failed (Status: ${response.status}): ${errorText}`;
            fileListDisplay.style.color = 'red';
            console.error('Upload failed details:', response.status, errorText);
        }
    } catch (error) {
        fileListDisplay.textContent = `Network error during upload: ${error.message}. Check server status.`;
        fileListDisplay.style.color = 'red';
        console.error('Network error caught by client:', error);
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Upload';
        submitBtn.classList.remove('opacity-50', 'cursor-not-allowed');
    }
}


document.addEventListener('DOMContentLoaded', () => {
    const dropArea = document.getElementById('drop-area');
    if (dropArea) {
        let fileInput = document.getElementById('file-input');
        let fileListDisplay = document.getElementById('file-list');
        let submitBtn = document.getElementById('submit-btn');

        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, preventDefaults, false);
        });
        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }

        ['dragenter', 'dragover'].forEach(eventName => {
            dropArea.addEventListener(eventName, () => dropArea.classList.add('highlight'), false);
        });
        ['dragleave', 'drop'].forEach(eventName => {
            dropArea.classList.remove('highlight');
        });

        dropArea.addEventListener('drop', handleDrop, false);
        function handleDrop(e) {
            let dt = e.dataTransfer;
            addFilesToAccumulator(dt.files);
        }

        dropArea.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', function() {
            addFilesToAccumulator(this.files);
            this.value = null; 
        });

        function addFilesToAccumulator(files) {
            for (let i = 0; i < files.length; i++) {
                const newFile = files[i];
                const isDuplicate = accumulatedFilesArray.some(existingFile => 
                    existingFile.name === newFile.name && existingFile.size === newFile.size
                );
                if (!isDuplicate) {
                    accumulatedFilesArray.push(newFile);
                }
            }
            updateFileListDisplay();
        }

        function updateFileListDisplay() {
            let fileNames = accumulatedFilesArray.map(file => file.name);

            if (fileNames.length > 0) {
                fileListDisplay.textContent = `${fileNames.length} file(s) selected: ${fileNames.join(', ')}`;
                fileListDisplay.style.color = '';
                if (submitBtn) submitBtn.style.display = 'inline-block';
            } else {
                fileListDisplay.textContent = '';
                if (submitBtn) submitBtn.style.display = 'none';
            }
        }

        if (submitBtn) submitBtn.style.display = 'none';
    }

    const inputModeRadios = document.querySelectorAll('input[name^="input_mode_"]');
    if (inputModeRadios.length > 0) {
        inputModeRadios.forEach(radio => {
            radio.addEventListener('change', function() {
                const parts = this.name.split('_');
                const dfId = parts[2];
                const colNameEncoded = parts[3];
                toggleInputMode(this, dfId, colNameEncoded);
            });
            if (radio.checked) {
                const parts = radio.name.split('_');
                const dfId = parts[2];
                const colNameEncoded = parts[3];
                toggleInputMode(radio, dfId, colNameEncoded);
            }
        });
    }
});

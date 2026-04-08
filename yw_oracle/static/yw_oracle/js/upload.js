document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const uploadForm = document.getElementById('uploadForm');
    const previewModal = document.getElementById('previewModal');
    const closePreviewModal = document.getElementById('closePreviewModal');

    // New Elements
    const selectedFileCard = document.getElementById('selectedFileCard');
    const fileNameDisplay = document.getElementById('fileNameDisplay');
    const fileSizeDisplay = document.getElementById('fileSizeDisplay');
    const removeFileBtn = document.getElementById('removeFileBtn');
    const submitBtn = document.getElementById('submitBtn');
    const loadingOverlay = document.getElementById('loadingOverlay');
    const loadingText = document.getElementById('loadingText');

    // Validation Elements
    const validationErrorsPanel = document.getElementById('validationErrorsPanel');
    const validationErrorsList = document.getElementById('validationErrorsList');

    // Preview Elements
    const previewTable = document.getElementById('modalPreviewTable');
    const cancelProcessBtn = document.getElementById('cancelProcessBtn');
    const confirmProcessBtn = document.getElementById('confirmProcessBtn');
    const modalCancelProcessBtn = document.getElementById('modalCancelProcessBtn');
    const modalConfirmProcessBtn = document.getElementById('modalConfirmProcessBtn');

    // State
    let currentUploadId = null;

    // Modal Elements
    const resultModal = document.getElementById('resultModal');
    const modalIcon = document.getElementById('modalIcon');
    const modalTitle = document.getElementById('modalTitle');
    const modalMessage = document.getElementById('modalMessage');
    const modalCloseBtn = document.getElementById('modalCloseBtn');

    // Planilla type selector
    const planillaOptions = document.querySelectorAll('.planilla-option');
    planillaOptions.forEach(option => {
        option.addEventListener('click', () => {
            planillaOptions.forEach(o => o.classList.remove('active'));
            option.classList.add('active');
        });
    });

    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });

    // Highlight drop zone
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, unhighlight, false);
    });

    // Handle dropped files
    dropZone.addEventListener('drop', handleDrop, false);

    // Handle click to select
    dropZone.addEventListener('click', () => fileInput.click());

    // Handle file selection
    fileInput.addEventListener('change', (e) => handleFiles(e.target.files));

    // Cancel Button Logic
    removeFileBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        resetFile();
    });

    // Preview Actions
    if (cancelProcessBtn) {
        cancelProcessBtn.addEventListener('click', () => resetFile());
    }
    if (modalCancelProcessBtn) {
        modalCancelProcessBtn.addEventListener('click', () => resetFile());
    }

    const handleConfirm = async () => {
        if (!currentUploadId) return;
        showLoading(true, "Por favor, estamos subiendo los datos...");
        try {
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 600000); // 10 minutes timeout

            const res = await fetch('', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    action: 'confirm_upload',
                    upload_id: currentUploadId
                }),
                signal: controller.signal
            });

            clearTimeout(timeoutId);
            if (!res.ok) throw new Error('Error enviando datos');
            const result = await res.json();
            showResult(result);
        } catch (error) {
            console.error(error);
            const errorMsg = error.name === 'AbortError'
                ? 'La solicitud tardó demasiado tiempo. Por favor, intenta de nuevo.'
                : error.message;
            showResult({ valid: false, error: errorMsg });
        } finally {
            showLoading(false);
        }
    };

    if (confirmProcessBtn) {
        confirmProcessBtn.addEventListener('click', handleConfirm);
    }
    if (modalConfirmProcessBtn) {
        modalConfirmProcessBtn.addEventListener('click', handleConfirm);
    }

    // Modal Close Logic
    if (modalCloseBtn) {
        modalCloseBtn.addEventListener('click', () => {
            resultModal.style.display = 'none';
        });
    }

    if (resultModal) {
        resultModal.addEventListener('click', (e) => {
            if (e.target === resultModal) {
                resultModal.style.display = 'none';
            }
        });
    }

    // Form submission (Initial Upload)
    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        hideValidationErrors();

        if (!fileInput.files.length) {
            alert('Por favor selecciona un archivo primero.');
            return;
        }

        const formData = new FormData(e.target);
        showLoading(true, "Analizando archivo...");

        try {
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 600000); // 10 minutes timeout

            const res = await fetch('', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': csrfToken
                },
                signal: controller.signal
            });

            clearTimeout(timeoutId);
            if (!res.ok) {
                try {
                    const errData = await res.json();
                    throw new Error(errData.error || `Server error: ${res.status}`);
                } catch {
                    throw new Error(`Server error: ${res.status}`);
                }
            }

            const data = await res.json();

            if (data.status === 'preview') {
                currentUploadId = data.upload_id;
                renderPreview(data);
                if (data.warnings && data.warnings.length > 0) {
                    showValidationErrors(data.warnings);
                }
            } else if (data.errors) {
                showValidationErrors(data.errors, data.upload_id);
            } else {
                showResult(data);
            }

        } catch (error) {
            console.error('Upload failed:', error);
            const errorMsg = error.name === 'AbortError'
                ? 'El análisis del archivo tardó demasiado tiempo. Por favor, intenta de nuevo.'
                : error.message;
            showResult({ valid: false, error: errorMsg });
        } finally {
            showLoading(false);
        }
    });

    // --- Helper Functions ---

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    function highlight() {
        dropZone.style.borderColor = '#0d6efd';
        dropZone.style.backgroundColor = '#eff6ff';
    }

    function unhighlight() {
        dropZone.style.borderColor = '#cbd5e1';
        dropZone.style.backgroundColor = '#f8fafc';
    }

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files);
    }

    function handleFiles(files) {
        if (files.length > 0) {
            const file = files[0];

            if (!file.name.match(/\.(xlsx|xls)$/)) {
                alert('Por favor sube un archivo Excel valido (.xlsx o .xls)');
                resetFile();
                return;
            }

            fileInput.files = files;
            updateFileInfo(file);
        }
    }

    function updateFileInfo(file) {
        fileNameDisplay.textContent = file.name;
        fileSizeDisplay.textContent = formatBytes(file.size);

        dropZone.style.display = 'none';
        selectedFileCard.style.display = 'flex';
        selectedFileCard.classList.add('file-info-active');
    }

    function resetFile() {
        fileInput.value = '';
        selectedFileCard.style.display = 'none';
        dropZone.style.display = 'flex';
        previewModal.style.display = 'none';
        currentUploadId = null;
        hideValidationErrors();
    }

    function formatBytes(bytes, decimals = 2) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    }

    function showLoading(isLoading, message = "Procesando...") {
        if (isLoading) {
            if (loadingText) loadingText.textContent = message;
            loadingOverlay.style.display = 'flex';
            submitBtn.disabled = true;
            removeFileBtn.disabled = true;
        } else {
            loadingOverlay.style.display = 'none';
            submitBtn.disabled = false;
            removeFileBtn.disabled = false;
        }
    }

    function showValidationErrors(errors, uploadId = null) {
        validationErrorsList.innerHTML = '';

        // Download button when transformed data is available
        if (uploadId) {
            const dlDiv = document.createElement('div');
            dlDiv.className = 'validation-download-row';
            dlDiv.innerHTML = `
                <span><i class="fa-solid fa-circle-info"></i> Se generó el Excel transformado para diagnóstico</span>
                <a href="/oracle/download_excel/${uploadId}/" class="btn-download-excel-inline">
                    <i class="fa-solid fa-file-arrow-down"></i> Descargar Excel transformado
                </a>
            `;
            validationErrorsList.appendChild(dlDiv);
        }

        errors.forEach(err => {
            const level = err.level || 'error';
            const icon = level === 'error' ? 'fa-circle-xmark' : 'fa-triangle-exclamation';
            const div = document.createElement('div');
            div.className = `validation-error-item ${level}`;

            let detailsHtml = '';
            if (err.details) {
                if (err.details.rows && err.details.rows.length > 0) {
                    detailsHtml = `<div class="validation-error-details">Filas: ${err.details.rows.join(', ')}</div>`;
                }
                if (err.details.missing_columns) {
                    detailsHtml = `<div class="validation-error-details">Columnas: ${err.details.missing_columns.join(', ')}</div>`;
                }
            }

            div.innerHTML = `
                <i class="fa-solid ${icon}"></i>
                <div>
                    <div>${err.message}</div>
                    ${detailsHtml}
                </div>
            `;
            validationErrorsList.appendChild(div);
        });
        validationErrorsPanel.style.display = 'block';
    }

    function hideValidationErrors() {
        validationErrorsPanel.style.display = 'none';
        validationErrorsList.innerHTML = '';
    }

    function renderPreview(data) {
        // Populate JSON viewer
        if (jsonPayloadViewer && data.netsuite_payload) {
            jsonPayloadViewer.textContent = JSON.stringify(data.netsuite_payload, null, 2);
        }

        // Totals bar
        const totalDebitEl = document.getElementById('totalDebitDisplay');
        const totalCreditEl = document.getElementById('totalCreditDisplay');
        const totalDiffEl = document.getElementById('totalDiffDisplay');
        const totalDiffItem = document.getElementById('totalDiffItem');
        const downloadBtn = document.getElementById('downloadExcelBtn');

        if (totalDebitEl && data.total_debit !== undefined) {
            const debit = parseFloat(data.total_debit);
            const credit = parseFloat(data.total_credit);
            const diff = parseFloat((debit - credit).toFixed(4));

            totalDebitEl.textContent = debit.toLocaleString('es-PE', { minimumFractionDigits: 4, maximumFractionDigits: 4 });
            totalCreditEl.textContent = credit.toLocaleString('es-PE', { minimumFractionDigits: 4, maximumFractionDigits: 4 });
            totalDiffEl.textContent = diff.toLocaleString('es-PE', { minimumFractionDigits: 4, maximumFractionDigits: 4 });

            totalDiffItem.classList.remove('diff-ok', 'diff-warn');
            totalDiffItem.classList.add(Math.abs(diff) < 0.01 ? 'diff-ok' : 'diff-warn');
        }

        // Download Excel button
        if (downloadBtn && data.upload_id) {
            downloadBtn.href = `/oracle/download_excel/${data.upload_id}/`;
            downloadBtn.style.display = 'inline-flex';
        }

        const thead = previewTable.querySelector('thead');
        const tbody = previewTable.querySelector('tbody');

        thead.innerHTML = '';
        tbody.innerHTML = '';

        if (data.columns && data.columns.length > 0) {
            const headerRow = document.createElement('tr');
            data.columns.forEach(col => {
                const th = document.createElement('th');
                th.textContent = col;
                headerRow.appendChild(th);
            });
            thead.appendChild(headerRow);
        }

        if (data.table_data && data.table_data.length > 0) {
            data.table_data.forEach(row => {
                const tr = document.createElement('tr');
                data.columns.forEach(col => {
                    const td = document.createElement('td');
                    const value = row[col];
                    td.textContent = value !== null && value !== undefined ? value : '';
                    tr.appendChild(td);
                });
                tbody.appendChild(tr);
            });
        }

        previewModal.style.display = 'flex';
    }

    function showResult(data) {
        modalIcon.innerHTML = '';
        modalCloseBtn.classList.remove('error');

        resultModal.style.display = 'flex';

        if (data.valid) {
            modalIcon.innerHTML = '<i class="fa-solid fa-circle-check icon-success"></i>';
            modalTitle.textContent = '¡Carga Exitosa!';

            // Extract journal entry ID from ns_results
            let journalId = null;
            if (data.ns_results && data.ns_results.length > 0) {
                const res = data.ns_results[0];
                if (res.data) {
                    const body = res.data.body || res.data;
                    const firstItem = Array.isArray(body) ? body[0] : body;
                    journalId = firstItem?.id ?? null;
                }
            }

            let msg = `El asiento contable fue registrado exitosamente en NetSuite.`;
            if (journalId) {
                msg += `<div style="margin-top: 14px; background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 12px 16px; display: inline-flex; align-items: center; gap: 10px;">
                    <i class="fa-solid fa-hashtag" style="color: #16a34a; font-size: 1rem;"></i>
                    <span style="font-size: 0.95rem; color: #15803d; font-weight: 600;">ID de asiento: <span style="font-size: 1.1rem;">${journalId}</span></span>
                </div>`;
            }
            if (data.row_count) {
                msg += `<p style="margin-top: 12px; font-size: 0.85rem; color: #64748b;">${data.row_count} filas procesadas</p>`;
            }

            // Show full server response for Owner role
            const userRole = document.querySelector('.portal-wrapper')?.getAttribute('data-user-role');
            if (userRole === 'Owner' && data.ns_results && data.ns_results.length > 0) {
                msg += `<details style="margin-top: 16px; padding: 12px; background: #f8f9fa; border: 1px solid #e2e8f0; border-radius: 6px; cursor: pointer;">
                    <summary style="font-weight: 600; color: #475569; font-size: 0.9rem; user-select: none;">
                        <i class="fa-solid fa-code" style="margin-right: 6px;"></i> Ver respuesta del servidor
                    </summary>
                    <pre style="margin-top: 10px; background: #1e293b; color: #e2e8f0; padding: 12px; border-radius: 4px; overflow-x: auto; font-size: 0.8rem; line-height: 1.4;">${JSON.stringify(data.ns_results[0].data, null, 2)}</pre>
                </details>`;
            }

            modalMessage.innerHTML = msg;
            resetFile();
        } else {
            modalIcon.innerHTML = '<i class="fa-solid fa-circle-xmark icon-error"></i>';
            modalTitle.textContent = 'No se pudo completar la carga';

            // Show a clean user-friendly error, not raw JSON
            const rawError = data.error || 'Ocurrió un error desconocido.';
            // Try to extract just the meaningful message from NetSuite error strings
            let friendlyError = rawError;
            try {
                const match = rawError.match(/"detail"\s*:\s*"([^"]+)"/);
                if (match) friendlyError = match[1];
            } catch (_) {}

            modalMessage.innerHTML = `<p style="color: #b91c1c; font-size: 0.95rem; line-height: 1.5;">${friendlyError}</p>
                <p style="margin-top: 10px; font-size: 0.8rem; color: #94a3b8;">Si el problema persiste, contacta al administrador del sistema.</p>`;
            modalCloseBtn.classList.add('error');
        }
    }

    // Preview Modal Tabs
    const previewTabs = document.querySelectorAll('.preview-tab');
    const tabTable = document.getElementById('tabTable');
    const tabJson = document.getElementById('tabJson');
    const jsonPayloadViewer = document.getElementById('jsonPayloadViewer');
    const copyJsonBtn = document.getElementById('copyJsonBtn');

    previewTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            previewTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            if (tab.dataset.tab === 'table') {
                tabTable.style.display = 'block';
                tabJson.style.display = 'none';
            } else {
                tabTable.style.display = 'none';
                tabJson.style.display = 'block';
            }
        });
    });

    if (copyJsonBtn) {
        copyJsonBtn.addEventListener('click', () => {
            const text = jsonPayloadViewer.textContent;
            navigator.clipboard.writeText(text).then(() => {
                copyJsonBtn.classList.add('copied');
                copyJsonBtn.innerHTML = '<i class="fa-solid fa-check"></i> Copiado';
                setTimeout(() => {
                    copyJsonBtn.classList.remove('copied');
                    copyJsonBtn.innerHTML = '<i class="fa-regular fa-copy"></i> Copiar';
                }, 2000);
            });
        });
    }

    // Modal close button
    closePreviewModal.addEventListener('click', () => {
        previewModal.style.display = 'none';
        resetPreviewTabs();
    });

    // Close modal when clicking outside
    previewModal.addEventListener('click', (e) => {
        if (e.target === previewModal) {
            previewModal.style.display = 'none';
            resetPreviewTabs();
        }
    });

    function resetPreviewTabs() {
        previewTabs.forEach(t => t.classList.remove('active'));
        const firstTab = document.querySelector('.preview-tab[data-tab="table"]');
        if (firstTab) firstTab.classList.add('active');
        if (tabTable) tabTable.style.display = 'block';
        if (tabJson) tabJson.style.display = 'none';
    }

});

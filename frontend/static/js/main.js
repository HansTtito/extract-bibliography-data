const API_BASE = '/api';

// Tab switching
function switchTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
    });

    // Show selected tab
    document.getElementById(`${tabName}-tab`).classList.add('active');
    if (event && event.target) {
        event.target.classList.add('active');
    } else {
        // Si no hay event (llamado programático), activar el botón correspondiente
        document.querySelectorAll('.tab-button').forEach(btn => {
            if (btn.textContent.includes(getTabLabel(tabName))) {
                btn.classList.add('active');
            }
        });
    }

    // Load documents if switching to documents tab
    if (tabName === 'documents') {
        loadDocuments();
    }
}

function getTabLabel(tabName) {
    const labels = {
        'pdf': 'Subir PDF',
        'reference': 'Subir Referencia',
        'references-pdf': 'PDF de Referencias',
        'documents': 'Ver Documentos'
    };
    return labels[tabName] || '';
}

// PDF Upload
document.getElementById('pdf-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData();
    const fileInput = document.getElementById('pdf-file');
    const resultDiv = document.getElementById('pdf-result');

    if (!fileInput.files[0]) {
        showResult(resultDiv, 'Por favor selecciona un archivo PDF', 'error');
        return;
    }

    formData.append('file', fileInput.files[0]);
    resultDiv.innerHTML = '<div class="loading">Procesando PDF...</div>';
    resultDiv.className = 'result';

    try {
        const response = await fetch(`${API_BASE}/upload-pdf`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (response.ok && data.success) {
            showPDFResult(resultDiv, data.document);
            fileInput.value = ''; // Reset form
        } else {
            showResult(resultDiv, data.detail || 'Error procesando PDF', 'error');
        }
    } catch (error) {
        showResult(resultDiv, `Error: ${error.message}`, 'error');
    }
});

// Reference Upload
document.getElementById('reference-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const referenceText = document.getElementById('reference-text').value;
    const resultDiv = document.getElementById('reference-result');

    if (!referenceText.trim()) {
        showResult(resultDiv, 'Por favor ingresa una referencia bibliográfica', 'error');
        return;
    }

    // Detectar si hay múltiples referencias (separadas por líneas)
    const lines = referenceText.split('\n').filter(line => line.trim());
    const hasMultipleRefs = lines.length > 1 && lines.some(line => {
        // Verificar si la línea tiene formato de referencia (año)
        return /\b(19|20)\d{2}\b/.test(line) && line.trim().length > 30;
    });

    if (hasMultipleRefs) {
        // Procesar múltiples referencias
        resultDiv.innerHTML = '<div class="loading">Procesando ' + lines.length + ' referencias...</div>';
        resultDiv.className = 'result';

        try {
            const response = await fetch(`${API_BASE}/upload-multiple-references`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ references: lines })
            });

            const data = await response.json();

            if (response.ok && data.success) {
                showMultipleReferencesResult(resultDiv, data);
                document.getElementById('reference-text').value = ''; // Reset form
            } else {
                showResult(resultDiv, data.detail || 'Error procesando referencias', 'error');
            }
        } catch (error) {
            showResult(resultDiv, `Error: ${error.message}`, 'error');
        }
    } else {
        // Procesar una sola referencia
        resultDiv.innerHTML = '<div class="loading">Procesando referencia...</div>';
        resultDiv.className = 'result';

        try {
            const response = await fetch(`${API_BASE}/upload-reference`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ reference_text: referenceText })
            });

            const data = await response.json();

            if (response.ok && data.success) {
                showReferenceResult(resultDiv, data.document, data.enriched);
                document.getElementById('reference-text').value = ''; // Reset form
            } else {
                showResult(resultDiv, data.detail || 'Error procesando referencia', 'error');
            }
        } catch (error) {
            showResult(resultDiv, `Error: ${error.message}`, 'error');
        }
    }
});

// Show result message
function showResult(div, message, type) {
    div.innerHTML = message;
    div.className = `result ${type}`;
}

// Show PDF result
function showPDFResult(div, document) {
    let html = '<div class="result success">';
    html += '<strong>✓ PDF procesado exitosamente</strong>';
    html += '<div class="result-info">';
    html += `<h3>Documento #${document.numero_doc}</h3>`;
    if (document.titulo_original) {
        html += `<p><strong>Título:</strong> ${document.titulo_original}</p>`;
    }
    if (document.autores) {
        html += `<p><strong>Autores:</strong> ${document.autores}</p>`;
    }
    if (document.ano) {
        html += `<p><strong>Año:</strong> ${document.ano}</p>`;
    }
    if (document.doi) {
        html += `<p><strong>DOI:</strong> ${document.doi}</p>`;
    }
    html += '</div></div>';
    div.innerHTML = html;
    div.className = 'result success';
}

// Show reference result
function showReferenceResult(div, document, enriched) {
    let html = '<div class="result success">';
    html += '<strong>✓ Referencia procesada exitosamente</strong>';
    if (enriched) {
        html += '<p style="color: #28a745; margin-top: 10px;">✓ Información enriquecida con CrossRef</p>';
    }
    html += '<div class="result-info">';
    html += `<h3>Documento #${document.numero_doc}</h3>`;
    if (document.titulo_original) {
        html += `<p><strong>Título:</strong> ${document.titulo_original}</p>`;
    }
    if (document.autores) {
        html += `<p><strong>Autores:</strong> ${document.autores}</p>`;
    }
    if (document.ano) {
        html += `<p><strong>Año:</strong> ${document.ano}</p>`;
    }
    if (document.lugar_publicacion_entrega) {
        html += `<p><strong>Lugar de publicación:</strong> ${document.lugar_publicacion_entrega}</p>`;
    }
    if (document.doi) {
        html += `<p><strong>DOI:</strong> ${document.doi}</p>`;
    }
    html += '</div></div>';
    div.innerHTML = html;
    div.className = 'result success';
}

// Load documents
async function loadDocuments() {
    const listDiv = document.getElementById('documents-list');
    listDiv.innerHTML = '<div class="loading">Cargando documentos...</div>';

    try {
        const response = await fetch(`${API_BASE}/documents`);
        const documents = await response.json();

        if (documents.length === 0) {
            listDiv.innerHTML = '<div class="empty-state"><p>📄</p><p>No hay documentos extraídos aún</p></div>';
            return;
        }

        let html = '';
        documents.forEach(doc => {
            html += '<div class="document-item">';
            html += `<h3>Documento #${doc.numero_doc}</h3>`;
            if (doc.titulo_original) {
                html += `<p><strong>Título:</strong> ${doc.titulo_original}</p>`;
            }
            if (doc.autores) {
                html += `<p><strong>Autores:</strong> ${doc.autores}</p>`;
            }
            if (doc.ano) {
                html += `<p><strong>Año:</strong> ${doc.ano}</p>`;
            }
            if (doc.lugar_publicacion_entrega) {
                html += `<p><strong>Lugar de publicación:</strong> ${doc.lugar_publicacion_entrega}</p>`;
            }
            if (doc.doi) {
                html += `<p><strong>DOI:</strong> ${doc.doi}</p>`;
            }
            html += '</div>';
        });

        listDiv.innerHTML = html;
    } catch (error) {
        listDiv.innerHTML = `<div class="result error">Error cargando documentos: ${error.message}</div>`;
    }
}

// Show multiple references result
function showMultipleReferencesResult(div, data) {
    let html = '<div class="result success">';
    html += '<strong>✓ Referencias procesadas exitosamente</strong>';
    html += `<p style="margin-top: 10px;"><strong>Total:</strong> ${data.total} | <strong>Procesadas:</strong> ${data.processed} | <strong>Fallidas:</strong> ${data.failed}</p>`;
    
    if (data.documents && data.documents.length > 0) {
        html += '<div class="result-info" style="margin-top: 15px;">';
        html += '<h3>Documentos creados:</h3>';
        data.documents.forEach(doc => {
            html += '<div style="margin: 10px 0; padding: 10px; background: white; border-left: 3px solid #667eea; border-radius: 3px;">';
            html += `<p><strong>Documento #${doc.numero_doc}</strong></p>`;
            if (doc.titulo_original) {
                html += `<p><strong>Título:</strong> ${doc.titulo_original.substring(0, 100)}${doc.titulo_original.length > 100 ? '...' : ''}</p>`;
            }
            if (doc.autores) {
                html += `<p><strong>Autores:</strong> ${doc.autores}</p>`;
            }
            if (doc.ano) {
                html += `<p><strong>Año:</strong> ${doc.ano}</p>`;
            }
            html += '</div>';
        });
        html += '</div>';
    }
    
    html += '</div>';
    div.innerHTML = html;
    div.className = 'result success';
}

// References PDF Upload
document.getElementById('references-pdf-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData();
    const fileInput = document.getElementById('references-pdf-file');
    const resultDiv = document.getElementById('references-pdf-result');

    if (!fileInput.files[0]) {
        showResult(resultDiv, 'Por favor selecciona un archivo PDF', 'error');
        return;
    }

    formData.append('file', fileInput.files[0]);
    resultDiv.innerHTML = '<div class="loading">Extrayendo referencias del PDF...</div>';
    resultDiv.className = 'result';

    try {
        const response = await fetch(`${API_BASE}/upload-references-pdf`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (response.ok && data.success) {
            showMultipleReferencesResult(resultDiv, data);
            fileInput.value = ''; // Reset form
        } else {
            showResult(resultDiv, data.detail || 'Error procesando PDF de referencias', 'error');
        }
    } catch (error) {
        showResult(resultDiv, `Error: ${error.message}`, 'error');
    }
});

// Download data
function downloadData(format) {
    window.location.href = `${API_BASE}/download/${format}`;
}


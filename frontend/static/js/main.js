// Configurar API_BASE según el entorno
// En producción (CloudFront/AWS), usar la URL completa del API Gateway
// En desarrollo local, usar vacío porque FastAPI ya tiene el prefijo /api en los routers
const API_BASE = window.location.hostname.includes('cloudfront.net') || window.location.hostname.includes('amazonaws.com')
    ? 'https://rv11r9yo98.execute-api.us-east-1.amazonaws.com/sandbox'
    : '';

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
        showResult(resultDiv, 'Por favor selecciona al menos un archivo PDF', 'error');
        return;
    }

    // Detectar si hay múltiples archivos
    const files = Array.from(fileInput.files);
    const hasMultiple = files.length > 1;
    
    console.log(`Archivos seleccionados: ${files.length}, Múltiples: ${hasMultiple}`);

    if (hasMultiple) {
        // Procesar múltiples PDFs
        // FastAPI requiere que todos los archivos tengan el mismo nombre de campo 'files'
        files.forEach(file => {
            formData.append('files', file);
        });
        
        resultDiv.innerHTML = `<div class="loading">Procesando ${files.length} PDFs...</div>`;
        resultDiv.className = 'result';

        try {
            const response = await fetch(`${API_BASE}/api/upload-multiple-pdfs`, {
                method: 'POST',
                body: formData
            });

            // Verificar si la respuesta es JSON
            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                const text = await response.text();
                console.error('Respuesta no JSON:', text);
                throw new Error(`Error del servidor: ${response.status} ${response.statusText}. Respuesta: ${text.substring(0, 200)}`);
            }

            const data = await response.json();

            if (response.ok && data.success) {
                showMultiplePDFsResult(resultDiv, data);
                fileInput.value = ''; // Reset form
            } else {
                showResult(resultDiv, data.detail || 'Error procesando PDFs', 'error');
            }
        } catch (error) {
            showResult(resultDiv, `Error: ${error.message}`, 'error');
        }
    } else {
        // Procesar un solo PDF usando S3 Presigned URLs (evita corrupción de archivos)
        const file = fileInput.files[0];
        resultDiv.innerHTML = '<div class="loading">Subiendo PDF a S3...</div>';
        resultDiv.className = 'result';

        try {
            // Paso 1: Obtener URL presignada
            const urlResponse = await fetch(`${API_BASE}/api/get-upload-url`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    filename: file.name,
                    content_type: 'application/pdf'
                })
            });

            if (!urlResponse.ok) {
                const errorData = await urlResponse.json();
                throw new Error(errorData.detail || 'Error obteniendo URL de upload');
            }

            const { upload_url, file_key } = await urlResponse.json();

            // Paso 2: Subir archivo directamente a S3
            resultDiv.innerHTML = '<div class="loading">Subiendo archivo...</div>';
            const uploadResponse = await fetch(upload_url, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/pdf',
                },
                body: file
            });

            if (!uploadResponse.ok) {
                throw new Error(`Error subiendo archivo: ${uploadResponse.status}`);
            }

            // Paso 3: Procesar PDF desde S3
            resultDiv.innerHTML = '<div class="loading">Extrayendo información del PDF...</div>';
            const processResponse = await fetch(`${API_BASE}/api/process-s3-pdf`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    file_key: file_key
                })
            });

            const contentType = processResponse.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                const text = await processResponse.text();
                console.error('Respuesta no JSON:', text);
                throw new Error(`Error del servidor: ${processResponse.status}. Respuesta: ${text.substring(0, 200)}`);
            }

            const data = await processResponse.json();

            if (processResponse.ok) {
                showPDFResult(resultDiv, data.document);
                fileInput.value = ''; // Reset form
            } else {
                showResult(resultDiv, data.detail || 'Error procesando PDF', 'error');
            }
        } catch (error) {
            showResult(resultDiv, `Error: ${error.message}`, 'error');
        }
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
            const response = await fetch(`${API_BASE}/api/upload-multiple-references`, {
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
            const response = await fetch(`${API_BASE}/api/upload-reference`, {
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
        const response = await fetch(`${API_BASE}/api/documents`);
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

function showMultiplePDFsResult(div, data) {
    let html = `<div class="success-message">
        <h3>✅ ${data.message}</h3>
        <p><strong>Total:</strong> ${data.total} PDFs | 
           <strong>Procesados:</strong> ${data.processed} | 
           <strong>Errores:</strong> ${data.failed}</p>
    </div>`;

    if (data.documents && data.documents.length > 0) {
        html += '<div class="documents-list"><h4>Documentos creados:</h4><ul>';
        data.documents.forEach(doc => {
            html += `<li>
                <strong>Documento #${doc.numero_doc}</strong><br>
                ${doc.titulo_original ? `Título: ${doc.titulo_original.substring(0, 100)}${doc.titulo_original.length > 100 ? '...' : ''}<br>` : ''}
                ${doc.autores ? `Autores: ${doc.autores}<br>` : ''}
                ${doc.ano ? `Año: ${doc.ano}` : ''}
            </li>`;
        });
        html += '</ul></div>';
    }

    if (data.errors && data.errors.length > 0) {
        html += '<div class="error-message"><h4>Errores:</h4><ul>';
        data.errors.forEach(error => {
            html += `<li>${error}</li>`;
        });
        html += '</ul></div>';
    }

    div.innerHTML = html;
    div.className = 'result success';
}

function showMultiplePDFsResult(div, data) {
    let html = '<div class="result success">';
    html += '<strong>✓ PDFs procesados exitosamente</strong>';
    html += `<p style="margin-top: 10px;"><strong>Total:</strong> ${data.total} | <strong>Procesados:</strong> ${data.processed} | <strong>Errores:</strong> ${data.failed}</p>`;
    
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
    
    if (data.errors && data.errors.length > 0) {
        html += '<div class="error-message" style="margin-top: 15px; padding: 10px; background: #fee; border-left: 3px solid #f00; border-radius: 3px;">';
        html += '<h4>Errores:</h4><ul>';
        data.errors.forEach(error => {
            html += `<li>${error}</li>`;
        });
        html += '</ul></div>';
    }
    
    html += '</div>';
    div.innerHTML = html;
    div.className = 'result success';
}

// References PDF Upload (usando S3 para evitar corrupción)
document.getElementById('references-pdf-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const fileInput = document.getElementById('references-pdf-file');
    const resultDiv = document.getElementById('references-pdf-result');

    if (!fileInput.files[0]) {
        showResult(resultDiv, 'Por favor selecciona un archivo PDF', 'error');
        return;
    }

    const file = fileInput.files[0];
    resultDiv.innerHTML = '<div class="loading">Subiendo PDF a S3...</div>';
    resultDiv.className = 'result';

    try {
        // Paso 1: Obtener URL presignada
        const urlResponse = await fetch(`${API_BASE}/api/get-upload-url`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                filename: file.name,
                content_type: 'application/pdf'
            })
        });

        if (!urlResponse.ok) {
            const errorData = await urlResponse.json();
            throw new Error(errorData.detail || 'Error obteniendo URL de upload');
        }

        const { upload_url, file_key } = await urlResponse.json();

        // Paso 2: Subir archivo directamente a S3
        resultDiv.innerHTML = '<div class="loading">Subiendo archivo...</div>';
        const uploadResponse = await fetch(upload_url, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/pdf',
            },
            body: file
        });

        if (!uploadResponse.ok) {
            throw new Error(`Error subiendo archivo: ${uploadResponse.status}`);
        }

        // Paso 3: Procesar referencias desde S3
        resultDiv.innerHTML = '<div class="loading">Extrayendo referencias del PDF...</div>';
        const response = await fetch(`${API_BASE}/api/process-s3-references-pdf`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                file_key: file_key
            })
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
    window.location.href = `${API_BASE}/api/download/${format}`;
}


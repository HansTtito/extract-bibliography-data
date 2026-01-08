// Configurar API_BASE según el entorno
// En producción (CloudFront/AWS), usar la URL completa del API Gateway
// En desarrollo local, usar vacío porque FastAPI ya tiene el prefijo /api en los routers
const API_BASE = window.location.hostname.includes('cloudfront.net') || window.location.hostname.includes('amazonaws.com')
    ? 'https://rv11r9yo98.execute-api.us-east-1.amazonaws.com/sandbox'
    : '';

// Funciones para manejar el banner de procesamiento
function showProcessingBanner(status, message, progress = 0) {
    const banner = document.getElementById('processing-banner');
    const bannerIcon = document.getElementById('banner-icon');
    const bannerText = document.getElementById('banner-text');
    const bannerProgress = document.getElementById('banner-progress');
    const body = document.body;
    
    if (!banner) {
        console.error('Banner element not found!');
        return;
    }
    
    console.log('Showing banner:', { status, message, progress });
    
    // Remover clases anteriores
    banner.classList.remove('analyzing', 'completed', 'error', 'show');
    
    // Configurar según estado
    let icon = '⏳';
    if (status === 'analyzing') {
        banner.classList.add('analyzing');
        icon = '🔍';
    } else if (status === 'completed') {
        banner.classList.add('completed');
        icon = '✅';
    } else if (status === 'failed' || status === 'error') {
        banner.classList.add('error');
        icon = '❌';
    } else {
        icon = '⏳';
    }
    
    if (bannerIcon) bannerIcon.textContent = icon;
    if (bannerText) bannerText.textContent = message;
    
    if (progress > 0) {
        if (bannerProgress) bannerProgress.textContent = `Progreso: ${progress}%`;
    } else {
        if (bannerProgress) bannerProgress.textContent = '';
    }
    
    // Forzar display block
    banner.style.display = 'block';
    banner.classList.add('show');
    body.classList.add('has-processing-banner');
    
    console.log('Banner should be visible now');
}

function updateProcessingBanner(message, progress = null) {
    const bannerText = document.getElementById('banner-text');
    const bannerProgress = document.getElementById('banner-progress');
    
    if (bannerText) {
        bannerText.textContent = message;
    }
    
    if (bannerProgress && progress !== null) {
        bannerProgress.textContent = `Progreso: ${progress}%`;
    }
}

function hideProcessingBanner() {
    const banner = document.getElementById('processing-banner');
    const body = document.body;
    
    if (banner) {
        banner.classList.remove('show');
    }
    body.classList.remove('has-processing-banner');
}

// Función para hacer fetch con reintentos automáticos
async function fetchWithRetry(url, options = {}, maxRetries = 3, retryDelay = 1000) {
    let lastError;
    
    for (let attempt = 0; attempt < maxRetries; attempt++) {
        let timeoutId;
        try {
            // Crear AbortController para timeout (compatible con navegadores más antiguos)
            const controller = new AbortController();
            timeoutId = setTimeout(() => controller.abort(), 30000); // 30 segundos
            
            const response = await fetch(url, {
                ...options,
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            // Si la respuesta es exitosa, retornarla
            if (response.ok) {
                return response;
            }
            
            // Si es un error 4xx (cliente), no reintentar
            if (response.status >= 400 && response.status < 500) {
                return response;
            }
            
            // Para errores 5xx (servidor) o de red, reintentar
            lastError = new Error(`HTTP ${response.status}: ${response.statusText}`);
            
        } catch (error) {
            // Limpiar timeout si aún está activo
            if (timeoutId) {
                clearTimeout(timeoutId);
            }
            
            lastError = error;
            
            // Si es un error de aborto (timeout), reintentar
            if (error.name === 'AbortError' || error.name === 'TimeoutError') {
                console.warn(`Intento ${attempt + 1}/${maxRetries} falló por timeout, reintentando...`);
            } else if (error.name === 'TypeError' && (error.message.includes('fetch') || error.message.includes('network'))) {
                // Error de red, reintentar
                console.warn(`Intento ${attempt + 1}/${maxRetries} falló por error de red: ${error.message}, reintentando...`);
            } else {
                // Otro tipo de error, no reintentar
                throw error;
            }
        }
        
        // Esperar antes del siguiente intento (backoff exponencial)
        if (attempt < maxRetries - 1) {
            const delay = retryDelay * Math.pow(2, attempt);
            await new Promise(resolve => setTimeout(resolve, delay));
        }
    }
    
    // Si todos los reintentos fallaron, lanzar el último error
    throw lastError || new Error('Error desconocido después de múltiples intentos');
}

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
        
        resultDiv.innerHTML = `<div class="loading">Subiendo ${files.length} PDFs a S3...</div>`;
        resultDiv.className = 'result';

        try {
            const results = [];
            let successCount = 0;
            let failCount = 0;

            for (let i = 0; i < files.length; i++) {
                const file = files[i];
                resultDiv.innerHTML = `<div class="loading">Procesando ${i + 1}/${files.length}: ${file.name}...</div>`;
                
                // Mostrar banner desde el inicio
                showProcessingBanner('processing', `📤 Preparando archivo ${i + 1}/${files.length}: ${file.name}`, 0);

                try {
                    // Paso 1: Obtener URL presignada (con reintentos)
                    showProcessingBanner('processing', `🔗 Obteniendo URL de subida... ${i + 1}/${files.length}: ${file.name}`, 5);
                    const urlResponse = await fetchWithRetry(`${API_BASE}/api/get-upload-url`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            filename: file.name,
                            content_type: 'application/pdf'
                        })
                    }, 3, 1000);

                    if (!urlResponse.ok) {
                        const errorData = await urlResponse.json().catch(() => ({}));
                        throw new Error(errorData.detail || 'Error obteniendo URL de upload');
                    }

                    const { upload_url, file_key } = await urlResponse.json();

                    // Paso 2: Subir a S3 (con reintentos, pero sin timeout muy corto para archivos grandes)
                    resultDiv.innerHTML = `<div class="loading">Subiendo ${i + 1}/${files.length}: ${file.name} a S3...</div>`;
                    showProcessingBanner('processing', `📤 Subiendo a S3... ${i + 1}/${files.length}: ${file.name}`, 15);
                    const uploadResponse = await fetchWithRetry(upload_url, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/pdf' },
                        body: file
                    }, 3, 2000); // Más tiempo entre reintentos para uploads

                    if (!uploadResponse.ok) {
                        throw new Error(`Error subiendo a S3: ${uploadResponse.status}`);
                    }

                    // Paso 3: Iniciar procesamiento asíncrono (con reintentos)
                    resultDiv.innerHTML = `<div class="loading">Iniciando procesamiento ${i + 1}/${files.length}: ${file.name}...</div>`;
                    showProcessingBanner('processing', `🚀 Iniciando procesamiento... ${i + 1}/${files.length}: ${file.name}`, 25);
                    const asyncResponse = await fetchWithRetry(`${API_BASE}/api/process-s3-pdf-async`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ file_key, filename: file.name })
                    }, 3, 1000);

                    if (!asyncResponse.ok) {
                        const errorData = await asyncResponse.json().catch(() => ({}));
                        throw new Error(errorData.detail || 'Error iniciando procesamiento');
                    }

                    const { job_id } = await asyncResponse.json();

                    // Paso 4: Hacer polling para obtener resultado
                    const result = await pollJobStatus(job_id, file.name, i + 1, files.length);
                    
                    if (result.success) {
                        results.push({ filename: file.name, success: true, document: result.document });
                        successCount++;
                    } else {
                        results.push({ filename: file.name, success: false, error: result.error });
                        failCount++;
                    }
                } catch (error) {
                    results.push({ filename: file.name, success: false, error: error.message });
                    failCount++;
                }
            }

            // Mostrar resultados
            showMultiplePDFsResult(resultDiv, { success: true, results, successCount, failCount, total: files.length });
            fileInput.value = ''; // Reset form
        } catch (error) {
            showResult(resultDiv, `Error: ${error.message}`, 'error');
        }
    } else {
        // Procesar un solo PDF usando S3 Presigned URLs (evita corrupción de archivos)
        const file = fileInput.files[0];
        resultDiv.innerHTML = '<div class="loading">Subiendo PDF a S3...</div>';
        resultDiv.className = 'result';
        
        // Mostrar banner desde el inicio
        showProcessingBanner('processing', `📤 Preparando archivo: ${file.name}`, 0);

        try {
            // Paso 1: Obtener URL presignada (con reintentos)
            showProcessingBanner('processing', `🔗 Obteniendo URL de subida... ${file.name}`, 5);
            const urlResponse = await fetchWithRetry(`${API_BASE}/api/get-upload-url`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    filename: file.name,
                    content_type: 'application/pdf'
                })
            }, 3, 1000);

            if (!urlResponse.ok) {
                const errorData = await urlResponse.json().catch(() => ({}));
                throw new Error(errorData.detail || 'Error obteniendo URL de upload');
            }

            const { upload_url, file_key } = await urlResponse.json();

            // Paso 2: Subir archivo directamente a S3 (con reintentos)
            resultDiv.innerHTML = '<div class="loading">Subiendo archivo...</div>';
            showProcessingBanner('processing', `📤 Subiendo a S3... ${file.name}`, 15);
            const uploadResponse = await fetchWithRetry(upload_url, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/pdf',
                },
                body: file
            }, 3, 2000); // Más tiempo entre reintentos para uploads

            if (!uploadResponse.ok) {
                throw new Error(`Error subiendo archivo: ${uploadResponse.status}`);
            }

            // Paso 3: Iniciar procesamiento asíncrono (con reintentos)
            resultDiv.innerHTML = '<div class="loading">Iniciando procesamiento...</div>';
            showProcessingBanner('processing', `🚀 Iniciando procesamiento... ${file.name}`, 25);
            const asyncResponse = await fetchWithRetry(`${API_BASE}/api/process-s3-pdf-async`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    file_key: file_key,
                    filename: file.name
                })
            }, 3, 1000);

            if (!asyncResponse.ok) {
                const errorData = await asyncResponse.json().catch(() => ({}));
                throw new Error(errorData.detail || 'Error iniciando procesamiento');
            }

            const { job_id } = await asyncResponse.json();
            
            // Paso 4: Hacer polling para obtener resultado
            const result = await pollJobStatus(job_id, file.name, 1, 1);

            if (result.success) {
                showPDFResult(resultDiv, result.document);
                fileInput.value = ''; // Reset form
            } else {
                hideProcessingBanner();
                showResult(resultDiv, result.error || 'Error procesando PDF', 'error');
            }
        } catch (error) {
            hideProcessingBanner();
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
            const response = await fetchWithRetry(`${API_BASE}/api/upload-multiple-references`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ references: lines })
            }, 3, 1000);

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
            const response = await fetchWithRetry(`${API_BASE}/api/upload-reference`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ reference_text: referenceText })
            }, 3, 1000);

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
        html += '<p style="color: #28a745; margin-top: 10px; font-weight: bold;">🌐 Información verificada y enriquecida con CrossRef</p>';
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
        html += `<p><strong>Revista/Publicación:</strong> ${document.lugar_publicacion_entrega}</p>`;
    }
    if (document.publicista_editorial) {
        html += `<p><strong>Editorial:</strong> ${document.publicista_editorial}</p>`;
    }
    if (document.volumen_edicion) {
        html += `<p><strong>Volumen:</strong> ${document.volumen_edicion}</p>`;
    }
    if (document.paginas) {
        html += `<p><strong>Páginas:</strong> ${document.paginas}</p>`;
    }
    if (document.doi) {
        html += `<p><strong>DOI:</strong> <a href="https://doi.org/${document.doi}" target="_blank">${document.doi}</a></p>`;
    }
    if (document.tipo_documento) {
        html += `<p><strong>Tipo:</strong> ${document.tipo_documento}</p>`;
    }
    if (document.peer_reviewed) {
        html += `<p><strong>Peer-reviewed:</strong> ${document.peer_reviewed}</p>`;
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
        // Solicitar hasta 1000 documentos para asegurar que se muestren todos
        const response = await fetchWithRetry(`${API_BASE}/api/documents?limit=1000`, {
            method: 'GET'
        }, 3, 1000);
        const documents = await response.json();

        if (documents.length === 0) {
            listDiv.innerHTML = '<div class="empty-state"><p>📄</p><p>No hay documentos extraídos aún</p></div>';
            return;
        }

        // Mostrar contador de documentos
        let html = `<div class="documents-count"><p><strong>Total de documentos: ${documents.length}</strong></p></div>`;
        
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
    let html = '<div class="result success">';
    html += '<strong>✓ PDFs procesados exitosamente</strong>';
    html += `<p style="margin-top: 10px;"><strong>Total:</strong> ${data.total} | <strong>Exitosos:</strong> ${data.successCount} | <strong>Errores:</strong> ${data.failCount}</p>`;
    
    if (data.results && data.results.length > 0) {
        // Separar exitosos de fallidos
        const successResults = data.results.filter(r => r.success);
        const failedResults = data.results.filter(r => !r.success);
        
        // Mostrar exitosos
        if (successResults.length > 0) {
            html += '<div class="result-info" style="margin-top: 15px;">';
            html += '<h3>Documentos creados:</h3>';
            successResults.forEach(result => {
                const doc = result.document;
                html += '<div style="margin: 10px 0; padding: 10px; background: white; border-left: 3px solid #667eea; border-radius: 3px;">';
                html += `<p><strong>${result.filename}</strong></p>`;
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
        
        // Mostrar errores
        if (failedResults.length > 0) {
            html += '<div class="error-message" style="margin-top: 15px; padding: 10px; background: #fee; border-left: 3px solid #f00; border-radius: 3px;">';
            html += '<h4>Errores:</h4><ul>';
            failedResults.forEach(result => {
                html += `<li><strong>${result.filename}:</strong> ${result.error}</li>`;
            });
            html += '</ul></div>';
        }
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
        // Paso 1: Obtener URL presignada (con reintentos)
        const urlResponse = await fetchWithRetry(`${API_BASE}/api/get-upload-url`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                filename: file.name,
                content_type: 'application/pdf'
            })
        }, 3, 1000);

        if (!urlResponse.ok) {
            const errorData = await urlResponse.json().catch(() => ({}));
            throw new Error(errorData.detail || 'Error obteniendo URL de upload');
        }

        const { upload_url, file_key } = await urlResponse.json();

        // Paso 2: Subir archivo directamente a S3 (con reintentos)
        resultDiv.innerHTML = '<div class="loading">Subiendo archivo...</div>';
        const uploadResponse = await fetchWithRetry(upload_url, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/pdf',
            },
            body: file
        }, 3, 2000); // Más tiempo entre reintentos para uploads

        if (!uploadResponse.ok) {
            throw new Error(`Error subiendo archivo: ${uploadResponse.status}`);
        }

        // Paso 3: Iniciar procesamiento asíncrono de referencias (con reintentos)
        resultDiv.innerHTML = '<div class="loading">Iniciando extracción de referencias...</div>';
        const processResponse = await fetchWithRetry(`${API_BASE}/api/process-s3-references-pdf-async`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                file_key: file_key,
                filename: file.name
            })
        }, 3, 1000);

        if (!processResponse.ok) {
            const errorData = await processResponse.json().catch(() => ({}));
            throw new Error(errorData.detail || 'Error iniciando procesamiento asíncrono');
        }

        const { job_id } = await processResponse.json();
        resultDiv.innerHTML = `<div class="loading">⏳ Extrayendo referencias del PDF (Job ID: ${job_id})...</div>`;

        // Paso 4: Polling para el estado del job
        await pollReferencesJobStatus(job_id, resultDiv, fileInput);
    } catch (error) {
        showResult(resultDiv, `Error: ${error.message}`, 'error');
    }
});

// Función para hacer polling del estado de un job
async function pollJobStatus(jobId, filename, currentIndex, totalFiles) {
    const maxAttempts = 300; // Máximo 5 minutos (300 * 1s)
    let attempts = 0;
    
    // Mostrar banner inicial
    showProcessingBanner('processing', `Procesando PDF ${currentIndex}/${totalFiles}: ${filename}`, 0);
    
    while (attempts < maxAttempts) {
        try {
            const response = await fetchWithRetry(`${API_BASE}/api/job-status/${jobId}`, {
                method: 'GET'
            }, 2, 500); // Menos reintentos para polling (ya es repetitivo)
            
            const job = await response.json();
            const progressPercent = job.progress || 0;
            
            // Determinar icono y mensaje según estado
            let status, statusText;
            if (job.status === 'analyzing') {
                status = 'analyzing';
                statusText = `🔍 Analizando contenido del PDF... ${currentIndex}/${totalFiles}: ${filename}`;
            } else if (job.status === 'processing') {
                status = 'processing';
                statusText = `⏳ Descargando PDF... ${currentIndex}/${totalFiles}: ${filename}`;
            } else if (job.status === 'completed') {
                status = 'completed';
                statusText = `✅ Procesamiento completado: ${filename}`;
            } else if (job.status === 'failed') {
                status = 'error';
                statusText = `❌ Error procesando: ${filename}`;
            } else {
                status = 'processing';
                statusText = `⏸️ Esperando procesamiento... ${currentIndex}/${totalFiles}: ${filename}`;
            }
            
            // Actualizar banner
            showProcessingBanner(status, statusText, progressPercent);
            
            // También actualizar el div de resultados (para compatibilidad)
            const progressDiv = document.getElementById('pdf-result');
            if (progressDiv) {
                progressDiv.innerHTML = `
                    <div class="loading">
                        <div style="margin-bottom: 10px; font-size: 16px;">
                            <strong>${statusText}</strong>
                        </div>
                        <div style="width: 100%; background-color: #f0f0f0; border-radius: 4px; overflow: hidden; margin-bottom: 8px; box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);">
                            <div style="width: ${progressPercent}%; background: linear-gradient(90deg, #4CAF50 0%, #45a049 100%); height: 24px; transition: width 0.5s ease; display: flex; align-items: center; justify-content: center; color: white; font-size: 12px; font-weight: bold;">
                                ${progressPercent}%
                            </div>
                        </div>
                        <div style="font-size: 14px; color: #666; margin-top: 5px;">
                            ${job.message || statusText}
                        </div>
                    </div>
                `;
            }
            
            if (job.status === 'completed') {
                // Mantener banner de éxito por 2 segundos
                setTimeout(() => hideProcessingBanner(), 2000);
                return { success: true, document: job.document };
            } else if (job.status === 'failed') {
                // Mantener banner de error por 5 segundos
                setTimeout(() => hideProcessingBanner(), 5000);
                return { success: false, error: job.error || 'Error desconocido' };
            }
            
            // Esperar 1 segundo antes del siguiente intento
            await new Promise(resolve => setTimeout(resolve, 1000));
            attempts++;
            
        } catch (error) {
            // Si es un error de red, esperar un poco más y continuar
            if (error.name === 'TypeError' && error.message.includes('fetch')) {
                console.warn(`Error de red en polling (intento ${attempts + 1}), reintentando...`);
                await new Promise(resolve => setTimeout(resolve, 2000)); // Esperar 2 segundos
                attempts++;
                continue;
            }
            hideProcessingBanner();
            return { success: false, error: error.message };
        }
    }
    
    // Timeout
    hideProcessingBanner();
    return { success: false, error: 'Tiempo de espera agotado. El procesamiento puede continuar en segundo plano.' };
}

// Función para hacer polling del estado de un job de referencias
async function pollReferencesJobStatus(jobId, resultDiv, fileInput) {
    const maxAttempts = 600; // Máximo 10 minutos (600 * 1s)
    let attempts = 0;
    
    // Mostrar banner inicial
    showProcessingBanner('processing', '🔍 Extrayendo referencias bibliográficas del PDF...', 0);
    
    const progressBarId = 'references-progress-bar';
    const statusMessageId = 'references-status-message';
    
    // Crear elementos de progreso si no existen
    if (!document.getElementById(progressBarId)) {
        resultDiv.innerHTML = `
            <div id="${statusMessageId}" class="loading">⏳ Extrayendo referencias...</div>
            <div class="progress-bar-container" style="margin-top: 10px;">
                <div class="progress-bar" id="${progressBarId}" style="width: 0%;"></div>
            </div>
        `;
    }
    
    while (attempts < maxAttempts) {
        try {
            const response = await fetchWithRetry(`${API_BASE}/api/job-status/${jobId}`, {
                method: 'GET'
            }, 2, 500); // Menos reintentos para polling
            
            if (!response.ok) {
                throw new Error('Error obteniendo estado del job');
            }
            
            const job = await response.json();
            const progressPercent = job.progress || 0;
            
            // Actualizar banner
            let status = 'processing';
            let statusText = '🔍 Extrayendo referencias bibliográficas...';
            
            if (job.status === 'completed') {
                status = 'completed';
                statusText = '✅ Referencias extraídas exitosamente';
            } else if (job.status === 'failed') {
                status = 'error';
                statusText = `❌ Error: ${job.error || 'Error desconocido'}`;
            } else if (job.status === 'processing') {
                statusText = '⏳ Procesando referencias...';
            }
            
            showProcessingBanner(status, statusText, progressPercent);
            
            // Actualizar barra de progreso
            const progressBar = document.getElementById(progressBarId);
            if (progressBar) {
                progressBar.style.width = `${job.progress}%`;
                progressBar.textContent = `${job.progress}%`;
            }
            
            // Actualizar mensaje de estado
            const statusMessage = document.getElementById(statusMessageId);
            if (statusMessage) {
                const statusIcon = job.status === 'pending' ? '⏳' : 
                                  job.status === 'processing' ? '⏳' : 
                                  job.status === 'analyzing' ? '🔍' : 
                                  job.status === 'completed' ? '✅' : 
                                  job.status === 'failed' ? '❌' : '⏸️';
                
                statusMessage.innerHTML = `
                    <span class="${job.status === 'completed' ? 'text-success' : job.status === 'failed' ? 'text-danger' : 'text-info'}">
                        ${statusIcon} ${job.message || 'Procesando...'}
                    </span>
                `;
            }
            
            if (job.status === 'completed') {
                // Mantener banner de éxito por 2 segundos
                setTimeout(() => hideProcessingBanner(), 2000);
                if (job.result && job.result.success) {
                    showMultipleReferencesResult(resultDiv, job.result);
                    fileInput.value = ''; // Reset form
                } else {
                    showResult(resultDiv, job.error || 'Error procesando referencias', 'error');
                }
                return;
            } else if (job.status === 'failed') {
                // Mantener banner de error por 5 segundos
                setTimeout(() => hideProcessingBanner(), 5000);
                showResult(resultDiv, job.error || 'Error procesando referencias', 'error');
                return;
            }
            
            // Esperar 1 segundo antes del siguiente intento
            await new Promise(resolve => setTimeout(resolve, 1000));
            attempts++;
            
        } catch (error) {
            // Si es un error de red, esperar un poco más y continuar
            if (error.name === 'TypeError' && error.message.includes('fetch')) {
                console.warn(`Error de red en polling (intento ${attempts + 1}), reintentando...`);
                await new Promise(resolve => setTimeout(resolve, 2000)); // Esperar 2 segundos
                attempts++;
                continue;
            }
            hideProcessingBanner();
            showResult(resultDiv, `Error de polling: ${error.message}`, 'error');
            console.error('Polling error:', error);
            return;
        }
    }
    
    // Timeout
    hideProcessingBanner();
    showResult(resultDiv, 'Tiempo de espera agotado. El procesamiento puede continuar en segundo plano.', 'warning');
}

// Download data
function downloadData(format) {
    window.location.href = `${API_BASE}/api/download/${format}`;
}


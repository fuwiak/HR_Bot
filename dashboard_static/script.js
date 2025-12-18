// Ретро Dashboard JavaScript

const API_BASE = '/api';

// Инициализация
document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    updateTime();
    setInterval(updateTime, 1000);
    refreshData();
    setInterval(refreshData, 30000); // Обновление каждые 30 секунд
    initParamsPanel();
    initClickSounds();
});

// Обновление времени
function updateTime() {
    const now = new Date();
    const timeStr = now.toLocaleTimeString('ru-RU');
    const timeEl = document.getElementById('current-time');
    if (timeEl) {
        timeEl.textContent = timeStr;
    }
}

// Управление вкладками
function initTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabId = btn.getAttribute('data-tab');
            switchTab(tabId);
        });
    });
}

function switchTab(tabId) {
    // Убираем активный класс со всех вкладок
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    
    // Добавляем активный класс к выбранной вкладке
    document.querySelector(`[data-tab="${tabId}"]`).classList.add('active');
    document.getElementById(tabId).classList.add('active');
    
    // Загружаем данные для вкладки
    if (tabId === 'vectordb') {
        loadVectorDBInfo();
        loadSources();
    } else if (tabId === 'metrics') {
        loadMetrics();
        loadMetricsHistory();
    } else if (tabId === 'files') {
        loadFiles();
    }
}

// Загрузка данных
async function refreshData() {
    await refreshAllData();
}

async function loadVectorDBInfo() {
    try {
        const response = await fetch(`${API_BASE}/vectordb/info`);
        const data = await response.json();
        
        document.getElementById('vectordb-status').textContent = data.status.toUpperCase();
        document.getElementById('vectordb-count').textContent = data.points_count.toLocaleString();
        document.getElementById('collection-name').textContent = data.collection_name;
        document.getElementById('points-count').textContent = data.points_count.toLocaleString();
        document.getElementById('vectors-count').textContent = data.vectors_count.toLocaleString();
        document.getElementById('collection-status').textContent = data.status.toUpperCase();
    } catch (error) {
        console.error('Error loading vector DB info:', error);
        document.getElementById('vectordb-status').textContent = 'ERROR';
    }
}

async function loadSources() {
    try {
        const response = await fetch(`${API_BASE}/vectordb/sources`);
        const sources = await response.json();
        
        const sourcesList = document.getElementById('sources-list');
        if (sources.length === 0) {
            sourcesList.innerHTML = '<div class="loading">Нет источников в базе данных</div>';
            return;
        }
        
        sourcesList.innerHTML = sources.map(source => `
            <div class="source-item">
                <div class="source-info">
                    <div class="source-name">${escapeHtml(source.source_url)}</div>
                    <div class="source-meta">
                        ${source.file_name || ''} | ${source.document_type || ''}
                    </div>
                </div>
                <div style="display: flex; align-items: center; gap: 10px;">
                    <div class="source-chunks">${source.chunks_count}</div>
                    <button class="retro-btn" style="padding: 5px 10px; font-size: 14px;" 
                            onclick="deleteSource('${escapeHtml(source.source_url)}')" 
                            title="Удалить источник">
                        🗑️
                    </button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading sources:', error);
        document.getElementById('sources-list').innerHTML = 
            '<div class="loading">Ошибка загрузки источников</div>';
    }
}

async function loadLatestMetrics() {
    try {
        const response = await fetch(`${API_BASE}/metrics/latest`);
        const metrics = await response.json();
        
        if (!metrics) {
            document.getElementById('last-eval-time').textContent = 'Нет данных';
            document.getElementById('precision-k').textContent = '-';
            return;
        }
        
        const date = new Date(metrics.timestamp);
        document.getElementById('last-eval-time').textContent = 
            date.toLocaleString('ru-RU');
        document.getElementById('precision-k').textContent = 
            metrics.precision_at_k_overall.toFixed(3);
    } catch (error) {
        console.error('Error loading latest metrics:', error);
    }
}

async function loadMetrics() {
    try {
        const response = await fetch(`${API_BASE}/metrics/latest`);
        const metrics = await response.json();
        
        if (!metrics) {
            document.getElementById('metric-precision-regulated').textContent = '-';
            document.getElementById('metric-precision-general').textContent = '-';
            document.getElementById('metric-mrr').textContent = '-';
            document.getElementById('metric-groundedness').textContent = '-';
            document.getElementById('metric-halucination').textContent = '-';
            return;
        }
        
        updateMetric('metric-precision-regulated', metrics.precision_at_k_regulated, 0.85);
        updateMetric('metric-precision-general', metrics.precision_at_k_general, 0.75);
        updateMetric('metric-mrr', metrics.mrr_overall, 0.9);
        updateMetric('metric-groundedness', metrics.groundedness_overall, 0.9);
        updateMetric('metric-halucination', metrics.halucination_rate_overall * 100, 10, true);
    } catch (error) {
        console.error('Error loading metrics:', error);
    }
}

function updateMetric(elementId, value, target, reverse = false) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    const formatted = typeof value === 'number' ? value.toFixed(3) : value;
    element.textContent = formatted;
    
    // Проверяем целевое значение
    const pass = reverse ? value <= target : value >= target;
    element.className = `metric-value ${pass ? 'pass' : 'fail'}`;
}

async function loadMetricsHistory() {
    try {
        const response = await fetch(`${API_BASE}/metrics/history`);
        const history = await response.json();
        
        const chartEl = document.getElementById('history-chart');
        if (history.length === 0) {
            chartEl.innerHTML = '<div class="loading">Нет истории метрик</div>';
            return;
        }
        
        // Простая визуализация истории
        chartEl.innerHTML = `
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                ${history.map(item => `
                    <div style="background: var(--bg-secondary); border: 1px solid var(--border-color); padding: 15px;">
                        <div style="color: var(--text-muted); font-size: 12px; margin-bottom: 10px;">
                            ${new Date(item.timestamp).toLocaleString('ru-RU')}
                        </div>
                        <div style="color: var(--text-primary); font-size: 14px;">
                            Precision@K: ${item.precision_at_k_overall.toFixed(3)}<br>
                            MRR: ${item.mrr_overall.toFixed(3)}<br>
                            Groundedness: ${item.groundedness_overall.toFixed(3)}<br>
                            Halucination: ${(item.halucination_rate_overall * 100).toFixed(1)}%
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    } catch (error) {
        console.error('Error loading metrics history:', error);
        document.getElementById('history-chart').innerHTML = 
            '<div class="loading">Ошибка загрузки истории</div>';
    }
}

async function loadFiles() {
    try {
        const response = await fetch(`${API_BASE}/vectordb/sources`);
        const sources = await response.json();
        
        const filesList = document.getElementById('files-list');
        const fileSources = sources.filter(s => s.source_url.startsWith('file://'));
        
        if (fileSources.length === 0) {
            filesList.innerHTML = '<div class="loading">Нет загруженных файлов</div>';
            return;
        }
        
        filesList.innerHTML = fileSources.map(source => `
            <div class="file-item">
                <div>
                    <div style="color: var(--text-primary); font-size: 18px;">
                        ${escapeHtml(source.file_name || source.source_url)}
                    </div>
                    <div style="color: var(--text-muted); font-size: 14px; margin-top: 5px;">
                        ${source.document_type || 'unknown'} | ${source.chunks_count} чанков
                    </div>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading files:', error);
        document.getElementById('files-list').innerHTML = 
            '<div class="loading">Ошибка загрузки файлов</div>';
    }
}

// Workflow функции
async function runEvaluation() {
    if (!confirm('Запустить оценку RAG системы? Это может занять несколько минут.')) {
        return;
    }
    
    const btn = event.target;
    const originalText = btn.textContent;
    btn.textContent = '⏳ ВЫПОЛНЯЕТСЯ...';
    btn.disabled = true;
    
    try {
        const response = await fetch(`${API_BASE}/workflow/evaluate`, {
            method: 'POST'
        });
        const result = await response.json();
        
        if (result.success) {
            alert(`Оценка завершена!\n\nPrecision@K: ${result.metrics.precision_at_k_overall.toFixed(3)}\nMRR: ${result.metrics.mrr_overall.toFixed(3)}`);
            loadMetrics();
            loadMetricsHistory();
        } else {
            alert('Ошибка при выполнении оценки');
        }
    } catch (error) {
        console.error('Error running evaluation:', error);
        alert('Ошибка при выполнении оценки: ' + error.message);
    } finally {
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

function loadPDF() {
    document.getElementById('file-input').click();
}

function loadExcel() {
    document.getElementById('file-input').click();
}

async function handleFileSelect(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch(`${API_BASE}/workflow/load-pdf`, {
            method: 'POST',
            body: formData
        });
        const result = await response.json();
        
        if (result.success) {
            // Показываем уведомление о начале обработки
            showNotification('Файл принят, обработка началась...', 'info');
            
            // Начинаем отслеживание статуса задачи
            pollTaskStatus(result.task_id, () => {
                showNotification('Файл успешно загружен!', 'success');
                refreshAllData();
            });
        } else {
            showNotification('Ошибка при загрузке файла', 'error');
        }
    } catch (error) {
        console.error('Error uploading file:', error);
        showNotification('Ошибка при загрузке файла: ' + error.message, 'error');
    }
    
    // Сбрасываем input
    event.target.value = '';
}

function pollTaskStatus(taskId, onComplete) {
    const maxAttempts = 300; // Максимум 5 минут (300 * 1 секунда)
    let attempts = 0;
    
    const checkStatus = async () => {
        try {
            const response = await fetch(`${API_BASE}/workflow/task-status/${taskId}`);
            const status = await response.json();
            
            if (status.status === 'completed') {
                onComplete();
                return;
            } else if (status.status === 'error') {
                showNotification('Ошибка обработки: ' + status.message, 'error');
                return;
            } else if (status.status === 'processing') {
                // Продолжаем проверку
                attempts++;
                if (attempts < maxAttempts) {
                    setTimeout(checkStatus, 1000); // Проверяем каждую секунду
                } else {
                    showNotification('Таймаут ожидания обработки', 'error');
                }
            } else {
                // pending - продолжаем проверку
                attempts++;
                if (attempts < maxAttempts) {
                    setTimeout(checkStatus, 1000);
                }
            }
        } catch (error) {
            console.error('Error checking task status:', error);
            showNotification('Ошибка проверки статуса задачи', 'error');
        }
    };
    
    // Начинаем проверку через 1 секунду
    setTimeout(checkStatus, 1000);
}

function showNotification(message, type = 'info') {
    // Простое уведомление через alert (можно заменить на более красивое)
    if (type === 'error') {
        alert('❌ ' + message);
    } else if (type === 'success') {
        alert('✅ ' + message);
    } else {
        alert('ℹ️ ' + message);
    }
}

async function scrapeWebsites() {
    if (!confirm('Запустить скрапинг сайтов из whitelist? Это может занять несколько минут.')) {
        return;
    }
    
    const btn = event.target;
    const originalText = btn.textContent;
    btn.textContent = '⏳ ЗАПУСК...';
    btn.disabled = true;
    
    try {
        const response = await fetch(`${API_BASE}/workflow/scrape`, {
            method: 'POST'
        });
        const result = await response.json();
        
        if (result.success) {
            showNotification('Скрапинг начат, обработка в фоне...', 'info');
            btn.textContent = '⏳ В ПРОЦЕССЕ...';
            
            // Отслеживаем статус задачи
            pollTaskStatus(result.task_id, () => {
                showNotification('Скрапинг завершен!', 'success');
                btn.textContent = originalText;
                btn.disabled = false;
                refreshAllData();
            });
        } else {
            showNotification('Ошибка при запуске скрапинга: ' + (result.message || 'Неизвестная ошибка'), 'error');
            btn.textContent = originalText;
            btn.disabled = false;
        }
    } catch (error) {
        console.error('Error scraping websites:', error);
        showNotification('Ошибка при скрапинге: ' + error.message, 'error');
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

async function deleteSource(sourceUrl) {
    if (!confirm(`Удалить источник "${sourceUrl}"?\n\nВсе документы из этого источника будут удалены.`)) {
        return;
    }
    
    try {
        const encodedUrl = encodeURIComponent(sourceUrl);
        const response = await fetch(`${API_BASE}/vectordb/sources/${encodedUrl}`, {
            method: 'DELETE'
        });
        const result = await response.json();
        
        if (result.success) {
            alert(`Источник удален!\n\nУдалено документов: ${result.deleted_points}`);
            // Автоматически обновляем все данные
            await refreshAllData();
        } else {
            alert('Ошибка при удалении: ' + (result.message || 'Неизвестная ошибка'));
        }
    } catch (error) {
        console.error('Error deleting source:', error);
        alert('Ошибка при удалении источника: ' + error.message);
    }
}

async function refreshAllData() {
    // Обновляем все данные после операций
    await loadVectorDBInfo();
    await loadSources();
    await loadFiles();
    await loadLatestMetrics();
    
    // Если на вкладке метрик - обновляем их тоже
    if (document.getElementById('metrics').classList.contains('active')) {
        await loadMetrics();
        await loadMetricsHistory();
    }
}

async function testQuery() {
    const query = document.getElementById('test-query-input').value.trim();
    if (!query) {
        alert('Введите вопрос');
        return;
    }
    
    const resultEl = document.getElementById('test-result');
    resultEl.innerHTML = '<div class="loading">Выполнение запроса...</div>';
    
    try {
        const response = await fetch(`${API_BASE}/test/query?query=${encodeURIComponent(query)}`);
        const result = await response.json();
        
        resultEl.innerHTML = `
            <div class="result-answer">${escapeHtml(result.answer)}</div>
            ${result.sources && result.sources.length > 0 ? `
                <div class="result-sources">
                    <strong>Источники:</strong>
                    ${result.sources.map(s => `<div class="result-source">${escapeHtml(s)}</div>`).join('')}
                </div>
            ` : ''}
            <div class="result-meta">
                Provider: ${result.provider} | Model: ${result.model}<br>
                Confidence: ${result.confidence?.toFixed(3) || 'N/A'} | 
                Context docs: ${result.context_count || 0}
            </div>
        `;
    } catch (error) {
        console.error('Error testing query:', error);
        resultEl.innerHTML = '<div class="loading">Ошибка при выполнении запроса</div>';
    }
}

function exportResults() {
    alert('Функция экспорта в разработке');
}

// ========== ПАНЕЛЬ ПАРАМЕТРОВ ==========

// Инициализация панели параметров
async function initParamsPanel() {
    // Загружаем текущие параметры
    try {
        const response = await fetch(`${API_BASE}/parameters`);
        const params = await response.json();
        
        // Устанавливаем значения слайдеров
        document.getElementById('chunk-size').value = params.chunk_size;
        document.getElementById('chunk-overlap').value = params.chunk_overlap;
        document.getElementById('top-k').value = params.top_k;
        document.getElementById('min-score').value = params.min_score;
        document.getElementById('temperature').value = params.temperature;
        document.getElementById('max-tokens').value = params.max_tokens;
        
        // Обновляем отображаемые значения
        updateParamValues();
    } catch (error) {
        console.error('Error loading parameters:', error);
    }
    
    // Добавляем обработчики для слайдеров
    const sliders = document.querySelectorAll('.param-slider');
    sliders.forEach(slider => {
        slider.addEventListener('input', () => {
            updateParamValue(slider.id);
            playClickSound();
        });
    });
}

// Переключение видимости панели
function toggleParamsPanel() {
    const panel = document.getElementById('params-panel');
    panel.classList.toggle('expanded');
    playClickSound();
}

// Обновление значения одного параметра
function updateParamValue(sliderId) {
    const slider = document.getElementById(sliderId);
    const value = parseFloat(slider.value);
    let displayValue = value;
    
    // Форматирование для отображения
    if (sliderId === 'min-score' || sliderId === 'temperature') {
        displayValue = value.toFixed(2);
    } else {
        displayValue = Math.round(value);
    }
    
    // Обновляем отображаемое значение
    const valueElement = document.getElementById(sliderId + '-value');
    if (valueElement) {
        valueElement.textContent = displayValue;
    }
}

// Обновление всех значений параметров
function updateParamValues() {
    updateParamValue('chunk-size');
    updateParamValue('chunk-overlap');
    updateParamValue('top-k');
    updateParamValue('min-score');
    updateParamValue('temperature');
    updateParamValue('max-tokens');
}

// Применение параметров
async function applyParameters() {
    playClickSound();
    
    const params = {
        chunk_size: parseInt(document.getElementById('chunk-size').value),
        chunk_overlap: parseInt(document.getElementById('chunk-overlap').value),
        top_k: parseInt(document.getElementById('top-k').value),
        min_score: parseFloat(document.getElementById('min-score').value),
        temperature: parseFloat(document.getElementById('temperature').value),
        max_tokens: parseInt(document.getElementById('max-tokens').value),
    };
    
    try {
        const response = await fetch(`${API_BASE}/parameters`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(params),
        });
        
        if (response.ok) {
            const result = await response.json();
            showNotification('✅ Параметры применены! Теперь можно протестировать запросы и запустить оценку для проверки метрик.', 'success');
        } else {
            const error = await response.json();
            showNotification('❌ Ошибка при применении параметров: ' + error.detail, 'error');
        }
    } catch (error) {
        console.error('Error applying parameters:', error);
        showNotification('❌ Ошибка при применении параметров: ' + error.message, 'error');
    }
}

// Сброс параметров к значениям по умолчанию
async function resetParameters() {
    playClickSound();
    
    try {
        const response = await fetch(`${API_BASE}/parameters`);
        const params = await response.json();
        
        // Устанавливаем значения слайдеров
        document.getElementById('chunk-size').value = params.chunk_size;
        document.getElementById('chunk-overlap').value = params.chunk_overlap;
        document.getElementById('top-k').value = params.top_k;
        document.getElementById('min-score').value = params.min_score;
        document.getElementById('temperature').value = params.temperature;
        document.getElementById('max-tokens').value = params.max_tokens;
        
        // Обновляем отображаемые значения
        updateParamValues();
        
        showNotification('🔄 Параметры сброшены к значениям из config.yaml', 'info');
    } catch (error) {
        console.error('Error resetting parameters:', error);
        showNotification('❌ Ошибка при сбросе параметров: ' + error.message, 'error');
    }
}

// ========== ЗВУКИ AMIGA ==========

// Инициализация звуков при клике
function initClickSounds() {
    // Добавляем обработчики клика ко всем кнопкам и слайдерам
    const buttons = document.querySelectorAll('button, .tab-btn, .retro-btn');
    buttons.forEach(btn => {
        btn.addEventListener('click', () => {
            playClickSound();
        });
    });
    
    // Звук при изменении слайдеров уже добавлен в initParamsPanel
}

// Воспроизведение звука клика (Amiga-style)
function playClickSound() {
    try {
        // Создаем простой звук клика через Web Audio API (Amiga-style)
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        // Amiga-style звук: короткий писк
        oscillator.frequency.setValueAtTime(800, audioContext.currentTime);
        oscillator.frequency.exponentialRampToValueAtTime(400, audioContext.currentTime + 0.05);
        
        gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.05);
        
        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.05);
    } catch (error) {
        // Если Web Audio API не поддерживается, игнорируем
        console.debug('Audio not supported:', error);
    }
}

// Утилиты
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Enter для тестового запроса
document.addEventListener('DOMContentLoaded', () => {
    const input = document.getElementById('test-query-input');
    if (input) {
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                testQuery();
            }
        });
    }
});


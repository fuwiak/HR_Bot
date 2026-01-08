'use client'

import { useState, useEffect } from 'react'
import {
  testRAGQuery,
  runRAGEvaluation,
  loadPDF,
  scrapeWebsites,
  getRAGStats,
  getRAGMetrics,
  getRAGParameters,
  updateRAGParameters,
} from '@/lib/api'
import styles from './page.module.css'

export default function RAGDashboardPage() {
  const [activeTab, setActiveTab] = useState('overview')
  const [testQuery, setTestQuery] = useState('')
  const [testResult, setTestResult] = useState<any>(null)
  const [stats, setStats] = useState<any>(null)
  const [metrics, setMetrics] = useState<any>(null)
  const [params, setParams] = useState({
    chunk_size: 500,
    chunk_overlap: 50,
    top_k: 10,
    min_score: 0.3,
    temperature: 0.7,
    max_tokens: 2048,
  })
  const [paramsPanelCollapsed, setParamsPanelCollapsed] = useState(true)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [statsData, metricsData, paramsData] = await Promise.all([
        getRAGStats().catch(() => null),
        getRAGMetrics().catch(() => null),
        getRAGParameters().catch(() => null),
      ])
      if (statsData) setStats(statsData)
      if (metricsData?.parameters) setParams(metricsData.parameters)
      if (paramsData?.parameters) setParams(paramsData.parameters)
      if (metricsData?.metrics) setMetrics(metricsData.metrics)
    } catch (error) {
      console.error('Error loading data:', error)
    }
  }

  const handleTestQuery = async () => {
    if (!testQuery.trim()) return
    try {
      const result = await testRAGQuery(testQuery, 5)
      setTestResult(result)
    } catch (error: any) {
      setTestResult({ error: error.message })
    }
  }

  const handleRunEvaluation = async () => {
    if (!confirm('Запустить оценку RAG системы? Это может занять некоторое время.')) return
    try {
      await runRAGEvaluation()
      alert('Оценка запущена! Результаты появятся после завершения.')
      setTimeout(loadData, 2000)
    } catch (error: any) {
      alert('Ошибка: ' + error.message)
    }
  }

  const handleLoadPDF = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      const result = await loadPDF(file)
      alert(`Файл загружен!\nЧанков: ${result.chunks_count}`)
      loadData()
    } catch (error: any) {
      alert('Ошибка: ' + error.message)
    }
  }

  const handleScrape = async () => {
    if (!confirm('Запустить скрапинг сайтов из whitelist?')) return
    try {
      const result = await scrapeWebsites()
      alert(`Скрапинг завершен!\nЗагружено страниц: ${result.pages_loaded}`)
      loadData()
    } catch (error: any) {
      alert('Ошибка: ' + error.message)
    }
  }

  const handleApplyParams = async () => {
    try {
      await updateRAGParameters(params)
      alert('Параметры применены!')
    } catch (error: any) {
      alert('Ошибка: ' + error.message)
    }
  }

  return (
    <div className={styles.ragDashboard}>
      <div className={styles.dashboardHeader}>
        <h1>
          <span>📚</span>
          HR2137 RAG Dashboard v1.0
        </h1>
        <div className={styles.status}>Система управления базой знаний | Status: ONLINE</div>
      </div>

      {/* Tabs */}
      <div className={styles.tabs}>
        {[
          { id: 'overview', label: '📊 ОБЗОР' },
          { id: 'vectordb', label: '🗄️ ВЕКТОРНАЯ БД' },
          { id: 'metrics', label: '📈 МЕТРИКИ' },
          { id: 'workflow', label: '⚙️ WORKFLOW' },
          { id: 'files', label: '📁 ФАЙЛЫ' },
          { id: 'test', label: '🧪 ТЕСТ' },
        ].map(tab => (
          <button
            key={tab.id}
            className={`${styles.tabBtn} ${activeTab === tab.id ? styles.active : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className={styles.tabContent}>
          <div className={styles.panel}>
            <h2 className={styles.panelTitle}>СИСТЕМНЫЙ СТАТУС</h2>
            <div className={styles.statusGrid}>
              <div className={styles.statusCard}>
                <div className={styles.statusLabel}>Векторная БД</div>
                <div className={styles.statusValue}>{stats?.status || 'Загрузка...'}</div>
              </div>
              <div className={styles.statusCard}>
                <div className={styles.statusLabel}>Документов</div>
                <div className={styles.statusValue}>{stats?.points_count || '-'}</div>
              </div>
              <div className={styles.statusCard}>
                <div className={styles.statusLabel}>Последняя оценка</div>
                <div className={styles.statusValue}>
                  {metrics?.timestamp ? new Date(metrics.timestamp).toLocaleString('ru-RU') : '-'}
                </div>
              </div>
              <div className={styles.statusCard}>
                <div className={styles.statusLabel}>Precision@K</div>
                <div className={styles.statusValue}>
                  {metrics?.metrics?.precision_at_k_overall?.toFixed(2) || '-'}
                </div>
              </div>
            </div>
          </div>

          <div className={styles.panel}>
            <h2 className={styles.panelTitle}>БЫСТРЫЕ ДЕЙСТВИЯ</h2>
            <div className={styles.buttonGrid}>
              <button className={`${styles.btn} ${styles.btnSecondary}`} onClick={handleRunEvaluation}>
                ▶ ЗАПУСТИТЬ ОЦЕНКУ
              </button>
              <button className={`${styles.btn} ${styles.btnSecondary}`} onClick={() => document.getElementById('file-input')?.click()}>
                📄 ЗАГРУЗИТЬ PDF
              </button>
              <button className={`${styles.btn} ${styles.btnSecondary}`} onClick={handleScrape}>
                🌐 СКРАПИТЬ САЙТЫ
              </button>
              <button className={styles.btn} onClick={loadData}>🔄 ОБНОВИТЬ</button>
              <button className={styles.btn} onClick={() => setActiveTab('test')}>🧪 ТЕСТОВЫЙ ЗАПРОС</button>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'vectordb' && (
        <div className={styles.tabContent}>
          <div className={styles.panel}>
            <h2 className={styles.panelTitle}>ИНФОРМАЦИЯ О ВЕКТОРНОЙ БД</h2>
            <div className={styles.infoTable}>
              <div className={styles.infoRow}>
                <span className={styles.infoLabel}>Коллекция:</span>
                <span className={styles.infoValue}>{stats?.collection_name || '-'}</span>
              </div>
              <div className={styles.infoRow}>
                <span className={styles.infoLabel}>Документов:</span>
                <span className={styles.infoValue}>{stats?.points_count || '-'}</span>
              </div>
              <div className={styles.infoRow}>
                <span className={styles.infoLabel}>Векторов:</span>
                <span className={styles.infoValue}>{stats?.vectors_count || '-'}</span>
              </div>
              <div className={styles.infoRow}>
                <span className={styles.infoLabel}>Статус:</span>
                <span className={styles.infoValue}>{stats?.status || '-'}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'metrics' && metrics && (
        <div className={styles.tabContent}>
          <div className={styles.panel}>
            <h2 className={styles.panelTitle}>ТЕКУЩИЕ МЕТРИКИ RAG</h2>
            <div className={styles.metricsGrid}>
              <div className={styles.metricCard}>
                <div className={styles.metricLabel}>Precision@K (Общие)</div>
                <div className={styles.metricValue}>
                  {metrics.metrics?.precision_at_k_overall?.toFixed(2) || '-'}
                </div>
                <div className={styles.metricTarget}>Цель: ≥0.75</div>
              </div>
              <div className={styles.metricCard}>
                <div className={styles.metricLabel}>MRR</div>
                <div className={styles.metricValue}>
                  {metrics.metrics?.mrr_overall?.toFixed(2) || '-'}
                </div>
                <div className={styles.metricTarget}>Цель: ≥0.9</div>
              </div>
              <div className={styles.metricCard}>
                <div className={styles.metricLabel}>Groundedness</div>
                <div className={styles.metricValue}>
                  {metrics.metrics?.groundedness_overall?.toFixed(2) || '-'}
                </div>
                <div className={styles.metricTarget}>Цель: ≥0.9</div>
              </div>
              <div className={styles.metricCard}>
                <div className={styles.metricLabel}>Halucination Rate</div>
                <div className={styles.metricValue}>
                  {metrics.metrics?.halucination_rate_overall 
                    ? `${(metrics.metrics.halucination_rate_overall * 100).toFixed(1)}%`
                    : '-'}
                </div>
                <div className={styles.metricTarget}>Цель: ≤10%</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'workflow' && (
        <div className={styles.tabContent}>
          <div className={styles.panel}>
            <h2 className={styles.panelTitle}>УПРАВЛЕНИЕ WORKFLOW</h2>
            <div style={{ display: 'grid', gap: '30px' }}>
              <div>
                <h3 style={{ marginBottom: '15px' }}>1. Загрузка данных</h3>
                <div style={{ display: 'flex', gap: '10px' }}>
                  <button className={`${styles.btn} ${styles.btnSecondary}`} onClick={() => document.getElementById('file-input')?.click()}>
                    Загрузить PDF
                  </button>
                  <button className={`${styles.btn} ${styles.btnSecondary}`}>
                    Загрузить Excel
                  </button>
                </div>
              </div>
              <div>
                <h3 style={{ marginBottom: '15px' }}>2. Оценка качества</h3>
                <div>
                  <button className={`${styles.btn} ${styles.btnSecondary}`} onClick={handleRunEvaluation}>
                    Запустить оценку RAG
                  </button>
                  <div style={{ marginTop: '10px', fontSize: '13px', color: '#65676b' }}>
                    Оценка использует Ground-Truth QA набор для проверки метрик
                  </div>
                </div>
              </div>
              <div>
                <h3 style={{ marginBottom: '15px' }}>3. Анализ результатов</h3>
                <div style={{ display: 'flex', gap: '10px' }}>
                  <button className={styles.btn} onClick={() => setActiveTab('metrics')}>
                    Просмотр метрик
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'files' && (
        <div className={styles.tabContent}>
          <div className={styles.panel}>
            <h2 className={styles.panelTitle}>УПРАВЛЕНИЕ ФАЙЛАМИ</h2>
            <div className={styles.fileUploadArea}>
              <input
                type="file"
                id="file-input"
                accept=".pdf,.xlsx,.xls"
                style={{ display: 'none' }}
                onChange={handleLoadPDF}
              />
              <div className={styles.uploadBox} onClick={() => document.getElementById('file-input')?.click()}>
                <div className={styles.uploadIcon}>📁</div>
                <div className={styles.uploadText}>Нажмите для выбора файла</div>
                <div className={styles.uploadHint}>Поддерживаются: PDF, Excel</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'test' && (
        <div className={styles.tabContent}>
          <div className={styles.panel}>
            <h2 className={styles.panelTitle}>ТЕСТОВЫЙ ЗАПРОС К RAG</h2>
            <div className={styles.testQueryForm}>
              <input
                type="text"
                className={styles.testInput}
                value={testQuery}
                onChange={(e) => setTestQuery(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleTestQuery()}
                placeholder="Введите вопрос для тестирования..."
              />
              <button className={styles.btn} onClick={handleTestQuery}>▶ ВЫПОЛНИТЬ</button>
            </div>
            <div className={styles.testResult}>
              {testResult ? (
                testResult.error ? (
                  <div style={{ color: '#e74c3c' }}>Ошибка: {testResult.error}</div>
                ) : testResult.status === 'success' ? (
                  <>
                    <div style={{ marginBottom: '15px' }}>
                      <strong>Вопрос:</strong> {testResult.query}
                    </div>
                    <div style={{ marginBottom: '15px', padding: '15px', background: 'white', borderRadius: '6px' }}>
                      <strong>Ответ:</strong><br />
                      <div style={{ whiteSpace: 'pre-wrap' }}>{testResult.answer}</div>
                    </div>
                    <div style={{ fontSize: '12px', color: '#65676b' }}>
                      Источников: {testResult.context_count} | Модель: {testResult.model} ({testResult.provider})
                    </div>
                  </>
                ) : (
                  <div>Результаты появятся здесь...</div>
                )
              ) : (
                <div className={styles.resultPlaceholder}>Результаты появятся здесь...</div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Parameters Panel */}
      <div className={`${styles.paramsPanel} ${paramsPanelCollapsed ? styles.collapsed : ''}`}>
        <div className={styles.paramsPanelHeader} onClick={() => setParamsPanelCollapsed(!paramsPanelCollapsed)}>
          <span>⚙️ ПАРАМЕТРЫ RAG</span>
          <span>{paramsPanelCollapsed ? '▲' : '▼'}</span>
        </div>
        {!paramsPanelCollapsed && (
          <div className={styles.paramsPanelContent}>
            <div className={styles.paramGroup}>
              <label className={styles.paramLabel}>
                <span>Размер чанка (chunk_size)</span>
                <span className={styles.paramValue}>{params.chunk_size}</span>
              </label>
              <input
                type="range"
                className={styles.paramSlider}
                min="100"
                max="2000"
                step="50"
                value={params.chunk_size}
                onChange={(e) => setParams({ ...params, chunk_size: parseInt(e.target.value) })}
              />
            </div>
            {/* Add other parameter sliders similarly */}
            <div className={styles.paramActions}>
              <button className={styles.btn} onClick={handleApplyParams}>▶ ПРИМЕНИТЬ</button>
              <button className={`${styles.btn} ${styles.btnSecondary}`} onClick={() => loadData()}>
                🔄 СБРОС
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
























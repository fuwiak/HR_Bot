'use client'

import { useState, useEffect } from 'react'
import { useWebApp } from '@/lib/useWebApp'
import { 
  getRAGStats, 
  getRAGParameters, 
  updateRAGParameters,
  getWEEEKStatus,
  checkEmails 
} from '@/lib/api'
import styles from './Settings.module.css'

interface SettingsProps {
  onBack: () => void
}

interface RAGParams {
  chunk_size: number
  chunk_overlap: number
  top_k: number
  min_score: number
  temperature: number
  max_tokens: number
}

export default function Settings({ onBack }: SettingsProps) {
  const WebApp = useWebApp()
  const [activeTab, setActiveTab] = useState<'status' | 'rag' | 'integrations'>('status')
  const [loading, setLoading] = useState(false)
  
  // Status state
  const [ragStats, setRagStats] = useState<any>(null)
  const [weeekStatus, setWeeekStatus] = useState<any>(null)
  const [emailStatus, setEmailStatus] = useState<any>(null)
  
  // RAG params state
  const [ragParams, setRagParams] = useState<RAGParams>({
    chunk_size: 500,
    chunk_overlap: 50,
    top_k: 10,
    min_score: 0.3,
    temperature: 0.7,
    max_tokens: 2048
  })
  const [paramsChanged, setParamsChanged] = useState(false)

  const loadStatus = async () => {
    setLoading(true)
    try {
      const [rag, weeek] = await Promise.all([
        getRAGStats().catch(() => null),
        getWEEEKStatus().catch(() => null)
      ])
      setRagStats(rag)
      setWeeekStatus(weeek)
    } catch (error) {
      console.error('Ошибка загрузки статуса:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadRAGParams = async () => {
    setLoading(true)
    try {
      const params = await getRAGParameters()
      setRagParams(params)
    } catch (error) {
      console.error('Ошибка загрузки параметров RAG:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleCheckEmails = async () => {
    setLoading(true)
    WebApp?.HapticFeedback?.impactOccurred('light')
    try {
      const result = await checkEmails()
      setEmailStatus(result)
      WebApp?.showAlert(`📧 Найдено писем: ${result.count || 0}`)
    } catch (error: any) {
      WebApp?.showAlert(error.message || 'Ошибка проверки почты')
    } finally {
      setLoading(false)
    }
  }

  const handleParamChange = (key: keyof RAGParams, value: number) => {
    setRagParams(prev => ({ ...prev, [key]: value }))
    setParamsChanged(true)
  }

  const handleSaveParams = async () => {
    setLoading(true)
    WebApp?.HapticFeedback?.impactOccurred('medium')
    try {
      await updateRAGParameters(ragParams)
      setParamsChanged(false)
      WebApp?.showAlert('✅ Параметры сохранены!')
    } catch (error: any) {
      WebApp?.showAlert(error.message || 'Ошибка сохранения параметров')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (activeTab === 'status') {
      loadStatus()
    } else if (activeTab === 'rag') {
      loadRAGParams()
    }
  }, [activeTab])

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <button className={styles.backButton} onClick={onBack}>
          ← Назад
        </button>
        <h1>⚙️ Панель управления</h1>
      </div>

      <div className={styles.tabs}>
        <button
          className={`${styles.tab} ${activeTab === 'status' ? styles.active : ''}`}
          onClick={() => setActiveTab('status')}
        >
          📊 Статус
        </button>
        <button
          className={`${styles.tab} ${activeTab === 'rag' ? styles.active : ''}`}
          onClick={() => setActiveTab('rag')}
        >
          🧠 RAG
        </button>
        <button
          className={`${styles.tab} ${activeTab === 'integrations' ? styles.active : ''}`}
          onClick={() => setActiveTab('integrations')}
        >
          🔗 Интеграции
        </button>
      </div>

      <div className={styles.content}>
        {activeTab === 'status' && (
          <div className={styles.statusTab}>
            {loading ? (
              <div className={styles.loading}>⏳ Загрузка статуса...</div>
            ) : (
              <>
                {/* RAG Status */}
                <div className={styles.statusCard}>
                  <div className={styles.statusHeader}>
                    <h3>📚 База знаний (RAG)</h3>
                    <span className={`${styles.statusBadge} ${ragStats?.exists ? styles.online : styles.offline}`}>
                      {ragStats?.exists ? '✅ Активна' : '❌ Недоступна'}
                    </span>
                  </div>
                  {ragStats && (
                    <div className={styles.statusDetails}>
                      <div className={styles.statRow}>
                        <span>Коллекция:</span>
                        <span>{ragStats.collection_name || 'N/A'}</span>
                      </div>
                      <div className={styles.statRow}>
                        <span>Документов:</span>
                        <span>{ragStats.points_count || 0}</span>
                      </div>
                      <div className={styles.statRow}>
                        <span>Размерность:</span>
                        <span>{ragStats.vector_size || 'N/A'}</span>
                      </div>
                    </div>
                  )}
                </div>

                {/* WEEEK Status */}
                <div className={styles.statusCard}>
                  <div className={styles.statusHeader}>
                    <h3>📋 WEEEK</h3>
                    <span className={`${styles.statusBadge} ${weeekStatus?.connected ? styles.online : styles.offline}`}>
                      {weeekStatus?.connected ? '✅ Подключен' : '⚠️ Не настроен'}
                    </span>
                  </div>
                  {weeekStatus && (
                    <div className={styles.statusDetails}>
                      <div className={styles.statRow}>
                        <span>Workspace:</span>
                        <span>{weeekStatus.workspace_name || 'N/A'}</span>
                      </div>
                      <div className={styles.statRow}>
                        <span>Проектов:</span>
                        <span>{weeekStatus.projects_count || 0}</span>
                      </div>
                    </div>
                  )}
                </div>

                {/* Email Status */}
                <div className={styles.statusCard}>
                  <div className={styles.statusHeader}>
                    <h3>📧 Email</h3>
                    <button 
                      className={styles.checkButton}
                      onClick={handleCheckEmails}
                      disabled={loading}
                    >
                      {loading ? '⏳' : '🔄'} Проверить
                    </button>
                  </div>
                  {emailStatus && (
                    <div className={styles.statusDetails}>
                      <div className={styles.statRow}>
                        <span>Новых писем:</span>
                        <span>{emailStatus.count || 0}</span>
                      </div>
                      <div className={styles.statRow}>
                        <span>Последняя проверка:</span>
                        <span>{new Date().toLocaleTimeString('ru-RU')}</span>
                      </div>
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        )}

        {activeTab === 'rag' && (
          <div className={styles.ragTab}>
            <h3>🧠 Параметры RAG</h3>
            
            {loading ? (
              <div className={styles.loading}>⏳ Загрузка параметров...</div>
            ) : (
              <div className={styles.paramsForm}>
                <div className={styles.paramGroup}>
                  <label>Размер чанка (chunk_size)</label>
                  <input
                    type="number"
                    value={ragParams.chunk_size}
                    onChange={(e) => handleParamChange('chunk_size', parseInt(e.target.value))}
                    className={styles.input}
                    min={100}
                    max={2000}
                  />
                  <span className={styles.hint}>Размер текстовых блоков (100-2000)</span>
                </div>

                <div className={styles.paramGroup}>
                  <label>Перекрытие чанков (chunk_overlap)</label>
                  <input
                    type="number"
                    value={ragParams.chunk_overlap}
                    onChange={(e) => handleParamChange('chunk_overlap', parseInt(e.target.value))}
                    className={styles.input}
                    min={0}
                    max={500}
                  />
                  <span className={styles.hint}>Перекрытие между блоками (0-500)</span>
                </div>

                <div className={styles.paramGroup}>
                  <label>Top-K результатов</label>
                  <input
                    type="number"
                    value={ragParams.top_k}
                    onChange={(e) => handleParamChange('top_k', parseInt(e.target.value))}
                    className={styles.input}
                    min={1}
                    max={50}
                  />
                  <span className={styles.hint}>Количество результатов поиска (1-50)</span>
                </div>

                <div className={styles.paramGroup}>
                  <label>Минимальный score</label>
                  <input
                    type="number"
                    value={ragParams.min_score}
                    onChange={(e) => handleParamChange('min_score', parseFloat(e.target.value))}
                    className={styles.input}
                    min={0}
                    max={1}
                    step={0.05}
                  />
                  <span className={styles.hint}>Порог релевантности (0-1)</span>
                </div>

                <div className={styles.paramGroup}>
                  <label>Температура LLM</label>
                  <input
                    type="number"
                    value={ragParams.temperature}
                    onChange={(e) => handleParamChange('temperature', parseFloat(e.target.value))}
                    className={styles.input}
                    min={0}
                    max={2}
                    step={0.1}
                  />
                  <span className={styles.hint}>Креативность ответов (0-2)</span>
                </div>

                <div className={styles.paramGroup}>
                  <label>Max Tokens</label>
                  <input
                    type="number"
                    value={ragParams.max_tokens}
                    onChange={(e) => handleParamChange('max_tokens', parseInt(e.target.value))}
                    className={styles.input}
                    min={256}
                    max={8192}
                  />
                  <span className={styles.hint}>Максимальная длина ответа (256-8192)</span>
                </div>

                <button 
                  className={`${styles.saveButton} ${paramsChanged ? styles.changed : ''}`}
                  onClick={handleSaveParams}
                  disabled={loading || !paramsChanged}
                >
                  {loading ? '⏳ Сохранение...' : '💾 Сохранить параметры'}
                </button>
              </div>
            )}
          </div>
        )}

        {activeTab === 'integrations' && (
          <div className={styles.integrationsTab}>
            <h3>🔗 Интеграции</h3>
            
            <div className={styles.integrationsList}>
              <div className={styles.integrationCard}>
                <div className={styles.integrationIcon}>📱</div>
                <div className={styles.integrationInfo}>
                  <h4>Telegram Bot</h4>
                  <p>Основной интерфейс бота</p>
                </div>
                <span className={`${styles.statusBadge} ${styles.online}`}>✅ Активен</span>
              </div>

              <div className={styles.integrationCard}>
                <div className={styles.integrationIcon}>📚</div>
                <div className={styles.integrationInfo}>
                  <h4>Qdrant (RAG)</h4>
                  <p>Векторная база знаний</p>
                </div>
                <span className={`${styles.statusBadge} ${ragStats?.exists ? styles.online : styles.offline}`}>
                  {ragStats?.exists ? '✅ Подключен' : '⚠️ Недоступен'}
                </span>
              </div>

              <div className={styles.integrationCard}>
                <div className={styles.integrationIcon}>📋</div>
                <div className={styles.integrationInfo}>
                  <h4>WEEEK</h4>
                  <p>Управление проектами</p>
                </div>
                <span className={`${styles.statusBadge} ${weeekStatus?.connected ? styles.online : styles.offline}`}>
                  {weeekStatus?.connected ? '✅ Подключен' : '⚠️ Не настроен'}
                </span>
              </div>

              <div className={styles.integrationCard}>
                <div className={styles.integrationIcon}>☁️</div>
                <div className={styles.integrationInfo}>
                  <h4>Яндекс.Диск</h4>
                  <p>Хранение файлов</p>
                </div>
                <span className={`${styles.statusBadge} ${styles.online}`}>✅ Подключен</span>
              </div>

              <div className={styles.integrationCard}>
                <div className={styles.integrationIcon}>📧</div>
                <div className={styles.integrationInfo}>
                  <h4>Email (IMAP/SMTP)</h4>
                  <p>Уведомления о письмах</p>
                </div>
                <span className={`${styles.statusBadge} ${styles.online}`}>✅ Настроен</span>
              </div>

              <div className={styles.integrationCard}>
                <div className={styles.integrationIcon}>📊</div>
                <div className={styles.integrationInfo}>
                  <h4>Google Sheets</h4>
                  <p>Прайс-лист и услуги</p>
                </div>
                <span className={`${styles.statusBadge} ${styles.online}`}>✅ Подключен</span>
              </div>

              <div className={styles.integrationCard}>
                <div className={styles.integrationIcon}>🤖</div>
                <div className={styles.integrationInfo}>
                  <h4>OpenRouter LLM</h4>
                  <p>AI модель для ответов</p>
                </div>
                <span className={`${styles.statusBadge} ${styles.online}`}>✅ Активен</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

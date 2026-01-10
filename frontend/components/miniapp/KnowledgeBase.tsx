'use client'

import { useState, useEffect } from 'react'
import WebApp from '@twa-dev/sdk'
import { searchRAG, getRAGStats, getRAGDocs } from '@/lib/api'
import styles from './KnowledgeBase.module.css'

interface KnowledgeBaseProps {
  onBack: () => void
}

export default function KnowledgeBase({ onBack }: KnowledgeBaseProps) {
  const [activeTab, setActiveTab] = useState<'search' | 'docs' | 'stats'>('search')
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [docs, setDocs] = useState<any[]>([])
  const [stats, setStats] = useState<any>(null)

  const handleSearch = async () => {
    if (!searchQuery.trim()) return
    
    setLoading(true)
    WebApp.HapticFeedback.impactOccurred('light')
    
    try {
      const results = await searchRAG(searchQuery, 5)
      setSearchResults(results)
    } catch (error: any) {
      WebApp.showAlert(error.message)
    } finally {
      setLoading(false)
    }
  }

  const loadDocs = async () => {
    setLoading(true)
    try {
      const result = await getRAGDocs(20)
      setDocs(result.docs || [])
    } catch (error: any) {
      WebApp.showAlert(error.message)
    } finally {
      setLoading(false)
    }
  }

  const loadStats = async () => {
    setLoading(true)
    try {
      const result = await getRAGStats()
      setStats(result)
    } catch (error: any) {
      WebApp.showAlert(error.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (activeTab === 'docs' && docs.length === 0) {
      loadDocs()
    }
    if (activeTab === 'stats' && !stats) {
      loadStats()
    }
  }, [activeTab])

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <button className={styles.backButton} onClick={onBack}>
          ← Назад
        </button>
        <h1>📚 База знаний</h1>
      </div>

      <div className={styles.tabs}>
        <button
          className={`${styles.tab} ${activeTab === 'search' ? styles.active : ''}`}
          onClick={() => setActiveTab('search')}
        >
          🔍 Поиск
        </button>
        <button
          className={`${styles.tab} ${activeTab === 'docs' ? styles.active : ''}`}
          onClick={() => setActiveTab('docs')}
        >
          📚 Документы
        </button>
        <button
          className={`${styles.tab} ${activeTab === 'stats' ? styles.active : ''}`}
          onClick={() => setActiveTab('stats')}
        >
          📊 Статистика
        </button>
      </div>

      <div className={styles.content}>
        {activeTab === 'search' && (
          <div className={styles.searchTab}>
            <div className={styles.searchBox}>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Введите запрос для поиска..."
                className={styles.input}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              />
              <button 
                className={styles.searchButton}
                onClick={handleSearch}
                disabled={loading}
              >
                {loading ? '⏳' : '🔍'}
              </button>
            </div>

            {searchResults && (
              <div className={styles.results}>
                <h3>Результаты поиска:</h3>
                {searchResults.answer && (
                  <div className={styles.answer}>
                    <p>{searchResults.answer}</p>
                  </div>
                )}
                {searchResults.sources && searchResults.sources.length > 0 && (
                  <div className={styles.sources}>
                    <h4>Источники:</h4>
                    {searchResults.sources.map((source: any, idx: number) => (
                      <div key={idx} className={styles.sourceItem}>
                        <p><strong>{source.title || source.name}</strong></p>
                        {source.path && <p className={styles.path}>{source.path}</p>}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {activeTab === 'docs' && (
          <div className={styles.docsTab}>
            {loading ? (
              <div className={styles.loading}>Загрузка...</div>
            ) : (
              <>
                {docs.length > 0 ? (
                  <div className={styles.docsList}>
                    {docs.map((doc: any, idx: number) => (
                      <div key={idx} className={styles.docItem}>
                        <h4>{doc.title || doc.name || 'Без названия'}</h4>
                        {doc.category && (
                          <p className={styles.category}>🏷 {doc.category}</p>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className={styles.empty}>Документы не найдены</p>
                )}
              </>
            )}
          </div>
        )}

        {activeTab === 'stats' && (
          <div className={styles.statsTab}>
            {loading ? (
              <div className={styles.loading}>Загрузка...</div>
            ) : stats ? (
              <div className={styles.statsContent}>
                <div className={styles.statItem}>
                  <span className={styles.statLabel}>Коллекция:</span>
                  <span className={styles.statValue}>{stats.collection_name || 'N/A'}</span>
                </div>
                <div className={styles.statItem}>
                  <span className={styles.statLabel}>Статус:</span>
                  <span className={styles.statValue}>
                    {stats.exists ? '✅ Активна' : '❌ Не найдена'}
                  </span>
                </div>
                {stats.exists && (
                  <>
                    <div className={styles.statItem}>
                      <span className={styles.statLabel}>Документов:</span>
                      <span className={styles.statValue}>{stats.points_count || 0}</span>
                    </div>
                    <div className={styles.statItem}>
                      <span className={styles.statLabel}>Размерность:</span>
                      <span className={styles.statValue}>{stats.vector_size || 'N/A'}</span>
                    </div>
                  </>
                )}
              </div>
            ) : (
              <p className={styles.empty}>Нажмите для загрузки статистики</p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

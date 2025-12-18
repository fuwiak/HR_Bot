'use client'

import { useState } from 'react'
import { sendEmail, generateProposal, searchRAG, getRAGStats, getRAGDocs } from '@/lib/api'
import Link from 'next/link'
import styles from './page.module.css'

export default function Home() {
  const [emailResult, setEmailResult] = useState<string | null>(null)
  const [proposalResult, setProposalResult] = useState<string | null>(null)
  const [ragSearchResult, setRagSearchResult] = useState<string | null>(null)
  const [ragStatsResult, setRagStatsResult] = useState<string | null>(null)
  const [ragDocsResult, setRagDocsResult] = useState<string | null>(null)

  const handleEmailSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    const recipient = formData.get('recipient') as string
    const subject = formData.get('subject') as string
    const body = formData.get('body') as string

    try {
      const result = await sendEmail(recipient, subject, body)
      setEmailResult(JSON.stringify(result, null, 2))
    } catch (error: any) {
      setEmailResult(`❌ Ошибка: ${error.message}`)
    }
  }

  const handleProposalSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    const request = formData.get('request') as string

    try {
      const result = await generateProposal(request)
      setProposalResult(JSON.stringify(result, null, 2))
    } catch (error: any) {
      setProposalResult(`❌ Ошибка: ${error.message}`)
    }
  }

  const handleRAGSearch = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    const query = formData.get('query') as string

    try {
      const result = await searchRAG(query, 5)
      setRagSearchResult(JSON.stringify(result, null, 2))
    } catch (error: any) {
      setRagSearchResult(`❌ Ошибка: ${error.message}`)
    }
  }

  const handleLoadRAGStats = async () => {
    try {
      const result = await getRAGStats()
      setRagStatsResult(JSON.stringify(result, null, 2))
    } catch (error: any) {
      setRagStatsResult(`❌ Ошибка: ${error.message}`)
    }
  }

  const handleLoadRAGDocs = async () => {
    try {
      const result = await getRAGDocs(20)
      setRagDocsResult(JSON.stringify(result, null, 2))
    } catch (error: any) {
      setRagDocsResult(`❌ Ошибка: ${error.message}`)
    }
  }

  return (
    <div className={styles.contentCard}>
      <h1>Добро пожаловать!</h1>
      <p className={styles.subtitle}>Демонстрационный интерфейс AI-ассистента для консалтинговой практики</p>
      
      <div className={styles.grid}>
        {/* RAG Dashboard */}
        <div 
          className={styles.card} 
          id="rag-dashboard" 
          style={{
            gridColumn: '1 / -1',
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            color: 'white',
            border: 'none'
          }}
        >
          <h2 style={{ color: 'white' }}>📊 RAG Dashboard - Полное управление базой знаний</h2>
          <p style={{ color: 'rgba(255,255,255,0.9)' }}>
            Управление векторной БД, метрики, оценка качества, загрузка файлов, тестирование запросов
          </p>
          <div style={{ display: 'flex', gap: '12px', marginTop: '16px', flexWrap: 'wrap' }}>
            <Link 
              href="/rag" 
              className={styles.btn}
              style={{
                background: 'white',
                color: '#667eea',
                fontWeight: 600,
                padding: '12px 24px',
                textDecoration: 'none'
              }}
            >
              ▶ Открыть RAG Dashboard
            </Link>
            <span style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '14px', opacity: 0.9 }}>
              <span>⚙️</span>
              <span>Оценка • Метрики • Workflow • Файлы • Тесты</span>
            </span>
          </div>
        </div>
        
        {/* Architecture */}
        <div className={styles.card}>
          <h2>🏗️ Архитектура</h2>
          <p>Визуализация архитектуры системы</p>
          <Link href="/architecture" className={styles.btn}>Просмотр архитектуры</Link>
        </div>
      </div>
    </div>
  )
}


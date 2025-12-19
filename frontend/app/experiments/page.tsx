'use client'

import { useState } from 'react'
import { sendEmail, generateProposal, searchRAG, getRAGStats, getRAGDocs } from '@/lib/api'
import styles from './page.module.css'

export default function ExperimentsPage() {
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
      <h1>🧪 Эксперименты</h1>
      <p className={styles.subtitle}>Тестирование и эксперименты с функциональностью AI-ассистента</p>
      
      <div className={styles.grid}>
        {/* Email Demo */}
        <div className={styles.card} id="email-demo">
          <h2>📧 Демонстрация Email</h2>
          <p>Отправка тестового email для демонстрации обработки запросов</p>
          <form onSubmit={handleEmailSubmit}>
            <div className={styles.formGroup}>
              <label>Получатель:</label>
              <input type="email" name="recipient" required placeholder="email@example.com" />
            </div>
            <div className={styles.formGroup}>
              <label>Тема:</label>
              <input type="text" name="subject" required placeholder="Тема письма" />
            </div>
            <div className={styles.formGroup}>
              <label>Сообщение:</label>
              <textarea name="body" required placeholder="Текст сообщения..." />
            </div>
            <button type="submit" className={styles.btn}>Отправить</button>
          </form>
          {emailResult && (
            <div className={styles.result}>
              <pre>{emailResult}</pre>
            </div>
          )}
        </div>
        
        {/* Proposal Demo */}
        <div className={styles.card} id="proposal-demo">
          <h2>📝 Генерация КП</h2>
          <p>Генерация коммерческого предложения по запросу клиента</p>
          <form onSubmit={handleProposalSubmit}>
            <div className={styles.formGroup}>
              <label>Запрос клиента:</label>
              <textarea name="request" required placeholder="Введите запрос клиента..." />
            </div>
            <button type="submit" className={styles.btn}>Сгенерировать КП</button>
          </form>
          {proposalResult && (
            <div className={styles.result}>
              <pre>{proposalResult}</pre>
            </div>
          )}
        </div>
        
        {/* RAG Search */}
        <div className={styles.card} id="rag-search">
          <h2>🔍 Поиск в RAG</h2>
          <p>Семантический поиск в базе знаний</p>
          <form onSubmit={handleRAGSearch}>
            <div className={styles.formGroup}>
              <label>Поисковый запрос:</label>
              <input type="text" name="query" required placeholder="Введите запрос..." />
            </div>
            <button type="submit" className={styles.btn}>Искать</button>
          </form>
          {ragSearchResult && (
            <div className={styles.result}>
              <pre>{ragSearchResult}</pre>
            </div>
          )}
        </div>
        
        {/* RAG Stats */}
        <div className={styles.card} id="rag-stats">
          <h2>📊 Статистика RAG</h2>
          <p>Информация о базе знаний</p>
          <button onClick={handleLoadRAGStats} className={styles.btn}>Загрузить статистику</button>
          {ragStatsResult && (
            <div className={styles.result}>
              <pre>{ragStatsResult}</pre>
            </div>
          )}
        </div>
        
        {/* RAG Docs */}
        <div className={styles.card} id="rag-docs">
          <h2>📚 Документы в базе</h2>
          <p>Список всех документов в RAG базе знаний</p>
          <button onClick={handleLoadRAGDocs} className={styles.btn}>Загрузить документы</button>
          {ragDocsResult && (
            <div className={styles.result}>
              <pre>{ragDocsResult}</pre>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}















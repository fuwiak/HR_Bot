'use client'

import { useState, useEffect } from 'react'
import { useWebApp } from '@/lib/useWebApp'
import { checkEmails, generateEmailDraft } from '@/lib/api'
import styles from './Email.module.css'

interface EmailProps {
  onBack: () => void
}

export default function Email({ onBack }: EmailProps) {
  const WebApp = useWebApp()
  const [activeTab, setActiveTab] = useState<'check' | 'draft'>('check')
  const [emails, setEmails] = useState<any[]>([])
  const [draftRequest, setDraftRequest] = useState('')
  const [draftResult, setDraftResult] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleCheckEmails = async () => {
    setLoading(true)
    try {
      const result = await checkEmails()
      setEmails(result.emails || result || [])
    } catch (error: any) {
      WebApp?.showAlert(error.message || 'Ошибка проверки писем')
      setEmails([])
    } finally {
      setLoading(false)
    }
  }

  const handleGenerateDraft = async () => {
    if (!draftRequest.trim()) {
      WebApp?.showAlert('Введите тему письма или запрос')
      return
    }

    setLoading(true)
    WebApp?.HapticFeedback?.impactOccurred('medium')
    
    try {
      const result = await generateEmailDraft(draftRequest)
      setDraftResult(result.draft || result.text || JSON.stringify(result, null, 2))
    } catch (error: any) {
      WebApp?.showAlert(error.message)
      setDraftResult(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (activeTab === 'check') {
      handleCheckEmails()
    }
  }, [activeTab])

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <button className={styles.backButton} onClick={onBack}>
          ← Назад
        </button>
        <h1>📧 Email</h1>
      </div>

      <div className={styles.tabs}>
        <button
          className={`${styles.tab} ${activeTab === 'check' ? styles.active : ''}`}
          onClick={() => setActiveTab('check')}
        >
          📬 Проверить
        </button>
        <button
          className={`${styles.tab} ${activeTab === 'draft' ? styles.active : ''}`}
          onClick={() => setActiveTab('draft')}
        >
          ✍️ Черновик
        </button>
      </div>

      <div className={styles.content}>
        {activeTab === 'check' && (
          <div className={styles.checkTab}>
            {loading ? (
              <div className={styles.loading}>Проверка писем...</div>
            ) : emails.length > 0 ? (
              <div className={styles.emailsList}>
                {emails.map((email: any, idx: number) => (
                  <div key={idx} className={styles.emailItem}>
                    <h3>{email.subject || 'Без темы'}</h3>
                    <p className={styles.emailFrom}>От: {email.from || email.sender || 'Неизвестно'}</p>
                    {email.date && <p className={styles.emailDate}>{email.date}</p>}
                    {email.preview && <p className={styles.emailPreview}>{email.preview}</p>}
                  </div>
                ))}
              </div>
            ) : (
              <div className={styles.empty}>
                <p>Новых писем нет</p>
                <button className={styles.refreshButton} onClick={handleCheckEmails}>
                  🔄 Обновить
                </button>
              </div>
            )}
          </div>
        )}

        {activeTab === 'draft' && (
          <div className={styles.draftTab}>
            <div className={styles.form}>
              <label>Тема письма или запрос:</label>
              <textarea
                value={draftRequest}
                onChange={(e) => setDraftRequest(e.target.value)}
                placeholder="Например: нужна помощь с подбором персонала"
                className={styles.textarea}
                rows={4}
              />
              <button
                className={styles.submitButton}
                onClick={handleGenerateDraft}
                disabled={loading}
              >
                {loading ? '⏳ Генерирую...' : '✍️ Сгенерировать черновик'}
              </button>
            </div>
            {draftResult && (
              <div className={styles.result}>
                <h3>Черновик:</h3>
                <div className={styles.resultContent}>
                  {draftResult}
                </div>
                <button
                  className={styles.copyButton}
                  onClick={() => {
                    navigator.clipboard.writeText(draftResult)
                    WebApp?.showAlert('Скопировано!')
                  }}
                >
                  📋 Копировать
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

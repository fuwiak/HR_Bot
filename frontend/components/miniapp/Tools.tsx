'use client'

import { useState } from 'react'
import { WebApp } from '@twa-dev/sdk'
import { generateProposal } from '@/lib/api'
import styles from './Tools.module.css'

interface ToolsProps {
  onBack: () => void
}

export default function Tools({ onBack }: ToolsProps) {
  const [activeTab, setActiveTab] = useState<'proposal' | 'summary'>('proposal')
  const [proposalRequest, setProposalRequest] = useState('')
  const [proposalResult, setProposalResult] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleGenerateProposal = async () => {
    if (!proposalRequest.trim()) {
      WebApp.showAlert('Введите запрос клиента')
      return
    }

    setLoading(true)
    WebApp.HapticFeedback.impactOccurred('medium')
    
    try {
      const result = await generateProposal(proposalRequest)
      setProposalResult(result.proposal || result.text || JSON.stringify(result, null, 2))
    } catch (error: any) {
      WebApp.showAlert(error.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <button className={styles.backButton} onClick={onBack}>
          ← Назад
        </button>
        <h1>🛠 Инструменты</h1>
      </div>

      <div className={styles.tabs}>
        <button
          className={`${styles.tab} ${activeTab === 'proposal' ? styles.active : ''}`}
          onClick={() => setActiveTab('proposal')}
        >
          📝 Генерация КП
        </button>
        <button
          className={`${styles.tab} ${activeTab === 'summary' ? styles.active : ''}`}
          onClick={() => setActiveTab('summary')}
        >
          📄 Суммаризация
        </button>
      </div>

      <div className={styles.content}>
        {activeTab === 'proposal' && (
          <div className={styles.proposalTab}>
            <div className={styles.form}>
              <label>Запрос клиента:</label>
              <textarea
                value={proposalRequest}
                onChange={(e) => setProposalRequest(e.target.value)}
                placeholder="Например: нужна помощь с подбором HR-менеджера"
                className={styles.textarea}
                rows={4}
              />
              <button
                className={styles.submitButton}
                onClick={handleGenerateProposal}
                disabled={loading}
              >
                {loading ? '⏳ Генерирую...' : '📝 Сгенерировать КП'}
              </button>
            </div>

            {proposalResult && (
              <div className={styles.result}>
                <h3>Результат:</h3>
                <div className={styles.resultContent}>
                  {proposalResult}
                </div>
                <button
                  className={styles.copyButton}
                  onClick={() => {
                    navigator.clipboard.writeText(proposalResult)
                    WebApp.showAlert('Скопировано!')
                  }}
                >
                  📋 Копировать
                </button>
              </div>
            )}
          </div>
        )}

        {activeTab === 'summary' && (
          <div className={styles.summaryTab}>
            <p className={styles.info}>
              Используйте команду в боте:
              <code>/summary [проект]</code>
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

'use client'

import { useState } from 'react'
import { useWebApp } from '@/lib/useWebApp'
import { generateProposal, generateSummary, generateReport, generateHypothesis } from '@/lib/api'
import styles from './Tools.module.css'

interface ToolsProps {
  onBack: () => void
}

export default function Tools({ onBack }: ToolsProps) {
  const WebApp = useWebApp()
  const [activeTab, setActiveTab] = useState<'proposal' | 'summary' | 'report' | 'hypothesis'>('proposal')
  const [proposalRequest, setProposalRequest] = useState('')
  const [proposalResult, setProposalResult] = useState<string | null>(null)
  const [summaryProject, setSummaryProject] = useState('')
  const [summaryResult, setSummaryResult] = useState<string | null>(null)
  const [reportProject, setReportProject] = useState('')
  const [reportResult, setReportResult] = useState<string | null>(null)
  const [hypothesisDescription, setHypothesisDescription] = useState('')
  const [hypothesisResult, setHypothesisResult] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleGenerateProposal = async () => {
    if (!proposalRequest.trim()) {
      WebApp?.showAlert('Введите запрос клиента')
      return
    }

    setLoading(true)
    WebApp?.HapticFeedback?.impactOccurred('medium')
    
    try {
      const result = await generateProposal(proposalRequest)
      setProposalResult(result.proposal || result.text || JSON.stringify(result, null, 2))
    } catch (error: any) {
      WebApp?.showAlert(error.message)
    } finally {
      setLoading(false)
    }
  }

  const handleGenerateSummary = async () => {
    if (!summaryProject.trim()) {
      WebApp?.showAlert('Введите название проекта')
      return
    }

    setLoading(true)
    WebApp?.HapticFeedback?.impactOccurred('medium')
    
    try {
      const result = await generateSummary(summaryProject)
      setSummaryResult(result.summary || result.text || JSON.stringify(result, null, 2))
    } catch (error: any) {
      WebApp?.showAlert(error.message)
    } finally {
      setLoading(false)
    }
  }

  const handleGenerateReport = async () => {
    if (!reportProject.trim()) {
      WebApp?.showAlert('Введите название проекта')
      return
    }

    setLoading(true)
    WebApp?.HapticFeedback?.impactOccurred('medium')
    
    try {
      const result = await generateReport(reportProject)
      setReportResult(result.report || result.text || JSON.stringify(result, null, 2))
    } catch (error: any) {
      WebApp?.showAlert(error.message)
    } finally {
      setLoading(false)
    }
  }

  const handleGenerateHypothesis = async () => {
    if (!hypothesisDescription.trim()) {
      WebApp?.showAlert('Введите описание')
      return
    }

    setLoading(true)
    WebApp?.HapticFeedback?.impactOccurred('medium')
    
    try {
      const result = await generateHypothesis(hypothesisDescription)
      setHypothesisResult(result.hypothesis || result.text || JSON.stringify(result, null, 2))
    } catch (error: any) {
      WebApp?.showAlert(error.message)
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
          📝 КП
        </button>
        <button
          className={`${styles.tab} ${activeTab === 'summary' ? styles.active : ''}`}
          onClick={() => setActiveTab('summary')}
        >
          📄 Сводка
        </button>
        <button
          className={`${styles.tab} ${activeTab === 'report' ? styles.active : ''}`}
          onClick={() => setActiveTab('report')}
        >
          📊 Отчёт
        </button>
        <button
          className={`${styles.tab} ${activeTab === 'hypothesis' ? styles.active : ''}`}
          onClick={() => setActiveTab('hypothesis')}
        >
          💡 Гипотеза
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
                    WebApp?.showAlert('Скопировано!')
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
            <div className={styles.form}>
              <label>Название проекта:</label>
              <input
                type="text"
                value={summaryProject}
                onChange={(e) => setSummaryProject(e.target.value)}
                placeholder="Например: Подбор HR"
                className={styles.input}
              />
              <button
                className={styles.submitButton}
                onClick={handleGenerateSummary}
                disabled={loading}
              >
                {loading ? '⏳ Генерирую...' : '📄 Сгенерировать сводку'}
              </button>
            </div>
            {summaryResult && (
              <div className={styles.result}>
                <h3>Сводка:</h3>
                <div className={styles.resultContent}>
                  {summaryResult}
                </div>
                <button
                  className={styles.copyButton}
                  onClick={() => {
                    navigator.clipboard.writeText(summaryResult)
                    WebApp?.showAlert('Скопировано!')
                  }}
                >
                  📋 Копировать
                </button>
              </div>
            )}
          </div>
        )}

        {activeTab === 'report' && (
          <div className={styles.reportTab}>
            <div className={styles.form}>
              <label>Название проекта:</label>
              <input
                type="text"
                value={reportProject}
                onChange={(e) => setReportProject(e.target.value)}
                placeholder="Например: Подбор HR-менеджера"
                className={styles.input}
              />
              <button
                className={styles.submitButton}
                onClick={handleGenerateReport}
                disabled={loading}
              >
                {loading ? '⏳ Генерирую...' : '📊 Сгенерировать отчёт'}
              </button>
            </div>
            {reportResult && (
              <div className={styles.result}>
                <h3>Отчёт:</h3>
                <div className={styles.resultContent}>
                  {reportResult}
                </div>
                <button
                  className={styles.copyButton}
                  onClick={() => {
                    navigator.clipboard.writeText(reportResult)
                    WebApp?.showAlert('Скопировано!')
                  }}
                >
                  📋 Копировать
                </button>
              </div>
            )}
          </div>
        )}

        {activeTab === 'hypothesis' && (
          <div className={styles.hypothesisTab}>
            <div className={styles.form}>
              <label>Описание задачи:</label>
              <textarea
                value={hypothesisDescription}
                onChange={(e) => setHypothesisDescription(e.target.value)}
                placeholder="Например: автоматизация HR в IT компании"
                className={styles.textarea}
                rows={4}
              />
              <button
                className={styles.submitButton}
                onClick={handleGenerateHypothesis}
                disabled={loading}
              >
                {loading ? '⏳ Генерирую...' : '💡 Сгенерировать гипотезы'}
              </button>
            </div>
            {hypothesisResult && (
              <div className={styles.result}>
                <h3>Гипотезы:</h3>
                <div className={styles.resultContent}>
                  {hypothesisResult}
                </div>
                <button
                  className={styles.copyButton}
                  onClick={() => {
                    navigator.clipboard.writeText(hypothesisResult)
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

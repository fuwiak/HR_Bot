'use client'

import { useState, useEffect } from 'react'
import { useWebApp } from '@/lib/useWebApp'
import { getWEEEKProjects, getWEEEKStatus, createWEEEKTask, generateSummary } from '@/lib/api'
import styles from './Projects.module.css'

interface ProjectsProps {
  onBack: () => void
}

export default function Projects({ onBack }: ProjectsProps) {
  const WebApp = useWebApp()
  const [activeTab, setActiveTab] = useState<'list' | 'create' | 'status' | 'summary'>('list')
  const [projects, setProjects] = useState<any[]>([])
  const [status, setStatus] = useState<any>(null)
  const [summaryResult, setSummaryResult] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [projectName, setProjectName] = useState('')
  const [taskName, setTaskName] = useState('')
  const [summaryProject, setSummaryProject] = useState('')

  const loadProjects = async () => {
    setLoading(true)
    try {
      const result = await getWEEEKProjects()
      setProjects(result.projects || result || [])
    } catch (error: any) {
      WebApp?.showAlert(error.message || 'Ошибка загрузки проектов')
      setProjects([])
    } finally {
      setLoading(false)
    }
  }

  const loadStatus = async () => {
    setLoading(true)
    try {
      const result = await getWEEEKStatus()
      setStatus(result)
    } catch (error: any) {
      WebApp?.showAlert(error.message || 'Ошибка загрузки статуса')
      setStatus(null)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateTask = async () => {
    if (!projectName.trim() || !taskName.trim()) {
      WebApp?.showAlert('Заполните название проекта и задачи')
      return
    }

    setLoading(true)
    try {
      await createWEEEKTask(projectName, taskName)
      WebApp?.showAlert('Задача создана!')
      setProjectName('')
      setTaskName('')
    } catch (error: any) {
      WebApp?.showAlert(error.message || 'Ошибка создания задачи')
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
    try {
      const result = await generateSummary(summaryProject)
      setSummaryResult(result.summary || result.text || JSON.stringify(result, null, 2))
    } catch (error: any) {
      WebApp?.showAlert(error.message || 'Ошибка генерации сводки')
      setSummaryResult(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (activeTab === 'list') {
      loadProjects()
    } else if (activeTab === 'status') {
      loadStatus()
    }
  }, [activeTab])

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <button className={styles.backButton} onClick={onBack}>
          ← Назад
        </button>
        <h1>📋 Проекты</h1>
      </div>

      <div className={styles.tabs}>
        <button
          className={`${styles.tab} ${activeTab === 'list' ? styles.active : ''}`}
          onClick={() => setActiveTab('list')}
        >
          📋 Список
        </button>
        <button
          className={`${styles.tab} ${activeTab === 'create' ? styles.active : ''}`}
          onClick={() => setActiveTab('create')}
        >
          ➕ Создать
        </button>
        <button
          className={`${styles.tab} ${activeTab === 'status' ? styles.active : ''}`}
          onClick={() => setActiveTab('status')}
        >
          📊 Статус
        </button>
        <button
          className={`${styles.tab} ${activeTab === 'summary' ? styles.active : ''}`}
          onClick={() => setActiveTab('summary')}
        >
          📝 Сводка
        </button>
      </div>

      <div className={styles.content}>
        {activeTab === 'list' && (
          <div className={styles.listTab}>
            {loading ? (
              <div className={styles.loading}>Загрузка проектов...</div>
            ) : projects.length > 0 ? (
              <div className={styles.projectsList}>
                {projects.map((project, idx) => (
                  <div key={idx} className={styles.projectItem}>
                    <h3>{project.title || project.name}</h3>
                    <p className={styles.projectId}>ID: {project.id}</p>
                  </div>
                ))}
              </div>
            ) : (
              <div className={styles.empty}>
                <p>Проекты не найдены</p>
                <button className={styles.createButton} onClick={() => setActiveTab('create')}>
                  Создать проект
                </button>
              </div>
            )}
          </div>
        )}

        {activeTab === 'create' && (
          <div className={styles.createTab}>
            <div className={styles.form}>
              <label>Название проекта:</label>
              <input
                type="text"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                placeholder="Например: Подбор HR"
                className={styles.input}
              />
              <label>Название задачи:</label>
              <input
                type="text"
                value={taskName}
                onChange={(e) => setTaskName(e.target.value)}
                placeholder="Например: Согласовать КП с клиентом"
                className={styles.input}
              />
              <button
                className={styles.submitButton}
                onClick={handleCreateTask}
                disabled={loading}
              >
                {loading ? '⏳ Создаю...' : '✅ Создать задачу'}
              </button>
            </div>
          </div>
        )}

        {activeTab === 'status' && (
          <div className={styles.statusTab}>
            {loading ? (
              <div className={styles.loading}>Загрузка статуса...</div>
            ) : status ? (
              <div className={styles.statusContent}>
                <pre>{JSON.stringify(status, null, 2)}</pre>
              </div>
            ) : (
              <div className={styles.empty}>
                <p>Статус не найден</p>
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
                {loading ? '⏳ Генерирую...' : '📝 Сгенерировать сводку'}
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
      </div>
    </div>
  )
}

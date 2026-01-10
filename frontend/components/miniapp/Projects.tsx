'use client'

import { useState, useEffect } from 'react'
import { useWebApp } from '@/lib/useWebApp'
import styles from './Projects.module.css'

interface ProjectsProps {
  onBack: () => void
}

export default function Projects({ onBack }: ProjectsProps) {
  const WebApp = useWebApp()
  const [activeTab, setActiveTab] = useState<'list' | 'create' | 'status' | 'summary'>('list')
  const [projects, setProjects] = useState<any[]>([])
  const [loading, setLoading] = useState(false)

  // TODO: Implement API calls to backend
  const loadProjects = async () => {
    setLoading(true)
    try {
      // const result = await getProjects()
      // setProjects(result)
      WebApp?.showAlert('Функция в разработке')
    } catch (error: any) {
      WebApp?.showAlert(error.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (activeTab === 'list') {
      loadProjects()
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
            <p className={styles.info}>
              Используйте команду в боте:
              <code>/weeek_create_project [название]</code>
            </p>
          </div>
        )}

        {activeTab === 'status' && (
          <div className={styles.statusTab}>
            <p className={styles.info}>
              Используйте команду в боте:
              <code>/status</code>
            </p>
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

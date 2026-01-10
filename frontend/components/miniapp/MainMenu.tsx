'use client'

import { useWebApp } from '@/lib/useWebApp'
import styles from './MainMenu.module.css'

export type PageType = 'knowledge' | 'projects' | 'tools' | 'help' | 'chat' | 'email' | 'yadisk' | 'booking' | 'settings'

interface MainMenuProps {
  user: any
  onNavigate: (page: PageType) => void
  isAdmin?: boolean
}

export default function MainMenu({ user, onNavigate, isAdmin = false }: MainMenuProps) {
  const WebApp = useWebApp()

  const handleNavigate = (page: PageType) => {
    WebApp?.HapticFeedback?.impactOccurred('light')
    onNavigate(page)
  }

  return (
    <div className={styles.menu}>
      <div className={styles.header}>
        <h1>✨ Добро пожаловать!</h1>
        {user && (
          <p className={styles.userName}>
            {user.first_name} {user.last_name || ''}
            {isAdmin && <span className={styles.adminBadge}>👑 Админ</span>}
          </p>
        )}
        <p className={styles.subtitle}>AI-ассистент Анастасии Новосёловой</p>
      </div>

      <div className={styles.grid}>
        <button 
          className={styles.card}
          onClick={() => handleNavigate('knowledge')}
        >
          <div className={styles.icon}>📚</div>
          <h2>База знаний</h2>
          <p>Поиск, документы, статистика</p>
        </button>

        <button 
          className={styles.card}
          onClick={() => handleNavigate('projects')}
        >
          <div className={styles.icon}>📋</div>
          <h2>Проекты</h2>
          <p>Управление задачами в WEEEK</p>
        </button>

        <button 
          className={styles.card}
          onClick={() => handleNavigate('tools')}
        >
          <div className={styles.icon}>🛠</div>
          <h2>Инструменты</h2>
          <p>Генерация КП, суммаризация</p>
        </button>

        <button 
          className={styles.card}
          onClick={() => handleNavigate('chat')}
        >
          <div className={styles.icon}>💬</div>
          <h2>Чат с AI</h2>
          <p>Общение с умным помощником</p>
        </button>

        <button 
          className={styles.card}
          onClick={() => handleNavigate('email')}
        >
          <div className={styles.icon}>📧</div>
          <h2>Email</h2>
          <p>Проверка писем, черновики</p>
        </button>

        <button 
          className={styles.card}
          onClick={() => handleNavigate('yadisk')}
        >
          <div className={styles.icon}>☁️</div>
          <h2>Яндекс.Диск</h2>
          <p>Файлы и документы</p>
        </button>

        <button 
          className={styles.card}
          onClick={() => handleNavigate('booking')}
        >
          <div className={styles.icon}>📅</div>
          <h2>Запись</h2>
          <p>Консультации и услуги</p>
        </button>

        <button 
          className={styles.card}
          onClick={() => handleNavigate('help')}
        >
          <div className={styles.icon}>❓</div>
          <h2>Помощь</h2>
          <p>Справочная информация</p>
        </button>

        {isAdmin && (
          <button 
            className={`${styles.card} ${styles.adminCard}`}
            onClick={() => handleNavigate('settings')}
          >
            <div className={styles.icon}>⚙️</div>
            <h2>Панель управления</h2>
            <p>Настройки бота и RAG</p>
          </button>
        )}
      </div>

      <div className={styles.footer}>
        <p>📬 Уведомления о новых письмах приходят автоматически</p>
      </div>
    </div>
  )
}

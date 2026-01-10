'use client'

import { useWebApp } from '@/lib/useWebApp'
import { getUnreadEmailCount } from '@/lib/api'
import { useState, useEffect } from 'react'
import Notifications from './Notifications'
import { SubMenuType } from './SubMenu'
import styles from './MainMenu.module.css'

export type PageType = 'knowledge' | 'projects' | 'tools' | 'help' | 'chat' | 'email' | 'yadisk' | 'booking' | 'settings'

// Re-export SubMenuType для удобства
export type { SubMenuType } from './SubMenu'

interface MainMenuProps {
  user: any
  onNavigate: (page: PageType | `submenu_${SubMenuType}`) => void
  isAdmin?: boolean
}

export default function MainMenu({ user, onNavigate, isAdmin = false }: MainMenuProps) {
  const WebApp = useWebApp()
  const [unreadEmailCount, setUnreadEmailCount] = useState(0)

  useEffect(() => {
    if (user?.id) {
      loadUnreadEmailCount()
      // Обновляем каждые 30 секунд
      const interval = setInterval(loadUnreadEmailCount, 30000)
      return () => clearInterval(interval)
    }
  }, [user?.id])

  const loadUnreadEmailCount = async () => {
    try {
      const result = await getUnreadEmailCount(user?.id?.toString())
      setUnreadEmailCount(result.unread_count || 0)
    } catch (error) {
      console.error('Ошибка загрузки количества писем:', error)
    }
  }

  const handleNavigate = (page: PageType | `submenu_${SubMenuType}`) => {
    WebApp?.HapticFeedback?.impactOccurred('light')
    onNavigate(page)
  }

  const handleCardClick = (page: PageType) => {
    // Для страниц с подменю открываем подменю, иначе переходим напрямую
    const pagesWithSubMenu: PageType[] = ['knowledge', 'projects', 'tools', 'help']
    if (pagesWithSubMenu.includes(page)) {
      handleNavigate(`submenu_${page}` as `submenu_${SubMenuType}`)
    } else {
      handleNavigate(page)
    }
  }

  return (
    <div className={styles.menu}>
      <div className={styles.header}>
        <div className={styles.headerTop}>
          <div>
            <h1>✨ Добро пожаловать!</h1>
            {user && (
              <p className={styles.userName}>
                {user.first_name} {user.last_name || ''}
                {isAdmin && <span className={styles.adminBadge}>👑 Админ</span>}
              </p>
            )}
            <p className={styles.subtitle}>AI-ассистент Анастасии Новосёловой</p>
          </div>
          {user?.id && (
            <Notifications userId={user.id.toString()} />
          )}
        </div>
      </div>

      <div className={styles.grid}>
        <button 
          className={styles.card}
          onClick={() => handleCardClick('knowledge')}
        >
          <div className={styles.icon}>📚</div>
          <h2>База знаний</h2>
          <p>Поиск, документы, статистика</p>
        </button>

        <button 
          className={styles.card}
          onClick={() => handleCardClick('projects')}
        >
          <div className={styles.icon}>📋</div>
          <h2>Проекты</h2>
          <p>Управление задачами в WEEEK</p>
        </button>

        <button 
          className={styles.card}
          onClick={() => handleCardClick('tools')}
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
          {unreadEmailCount > 0 && (
            <span className={styles.badge}>{unreadEmailCount > 99 ? '99+' : unreadEmailCount}</span>
          )}
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
          onClick={() => handleCardClick('help')}
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

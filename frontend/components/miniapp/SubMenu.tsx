'use client'

import { useWebApp } from '@/lib/useWebApp'
import styles from './SubMenu.module.css'

export type SubMenuType = 'knowledge' | 'projects' | 'tools' | 'help'

interface SubMenuItem {
  id: string
  icon: string
  title: string
  description: string
  action: () => void
}

interface SubMenuProps {
  type: SubMenuType
  onBack: () => void
  onNavigate: (page: string) => void
}

const subMenuConfig: Record<SubMenuType, { title: string; items: Omit<SubMenuItem, 'action'>[] }> = {
  knowledge: {
    title: '📚 База знаний',
    items: [
      {
        id: 'search',
        icon: '🔍',
        title: 'Поиск',
        description: 'Семантический поиск по методикам, кейсам, шаблонам'
      },
      {
        id: 'docs',
        icon: '📚',
        title: 'Документы',
        description: 'Список всех документов в базе'
      },
      {
        id: 'stats',
        icon: '📊',
        title: 'Статистика',
        description: 'Информация о базе знаний'
      }
    ]
  },
  projects: {
    title: '📋 Проекты',
    items: [
      {
        id: 'list',
        icon: '📋',
        title: 'Мои проекты',
        description: 'Список проектов в WEEEK'
      },
      {
        id: 'create',
        icon: '➕',
        title: 'Создать задачу',
        description: 'Новая задача в проекте'
      },
      {
        id: 'status',
        icon: '📊',
        title: 'Статус',
        description: 'Ближайшие дедлайны'
      },
      {
        id: 'summary',
        icon: '📝',
        title: 'Суммаризация',
        description: 'Сводка по проекту'
      }
    ]
  },
  tools: {
    title: '🛠 Инструменты',
    items: [
      {
        id: 'proposal',
        icon: '📝',
        title: 'Генерация КП',
        description: 'Создать коммерческое предложение'
      },
      {
        id: 'summary',
        icon: '📄',
        title: 'Суммаризация',
        description: 'Краткая сводка текста'
      }
    ]
  },
  help: {
    title: '❓ Помощь',
    items: [
      {
        id: 'commands',
        icon: '📖',
        title: 'Команды',
        description: 'Список всех команд бота'
      },
      {
        id: 'examples',
        icon: '💡',
        title: 'Примеры',
        description: 'Примеры использования'
      }
    ]
  }
}

export default function SubMenu({ type, onBack, onNavigate }: SubMenuProps) {
  const WebApp = useWebApp()
  const config = subMenuConfig[type]

  const handleItemClick = (itemId: string) => {
    WebApp?.HapticFeedback?.impactOccurred('light')
    
    // Маппинг действий для навигации с учетом типа подменю
    const actionMap: Record<string, () => void> = {
      // Knowledge base
      'search': () => onNavigate('knowledge'),
      'docs': () => onNavigate('knowledge'),
      'stats': () => onNavigate('knowledge'),
      
      // Projects
      'list': () => onNavigate('projects'),
      'create': () => onNavigate('projects'),
      'status': () => onNavigate('projects'),
      'projects_summary': () => onNavigate('projects'),
      
      // Tools
      'proposal': () => onNavigate('tools'),
      'tools_summary': () => onNavigate('tools'),
      
      // Help
      'commands': () => onNavigate('help'),
      'examples': () => onNavigate('help')
    }
    
    // Для summary используем префикс типа подменю
    const key = type === 'projects' && itemId === 'summary' 
      ? 'projects_summary'
      : type === 'tools' && itemId === 'summary'
      ? 'tools_summary'
      : itemId
    
    const action = actionMap[key]
    if (action) {
      action()
    }
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <button className={styles.backButton} onClick={onBack}>
          ← Назад
        </button>
        <h1>{config.title}</h1>
      </div>

      <div className={styles.menu}>
        {config.items.map((item) => (
          <button
            key={item.id}
            className={styles.menuItem}
            onClick={() => handleItemClick(item.id)}
          >
            <div className={styles.menuIcon}>{item.icon}</div>
            <div className={styles.menuContent}>
              <h3>{item.title}</h3>
              <p>{item.description}</p>
            </div>
            <div className={styles.menuArrow}>→</div>
          </button>
        ))}
      </div>
    </div>
  )
}

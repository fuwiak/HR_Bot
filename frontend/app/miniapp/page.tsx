'use client'

// Отключаем SSR для этой страницы, так как она использует Telegram WebApp API
export const dynamic = 'force-dynamic'

import { useEffect, useState } from 'react'
import styles from './page.module.css'
import MainMenu from '@/components/miniapp/MainMenu'
import KnowledgeBase from '@/components/miniapp/KnowledgeBase'
import Projects from '@/components/miniapp/Projects'
import Tools from '@/components/miniapp/Tools'
import Help from '@/components/miniapp/Help'
import Chat from '@/components/miniapp/Chat'

type Page = 'main' | 'knowledge' | 'projects' | 'tools' | 'help' | 'chat'

export default function MiniAppPage() {
  const [currentPage, setCurrentPage] = useState<Page>('main')
  const [isReady, setIsReady] = useState(false)
  const [user, setUser] = useState<any>(null)

  useEffect(() => {
    // Динамический импорт @twa-dev/sdk только на клиенте
    if (typeof window !== 'undefined') {
      import('@twa-dev/sdk').then(({ default: WebApp }) => {
        // Инициализация Telegram WebApp
        WebApp.ready()
        WebApp.expand()
        
        // Настройка темы
        WebApp.setHeaderColor('#667eea')
        WebApp.setBackgroundColor('#ffffff')
        
        // Получаем данные пользователя
        if (WebApp.initDataUnsafe?.user) {
          setUser(WebApp.initDataUnsafe.user)
        }
        
        setIsReady(true)
      })
    }
  }, [])

  if (!isReady) {
    return (
      <div className={styles.loading}>
        <div className={styles.spinner}></div>
        <p>Загрузка...</p>
      </div>
    )
  }

  return (
    <div className={styles.container}>
      {currentPage === 'main' && (
        <MainMenu 
          user={user}
          onNavigate={(page) => setCurrentPage(page)}
        />
      )}
      {currentPage === 'knowledge' && (
        <KnowledgeBase 
          onBack={() => setCurrentPage('main')}
        />
      )}
      {currentPage === 'projects' && (
        <Projects 
          onBack={() => setCurrentPage('main')}
        />
      )}
      {currentPage === 'tools' && (
        <Tools 
          onBack={() => setCurrentPage('main')}
        />
      )}
      {currentPage === 'help' && (
        <Help 
          onBack={() => setCurrentPage('main')}
        />
      )}
      {currentPage === 'chat' && (
        <Chat 
          onBack={() => setCurrentPage('main')}
        />
      )}
    </div>
  )
}

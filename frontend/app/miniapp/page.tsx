'use client'

import { useEffect, useState } from 'react'
import { initDataRaw, initData, WebApp } from '@twa-dev/sdk'
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
    // Инициализация Telegram WebApp
    if (typeof window !== 'undefined') {
      WebApp.ready()
      WebApp.expand()
      
      // Настройка темы
      WebApp.setHeaderColor('#667eea')
      WebApp.setBackgroundColor('#ffffff')
      
      // Получаем данные пользователя
      if (initDataRaw) {
        const data = initData
        if (data?.user) {
          setUser(data.user)
        }
      }
      
      setIsReady(true)
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

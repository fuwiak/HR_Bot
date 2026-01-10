'use client'

// Отключаем SSR для этой страницы, так как она использует Telegram WebApp API
export const dynamic = 'force-dynamic'

import { useEffect, useState } from 'react'
import styles from './page.module.css'
import MainMenu, { PageType } from '@/components/miniapp/MainMenu'
import KnowledgeBase from '@/components/miniapp/KnowledgeBase'
import Projects from '@/components/miniapp/Projects'
import Tools from '@/components/miniapp/Tools'
import Help from '@/components/miniapp/Help'
import Chat from '@/components/miniapp/Chat'
import Email from '@/components/miniapp/Email'
import YandexDisk from '@/components/miniapp/YandexDisk'
import Booking from '@/components/miniapp/Booking'
import Settings from '@/components/miniapp/Settings'
import { checkAdminStatus } from '@/lib/api'

type Page = 'main' | PageType

// Список ID администраторов (можно расширить через env)
const ADMIN_IDS = [5305427956, 123456789] // Добавьте свои ID

export default function MiniAppPage() {
  const [currentPage, setCurrentPage] = useState<Page>('main')
  const [isReady, setIsReady] = useState(false)
  const [user, setUser] = useState<any>(null)
  const [isAdmin, setIsAdmin] = useState(false)

  useEffect(() => {
    // Динамический импорт @twa-dev/sdk только на клиенте
    if (typeof window !== 'undefined') {
      import('@twa-dev/sdk').then(async ({ default: WebApp }) => {
        // Инициализация Telegram WebApp
        WebApp.ready()
        WebApp.expand()
        
        // Настройка темы
        WebApp.setHeaderColor('#667eea')
        WebApp.setBackgroundColor('#ffffff')
        
        // Получаем данные пользователя
        if (WebApp.initDataUnsafe?.user) {
          const userData = WebApp.initDataUnsafe.user
          setUser(userData)
          
          // Проверяем, является ли пользователь администратором
          const adminCheck = ADMIN_IDS.includes(userData.id)
          setIsAdmin(adminCheck)
          
          // Дополнительная проверка через API (если настроен)
          try {
            const result = await checkAdminStatus(userData.id.toString())
            if (result.is_admin) {
              setIsAdmin(true)
            }
          } catch {
            // Используем локальную проверку если API недоступен
          }
        }
        
        setIsReady(true)
      })
    }
  }, [])

  // Обработка кнопки "Назад" в Telegram
  useEffect(() => {
    if (typeof window !== 'undefined' && currentPage !== 'main') {
      import('@twa-dev/sdk').then(({ default: WebApp }) => {
        WebApp.BackButton.show()
        WebApp.BackButton.onClick(() => {
          setCurrentPage('main')
          WebApp.BackButton.hide()
        })
      })
    } else if (typeof window !== 'undefined') {
      import('@twa-dev/sdk').then(({ default: WebApp }) => {
        WebApp.BackButton.hide()
      })
    }
  }, [currentPage])

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
          isAdmin={isAdmin}
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
      {currentPage === 'email' && (
        <Email 
          onBack={() => setCurrentPage('main')}
        />
      )}
      {currentPage === 'yadisk' && (
        <YandexDisk 
          onBack={() => setCurrentPage('main')}
        />
      )}
      {currentPage === 'booking' && (
        <Booking 
          onBack={() => setCurrentPage('main')}
          userId={user?.id?.toString()}
        />
      )}
      {currentPage === 'settings' && isAdmin && (
        <Settings 
          onBack={() => setCurrentPage('main')}
        />
      )}
    </div>
  )
}

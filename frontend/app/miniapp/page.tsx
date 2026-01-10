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
import SubMenu, { SubMenuType } from '@/components/miniapp/SubMenu'

type Page = 'main' | PageType | `submenu_${SubMenuType}`

// Список ID администраторов (можно расширить через env)
const ADMIN_IDS = [5305427956, 123456789] // Добавьте свои ID

export default function MiniAppPage() {
  const [currentPage, setCurrentPage] = useState<Page>('main')
  const [isReady, setIsReady] = useState(false)
  const [user, setUser] = useState<any>(null)
  const [isAdmin, setIsAdmin] = useState(false)
  const [navigationHistory, setNavigationHistory] = useState<Page[]>(['main'])

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

  // Обработка навигации
  const handleNavigate = (page: PageType | `submenu_${SubMenuType}`) => {
    setNavigationHistory(prev => [...prev, page as Page])
    setCurrentPage(page as Page)
  }

  const handleBack = () => {
    if (navigationHistory.length > 1) {
      const newHistory = [...navigationHistory]
      newHistory.pop() // Удаляем текущую страницу
      const previousPage = newHistory[newHistory.length - 1]
      setNavigationHistory(newHistory)
      setCurrentPage(previousPage)
    } else {
      setCurrentPage('main')
      setNavigationHistory(['main'])
    }
  }

  const handleSubMenuNavigate = (subMenuType: SubMenuType) => {
    setNavigationHistory(prev => [...prev, `submenu_${subMenuType}` as Page])
    setCurrentPage(`submenu_${subMenuType}` as Page)
  }

  // Обработка кнопки "Назад" в Telegram
  useEffect(() => {
    if (typeof window !== 'undefined' && currentPage !== 'main') {
      import('@twa-dev/sdk').then(({ default: WebApp }) => {
        WebApp.BackButton.show()
        WebApp.BackButton.onClick(() => {
          handleBack()
          if (navigationHistory.length <= 1) {
            WebApp.BackButton.hide()
          }
        })
      })
    } else if (typeof window !== 'undefined') {
      import('@twa-dev/sdk').then(({ default: WebApp }) => {
        WebApp.BackButton.hide()
      })
    }
  }, [currentPage, navigationHistory])

  if (!isReady) {
    return (
      <div className={styles.loading}>
        <div className={styles.spinner}></div>
        <p>Загрузка...</p>
      </div>
    )
  }

  // Определяем, показывать ли подменю
  const getSubMenuType = (): SubMenuType | null => {
    if (currentPage.startsWith('submenu_')) {
      return currentPage.replace('submenu_', '') as SubMenuType
    }
    return null
  }

  const subMenuType = getSubMenuType()

  return (
    <div className={styles.container}>
      {currentPage === 'main' && (
        <MainMenu 
          user={user}
          onNavigate={handleNavigate}
          isAdmin={isAdmin}
        />
      )}
      
      {subMenuType && (
        <SubMenu
          type={subMenuType}
          onBack={handleBack}
          onNavigate={(page) => {
            // При навигации из подменю переходим на страницу
            setNavigationHistory(prev => [...prev, page as Page])
            setCurrentPage(page as Page)
          }}
        />
      )}
      {currentPage === 'knowledge' && !subMenuType && (
        <KnowledgeBase 
          onBack={handleBack}
        />
      )}
      {currentPage === 'projects' && !subMenuType && (
        <Projects 
          onBack={handleBack}
        />
      )}
      {currentPage === 'tools' && !subMenuType && (
        <Tools 
          onBack={handleBack}
        />
      )}
      {currentPage === 'help' && !subMenuType && (
        <Help 
          onBack={handleBack}
        />
      )}
      {currentPage === 'chat' && (
        <Chat 
          onBack={handleBack}
        />
      )}
      {currentPage === 'email' && (
        <Email 
          onBack={handleBack}
        />
      )}
      {currentPage === 'yadisk' && (
        <YandexDisk 
          onBack={handleBack}
        />
      )}
      {currentPage === 'booking' && (
        <Booking 
          onBack={handleBack}
          userId={user?.id?.toString()}
        />
      )}
      {currentPage === 'settings' && isAdmin && (
        <Settings 
          onBack={handleBack}
        />
      )}
    </div>
  )
}

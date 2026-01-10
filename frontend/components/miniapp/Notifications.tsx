'use client'

import { useState, useEffect, useRef } from 'react'
import { useWebApp } from '@/lib/useWebApp'
import { getNotifications, getUnreadNotificationCount, markNotificationAsRead } from '@/lib/api'
import styles from './Notifications.module.css'

interface Notification {
  id: string
  type: 'email' | 'task' | 'project' | 'system' | 'hrtime' | 'deadline'
  title: string
  message: string
  created_at: string
  read: boolean
  read_at?: string
  action_url?: string
  metadata?: {
    order_id?: string
    score?: number
    category?: string
    client_name?: string
    client_email?: string
  }
}

interface NotificationsProps {
  userId: string
}

export default function Notifications({ userId }: NotificationsProps) {
  const WebApp = useWebApp()
  const [isOpen, setIsOpen] = useState(false)
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [loading, setLoading] = useState(false)
  const [previousUnreadCount, setPreviousUnreadCount] = useState(0)
  const dropdownRef = useRef<HTMLDivElement>(null)

  const loadNotifications = async () => {
    if (!userId) return
    
    try {
      setLoading(true)
      const [notificationsData, unreadData] = await Promise.all([
        getNotifications(userId, 20),
        getUnreadNotificationCount(userId)
      ])
      
      const newNotifications = notificationsData.notifications || []
      const newUnreadCount = unreadData.unread_count || 0
      
      setNotifications(newNotifications)
      
      // Toast notification для новых уведомлений
      if (newUnreadCount > previousUnreadCount && previousUnreadCount > 0) {
        const newNotificationsCount = newUnreadCount - previousUnreadCount
        if (newNotificationsCount > 0) {
          // Haptic feedback для новых уведомлений
          WebApp?.HapticFeedback?.impactOccurred('medium')
          
          // Можно добавить toast notification здесь
          console.log(`🔔 ${newNotificationsCount} новое(ых) уведомление(й)`)
        }
      }
      
      setPreviousUnreadCount(newUnreadCount)
      setUnreadCount(newUnreadCount)
    } catch (error: any) {
      console.error('Ошибка загрузки уведомлений:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (userId) {
      loadNotifications()
      // Polling каждые 20 секунд
      const interval = setInterval(loadNotifications, 20000)
      return () => clearInterval(interval)
    }
  }, [userId])

  // Закрытие при клике вне компонента
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])

  const handleToggle = () => {
    WebApp?.HapticFeedback?.impactOccurred('light')
    setIsOpen(!isOpen)
    if (!isOpen) {
      loadNotifications()
    }
  }

  const handleNotificationClick = async (notification: Notification) => {
    if (!notification.read) {
      try {
        await markNotificationAsRead(userId, notification.id)
        setNotifications(prev => 
          prev.map(n => 
            n.id === notification.id 
              ? { ...n, read: true, read_at: new Date().toISOString() }
              : n
          )
        )
        setUnreadCount(prev => Math.max(0, prev - 1))
      } catch (error) {
        console.error('Ошибка отметки уведомления:', error)
      }
    }

    if (notification.action_url) {
      // Можно добавить навигацию по action_url
      WebApp?.openLink(notification.action_url)
    }
  }

  const handleMarkAllRead = async () => {
    try {
      await markNotificationAsRead(userId)
      setNotifications(prev => 
        prev.map(n => ({ ...n, read: true, read_at: new Date().toISOString() }))
      )
      setUnreadCount(0)
      WebApp?.HapticFeedback?.impactOccurred('medium')
    } catch (error) {
      console.error('Ошибка отметки всех уведомлений:', error)
    }
  }

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case 'email':
        return '📧'
      case 'hrtime':
        return '🔥'
      case 'deadline':
        return '⏰'
      case 'task':
        return '📋'
      case 'project':
        return '📁'
      default:
        return '🔔'
    }
  }

  const formatTime = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const minutes = Math.floor(diff / 60000)
    const hours = Math.floor(diff / 3600000)
    const days = Math.floor(diff / 86400000)

    if (minutes < 1) return 'только что'
    if (minutes < 60) return `${minutes} мин назад`
    if (hours < 24) return `${hours} ч назад`
    if (days < 7) return `${days} дн назад`
    return date.toLocaleDateString('ru-RU')
  }

  return (
    <div className={styles.container} ref={dropdownRef}>
      <button 
        className={styles.bellButton}
        onClick={handleToggle}
        aria-label="Уведомления"
      >
        <span className={styles.bellIcon}>🔔</span>
        {unreadCount > 0 && (
          <span className={styles.badge}>{unreadCount > 99 ? '99+' : unreadCount}</span>
        )}
        {unreadCount > 0 && (
          <span className={styles.pulse}></span>
        )}
      </button>

      {isOpen && (
        <div className={styles.dropdown}>
          <div className={styles.dropdownHeader}>
            <h3>Уведомления</h3>
            {unreadCount > 0 && (
              <button 
                className={styles.markAllRead}
                onClick={handleMarkAllRead}
              >
                Отметить все прочитанными
              </button>
            )}
          </div>

          <div className={styles.notificationsList}>
            {loading ? (
              <div className={styles.loading}>Загрузка...</div>
            ) : notifications.length === 0 ? (
              <div className={styles.empty}>Нет уведомлений</div>
            ) : (
              notifications.map((notification) => (
                <div
                  key={notification.id}
                  className={`${styles.notification} ${!notification.read ? styles.unread : ''}`}
                  onClick={() => handleNotificationClick(notification)}
                  data-type={notification.type}
                >
                  <div className={styles.notificationIcon}>
                    {getNotificationIcon(notification.type)}
                  </div>
                  <div className={styles.notificationContent}>
                    <div className={styles.notificationTitle}>
                      {notification.title}
                    </div>
                    <div className={styles.notificationMessage}>
                      {notification.message}
                    </div>
                    <div className={styles.notificationTime}>
                      {formatTime(notification.created_at)}
                    </div>
                  </div>
                  {!notification.read && (
                    <div className={styles.unreadDot}></div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}

'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import styles from './LayoutWrapper.module.css'

export default function LayoutWrapper({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()

  return (
    <>
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.headerContent}>
          <Link href="/" className={styles.logo}>
            <span>🤖</span>
            <span>HR2137 Bot</span>
          </Link>
          <span className={styles.statusBadge}>Live</span>
        </div>
      </div>
      
      {/* Layout */}
      <div className={styles.layout}>
        {/* Sidebar */}
        <aside className={styles.sidebar}>
          <div className={styles.sidebarSection}>
            <div className={styles.sidebarTitle}>Навигация</div>
            <Link 
              href="/" 
              className={`${styles.navItem} ${pathname === '/' ? styles.navItemActive : ''}`}
            >
              <span className={styles.navIcon}>🏠</span>
              <span>Главная</span>
            </Link>
            <Link 
              href="/architecture" 
              className={`${styles.navItem} ${pathname === '/architecture' ? styles.navItemActive : ''}`}
            >
              <span className={styles.navIcon}>🏗️</span>
              <span>Архитектура</span>
            </Link>
          </div>
          
          <div className={styles.sidebarSection}>
            <div className={styles.sidebarTitle}>Функции</div>
            <Link 
              href="/rag" 
              className={`${styles.navItem} ${pathname === '/rag' ? styles.navItemActive : ''}`}
            >
              <span className={styles.navIcon}>📊</span>
              <span>RAG Dashboard</span>
            </Link>
          </div>
          
          <div className={styles.sidebarSection}>
            <div className={styles.sidebarTitle}>Эксперименты</div>
            <Link 
              href="/experiments" 
              className={`${styles.navItem} ${pathname === '/experiments' ? styles.navItemActive : ''}`}
            >
              <span className={styles.navIcon}>🧪</span>
              <span>Эксперименты</span>
            </Link>
          </div>
          
          <div className={styles.sidebarSection}>
            <div className={styles.sidebarTitle}>Информация</div>
            <div style={{ padding: '10px 12px', color: '#65676b', fontSize: '13px', lineHeight: '1.5' }}>
              AI-ассистент для консалтинговой практики. Демонстрационный интерфейс для инвесторов.
            </div>
          </div>
        </aside>
        
        {/* Main Content */}
        <main className={styles.mainContent}>
          {children}
        </main>
      </div>
    </>
  )
}


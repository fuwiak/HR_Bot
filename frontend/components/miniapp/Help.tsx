'use client'

import { WebApp } from '@twa-dev/sdk'
import styles from './Help.module.css'

interface HelpProps {
  onBack: () => void
}

export default function Help({ onBack }: HelpProps) {
  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <button className={styles.backButton} onClick={onBack}>
          ← Назад
        </button>
        <h1>❓ Помощь</h1>
      </div>

      <div className={styles.content}>
        <div className={styles.section}>
          <h2>🏠 Основные команды</h2>
          <div className={styles.commandList}>
            <div className={styles.commandItem}>
              <code>/start</code>
              <span>Главное меню</span>
            </div>
            <div className={styles.commandItem}>
              <code>/menu</code>
              <span>Главное меню</span>
            </div>
          </div>
        </div>

        <div className={styles.section}>
          <h2>📚 База знаний</h2>
          <div className={styles.commandList}>
            <div className={styles.commandItem}>
              <code>/rag_search [запрос]</code>
              <span>Поиск в базе знаний</span>
            </div>
            <div className={styles.commandItem}>
              <code>/rag_stats</code>
              <span>Статистика базы</span>
            </div>
            <div className={styles.commandItem}>
              <code>/rag_docs</code>
              <span>Список документов</span>
            </div>
          </div>
        </div>

        <div className={styles.section}>
          <h2>📋 Проекты</h2>
          <div className={styles.commandList}>
            <div className={styles.commandItem}>
              <code>/weeek_projects</code>
              <span>Список проектов</span>
            </div>
            <div className={styles.commandItem}>
              <code>/weeek_create_project [название]</code>
              <span>Создать проект</span>
            </div>
            <div className={styles.commandItem}>
              <code>/weeek_task [проект] | [задача]</code>
              <span>Создать задачу</span>
            </div>
            <div className={styles.commandItem}>
              <code>/status</code>
              <span>Статус проектов</span>
            </div>
          </div>
        </div>

        <div className={styles.section}>
          <h2>🛠 Инструменты</h2>
          <div className={styles.commandList}>
            <div className={styles.commandItem}>
              <code>/demo_proposal [запрос]</code>
              <span>Генерация КП</span>
            </div>
            <div className={styles.commandItem}>
              <code>/summary [проект]</code>
              <span>Суммаризация проекта</span>
            </div>
          </div>
        </div>

        <div className={styles.footer}>
          <p>💡 Используйте Mini App для удобного доступа ко всем функциям</p>
        </div>
      </div>
    </div>
  )
}

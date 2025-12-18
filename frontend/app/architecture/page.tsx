'use client'

import { useEffect } from 'react'
import styles from './page.module.css'

declare global {
  interface Window {
    mermaid: {
      initialize: (config: any) => void
      contentLoaded: () => void
    }
  }
}

export default function ArchitecturePage() {
  useEffect(() => {
    const script = document.createElement('script')
    script.src = 'https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js'
    script.onload = () => {
      if (window.mermaid) {
        window.mermaid.initialize({
          startOnLoad: true,
          theme: 'default',
          themeVariables: {
            primaryColor: '#1877f2',
            primaryTextColor: '#1c1e21',
            primaryBorderColor: '#1877f2',
            lineColor: '#8b9dc3',
            secondaryColor: '#f0f2f5',
            tertiaryColor: '#fff',
          },
        })
        window.mermaid.contentLoaded()
      }
    }
    document.body.appendChild(script)

    return () => {
      if (document.body.contains(script)) {
        document.body.removeChild(script)
      }
    }
  }, [])

  const mermaidDiagram = `graph TB
    subgraph "Входные источники лидов"
        HRTime[HR Time API]
        Email[Yandex Email<br/>IMAP/SMTP]
        Website[Сайт-визитка<br/>Webhook]
    end
    
    subgraph "Telegram Bot - Async Hub"
        Bot[Telegram Bot<br/>Async Handlers]
        WebUI[Веб-интерфейс<br/>для демонстрации]
    end
    
    subgraph "LLM Слой"
        DeepSeek[DeepSeek Chat<br/>через OpenRouter<br/>Основной]
        GigaChat[GigaChat<br/>Fallback<br/>Российское решение]
    end
    
    subgraph "RAG База знаний"
        Qdrant[Qdrant OSS<br/>Векторная БД]
        QwenEmbed[Qwen3-Embedding-8B<br/>через OpenRouter]
        KnowledgeBase[Документы<br/>Word/Excel/PDF]
    end
    
    subgraph "Интеграции"
        Weeek[WEEEK API<br/>Проекты/Задачи]
    end
    
    HRTime -->|Async polling| Bot
    Email -->|Async polling| Bot
    Website -->|Webhook| Bot
    
    Bot -->|Async requests| DeepSeek
    DeepSeek -->|Fallback| GigaChat
    
    Bot -->|Semantic search| Qdrant
    QwenEmbed -->|Генерация эмбеддингов| Qdrant
    KnowledgeBase -->|Индексация| Qdrant
    
    Qdrant -->|RAG контекст| Bot
    Bot -->|Создание проектов| Weeek
    Bot -->|Уведомления| WebUI`

  return (
    <div className={styles.contentCard}>
      <h1>🏗️ Архитектура системы</h1>
      <p className={styles.subtitle}>Техническая архитектура AI-ассистента HR2137 Bot</p>
      
      <div className={styles.mermaidContainer}>
        <div className="mermaid">{mermaidDiagram}</div>
      </div>
      
      <div className={styles.techStack}>
        <div className={styles.techCard}>
          <h3>LLM для генерации ответов</h3>
          <ul>
            <li>Primary: DeepSeek Chat (OpenRouter)</li>
            <li>Fallback: GigaChat</li>
          </ul>
        </div>
        
        <div className={styles.techCard}>
          <h3>Эмбеддинги для RAG</h3>
          <ul>
            <li>Модель: Qwen3-Embedding-8B</li>
            <li>Через OpenRouter API</li>
          </ul>
        </div>
        
        <div className={styles.techCard}>
          <h3>Векторная БД</h3>
          <ul>
            <li>Qdrant Opensource</li>
            <li>Cloud или Self-hosted</li>
          </ul>
        </div>
        
        <div className={styles.techCard}>
          <h3>Веб-фреймворк</h3>
          <ul>
            <li>FastAPI</li>
            <li>Uvicorn</li>
          </ul>
        </div>
        
        <div className={styles.techCard}>
          <h3>Telegram Bot</h3>
          <ul>
            <li>python-telegram-bot</li>
            <li>Async handlers</li>
            <li>Webhook/Polling</li>
          </ul>
        </div>
        
        <div className={styles.techCard}>
          <h3>Интеграции</h3>
          <ul>
            <li>WEEEK API</li>
            <li>Yandex Email</li>
            <li>HR Time API</li>
          </ul>
        </div>
      </div>
    </div>
  )
}


'use client'

import { useState } from 'react'
import styles from './Chat.module.css'

interface ChatProps {
  onBack: () => void
}

export default function Chat({ onBack }: ChatProps) {
  const [message, setMessage] = useState('')
  const [messages, setMessages] = useState<Array<{role: 'user' | 'assistant', text: string}>>([])
  const [loading, setLoading] = useState(false)

  const handleSend = async () => {
    if (!message.trim()) return

    const userMessage = message
    setMessage('')
    setMessages(prev => [...prev, { role: 'user', text: userMessage }])
    setLoading(true)

    // TODO: Implement API call to backend chat endpoint
    setTimeout(() => {
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        text: 'Функция чата будет доступна в следующей версии. Пока используйте команды в боте.' 
      }])
      setLoading(false)
    }, 1000)
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <button className={styles.backButton} onClick={onBack}>
          ← Назад
        </button>
        <h1>💬 Чат с AI</h1>
      </div>

      <div className={styles.messages}>
        {messages.length === 0 && (
          <div className={styles.empty}>
            <p>Начните общение с AI-помощником</p>
            <p className={styles.hint}>
              Ассистент использует базу знаний для формирования ответов
            </p>
          </div>
        )}
        
        {messages.map((msg, idx) => (
          <div key={idx} className={`${styles.message} ${styles[msg.role]}`}>
            <p>{msg.text}</p>
          </div>
        ))}
        
        {loading && (
          <div className={`${styles.message} ${styles.assistant}`}>
            <div className={styles.typing}>⏳ Печатает...</div>
          </div>
        )}
      </div>

      <div className={styles.inputArea}>
        <input
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSend()}
          placeholder="Введите сообщение..."
          className={styles.input}
          disabled={loading}
        />
        <button
          className={styles.sendButton}
          onClick={handleSend}
          disabled={loading || !message.trim()}
        >
          ➤
        </button>
      </div>
    </div>
  )
}

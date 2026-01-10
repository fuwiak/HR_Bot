'use client'

import { useState, useEffect } from 'react'
import { useWebApp } from '@/lib/useWebApp'
import { getYadiskFiles, searchYadiskFiles, getYadiskRecent } from '@/lib/api'
import styles from './YandexDisk.module.css'

interface YandexDiskProps {
  onBack: () => void
}

interface FileItem {
  name: string
  type: 'file' | 'dir'
  path: string
  size?: number
  modified?: string
}

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Б'
  const k = 1024
  const sizes = ['Б', 'КБ', 'МБ', 'ГБ']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

const getFileIcon = (name: string, type: string): string => {
  if (type === 'dir') return '📁'
  const ext = name.split('.').pop()?.toLowerCase() || ''
  const icons: Record<string, string> = {
    pdf: '📕',
    doc: '📝',
    docx: '📝',
    xls: '📊',
    xlsx: '📊',
    ppt: '📈',
    pptx: '📈',
    jpg: '🖼',
    jpeg: '🖼',
    png: '🖼',
    gif: '🖼',
    zip: '📦',
    rar: '📦',
    py: '🐍',
    js: '💛',
    ts: '💙',
    txt: '📄',
  }
  return icons[ext] || '📄'
}

export default function YandexDisk({ onBack }: YandexDiskProps) {
  const WebApp = useWebApp()
  const [activeTab, setActiveTab] = useState<'browse' | 'search' | 'recent'>('browse')
  const [currentPath, setCurrentPath] = useState('/')
  const [files, setFiles] = useState<FileItem[]>([])
  const [recentFiles, setRecentFiles] = useState<FileItem[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<FileItem[]>([])
  const [loading, setLoading] = useState(false)
  const [diskInfo, setDiskInfo] = useState<{ total: number; used: number } | null>(null)

  const loadFiles = async (path: string = '/') => {
    setLoading(true)
    try {
      const result = await getYadiskFiles(path)
      setFiles(result.items || [])
      if (result.disk_info) {
        setDiskInfo({
          total: result.disk_info.total_space,
          used: result.disk_info.used_space
        })
      }
      setCurrentPath(path)
    } catch (error: any) {
      WebApp?.showAlert(error.message || 'Ошибка загрузки файлов')
      setFiles([])
    } finally {
      setLoading(false)
    }
  }

  const loadRecent = async () => {
    setLoading(true)
    try {
      const result = await getYadiskRecent()
      setRecentFiles(result.files || [])
    } catch (error: any) {
      WebApp?.showAlert(error.message || 'Ошибка загрузки последних файлов')
      setRecentFiles([])
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = async () => {
    if (!searchQuery.trim()) return
    
    setLoading(true)
    WebApp?.HapticFeedback?.impactOccurred('light')
    
    try {
      const result = await searchYadiskFiles(searchQuery)
      setSearchResults(result.files || [])
    } catch (error: any) {
      WebApp?.showAlert(error.message || 'Ошибка поиска')
      setSearchResults([])
    } finally {
      setLoading(false)
    }
  }

  const handleFolderClick = (folder: FileItem) => {
    WebApp?.HapticFeedback?.impactOccurred('light')
    loadFiles(folder.path)
  }

  const handleGoBack = () => {
    if (currentPath === '/') return
    const parentPath = currentPath.split('/').slice(0, -1).join('/') || '/'
    loadFiles(parentPath)
  }

  useEffect(() => {
    if (activeTab === 'browse') {
      loadFiles(currentPath)
    } else if (activeTab === 'recent') {
      loadRecent()
    }
  }, [activeTab])

  const formatDate = (dateStr: string): string => {
    try {
      const date = new Date(dateStr)
      return date.toLocaleDateString('ru-RU', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      })
    } catch {
      return dateStr
    }
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <button className={styles.backButton} onClick={onBack}>
          ← Назад
        </button>
        <h1>☁️ Яндекс.Диск</h1>
      </div>

      {diskInfo && (
        <div className={styles.diskInfo}>
          <div className={styles.diskBar}>
            <div 
              className={styles.diskUsed} 
              style={{ width: `${(diskInfo.used / diskInfo.total) * 100}%` }}
            />
          </div>
          <p>
            💾 {formatFileSize(diskInfo.used)} из {formatFileSize(diskInfo.total)}
          </p>
        </div>
      )}

      <div className={styles.tabs}>
        <button
          className={`${styles.tab} ${activeTab === 'browse' ? styles.active : ''}`}
          onClick={() => setActiveTab('browse')}
        >
          📂 Обзор
        </button>
        <button
          className={`${styles.tab} ${activeTab === 'search' ? styles.active : ''}`}
          onClick={() => setActiveTab('search')}
        >
          🔍 Поиск
        </button>
        <button
          className={`${styles.tab} ${activeTab === 'recent' ? styles.active : ''}`}
          onClick={() => setActiveTab('recent')}
        >
          🕐 Последние
        </button>
      </div>

      <div className={styles.content}>
        {activeTab === 'browse' && (
          <div className={styles.browseTab}>
            <div className={styles.pathBar}>
              <span className={styles.pathLabel}>📁 Путь:</span>
              <span className={styles.pathValue}>{currentPath}</span>
              {currentPath !== '/' && (
                <button className={styles.upButton} onClick={handleGoBack}>
                  ⬆️ Вверх
                </button>
              )}
            </div>

            {loading ? (
              <div className={styles.loading}>⏳ Загрузка...</div>
            ) : files.length > 0 ? (
              <div className={styles.filesList}>
                {files.map((file, idx) => (
                  <div 
                    key={idx} 
                    className={`${styles.fileItem} ${file.type === 'dir' ? styles.folder : ''}`}
                    onClick={() => file.type === 'dir' && handleFolderClick(file)}
                  >
                    <span className={styles.fileIcon}>
                      {getFileIcon(file.name, file.type)}
                    </span>
                    <div className={styles.fileInfo}>
                      <h4>{file.name}</h4>
                      {file.type === 'file' && file.size && (
                        <p>{formatFileSize(file.size)}</p>
                      )}
                    </div>
                    {file.type === 'dir' && (
                      <span className={styles.chevron}>›</span>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className={styles.empty}>
                <p>📂 Папка пуста</p>
              </div>
            )}
          </div>
        )}

        {activeTab === 'search' && (
          <div className={styles.searchTab}>
            <div className={styles.searchBox}>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Поиск файлов..."
                className={styles.input}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              />
              <button 
                className={styles.searchButton}
                onClick={handleSearch}
                disabled={loading}
              >
                {loading ? '⏳' : '🔍'}
              </button>
            </div>

            {searchResults.length > 0 && (
              <div className={styles.filesList}>
                <p className={styles.resultsCount}>
                  Найдено: {searchResults.length} файлов
                </p>
                {searchResults.map((file, idx) => (
                  <div key={idx} className={styles.fileItem}>
                    <span className={styles.fileIcon}>
                      {getFileIcon(file.name, file.type)}
                    </span>
                    <div className={styles.fileInfo}>
                      <h4>{file.name}</h4>
                      <p className={styles.filePath}>{file.path}</p>
                      {file.size && (
                        <p>{formatFileSize(file.size)}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'recent' && (
          <div className={styles.recentTab}>
            {loading ? (
              <div className={styles.loading}>⏳ Загрузка...</div>
            ) : recentFiles.length > 0 ? (
              <div className={styles.filesList}>
                {recentFiles.map((file, idx) => (
                  <div key={idx} className={styles.fileItem}>
                    <span className={styles.fileIcon}>
                      {getFileIcon(file.name, file.type)}
                    </span>
                    <div className={styles.fileInfo}>
                      <h4>{file.name}</h4>
                      {file.modified && (
                        <p className={styles.fileDate}>{formatDate(file.modified)}</p>
                      )}
                      {file.size && (
                        <p>{formatFileSize(file.size)}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className={styles.empty}>
                <p>🕐 Нет последних файлов</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

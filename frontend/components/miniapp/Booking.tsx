'use client'

import { useState, useEffect } from 'react'
import { useWebApp } from '@/lib/useWebApp'
import { getServices, getMasters, createBooking } from '@/lib/api'
import styles from './Booking.module.css'

interface BookingProps {
  onBack: () => void
  userId?: string
}

interface Service {
  id: string
  name: string
  price: number
  duration: number
  category?: string
}

interface Master {
  id: string
  name: string
  specialization?: string
}

export default function Booking({ onBack, userId }: BookingProps) {
  const WebApp = useWebApp()
  const [activeTab, setActiveTab] = useState<'services' | 'book' | 'my'>('services')
  const [services, setServices] = useState<Service[]>([])
  const [masters, setMasters] = useState<Master[]>([])
  const [loading, setLoading] = useState(false)
  
  // Booking form state
  const [selectedService, setSelectedService] = useState<Service | null>(null)
  const [selectedMaster, setSelectedMaster] = useState<Master | null>(null)
  const [selectedDate, setSelectedDate] = useState('')
  const [selectedTime, setSelectedTime] = useState('')
  const [bookingStep, setBookingStep] = useState<'service' | 'master' | 'datetime' | 'confirm'>('service')

  const loadServices = async () => {
    setLoading(true)
    try {
      const result = await getServices()
      setServices(result.services || [])
    } catch (error: any) {
      console.error('Ошибка загрузки услуг:', error)
      setServices([])
    } finally {
      setLoading(false)
    }
  }

  const loadMasters = async () => {
    setLoading(true)
    try {
      const result = await getMasters()
      setMasters(result.masters || [])
    } catch (error: any) {
      console.error('Ошибка загрузки специалистов:', error)
      setMasters([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadServices()
    loadMasters()
  }, [])

  const handleServiceSelect = (service: Service) => {
    WebApp?.HapticFeedback?.impactOccurred('light')
    setSelectedService(service)
    setBookingStep('master')
    setActiveTab('book')
  }

  const handleMasterSelect = (master: Master) => {
    WebApp?.HapticFeedback?.impactOccurred('light')
    setSelectedMaster(master)
    setBookingStep('datetime')
  }

  const handleDateTimeConfirm = () => {
    if (!selectedDate || !selectedTime) {
      WebApp?.showAlert('Выберите дату и время')
      return
    }
    WebApp?.HapticFeedback?.impactOccurred('light')
    setBookingStep('confirm')
  }

  const handleBookingSubmit = async () => {
    if (!selectedService || !selectedMaster || !selectedDate || !selectedTime) {
      WebApp?.showAlert('Заполните все поля')
      return
    }

    setLoading(true)
    WebApp?.HapticFeedback?.impactOccurred('medium')
    
    try {
      await createBooking({
        service: selectedService.name,
        master: selectedMaster.name,
        date: selectedDate,
        time: selectedTime,
        userId: userId || 'miniapp_user'
      })
      
      WebApp?.showAlert('✅ Запись успешно создана!')
      
      // Reset form
      setSelectedService(null)
      setSelectedMaster(null)
      setSelectedDate('')
      setSelectedTime('')
      setBookingStep('service')
      setActiveTab('services')
    } catch (error: any) {
      WebApp?.showAlert(error.message || 'Ошибка создания записи')
    } finally {
      setLoading(false)
    }
  }

  const resetBooking = () => {
    setSelectedService(null)
    setSelectedMaster(null)
    setSelectedDate('')
    setSelectedTime('')
    setBookingStep('service')
  }

  const formatPrice = (price: number): string => {
    return new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency: 'RUB',
      minimumFractionDigits: 0
    }).format(price)
  }

  // Generate available time slots
  const timeSlots = ['09:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00', '18:00']

  // Get min date (today)
  const today = new Date().toISOString().split('T')[0]

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <button className={styles.backButton} onClick={onBack}>
          ← Назад
        </button>
        <h1>📅 Запись на услуги</h1>
      </div>

      <div className={styles.tabs}>
        <button
          className={`${styles.tab} ${activeTab === 'services' ? styles.active : ''}`}
          onClick={() => { setActiveTab('services'); resetBooking() }}
        >
          📋 Услуги
        </button>
        <button
          className={`${styles.tab} ${activeTab === 'book' ? styles.active : ''}`}
          onClick={() => setActiveTab('book')}
        >
          ✏️ Запись
        </button>
      </div>

      <div className={styles.content}>
        {activeTab === 'services' && (
          <div className={styles.servicesTab}>
            {loading ? (
              <div className={styles.loading}>⏳ Загрузка услуг...</div>
            ) : services.length > 0 ? (
              <div className={styles.servicesList}>
                {services.map((service, idx) => (
                  <div key={idx} className={styles.serviceCard}>
                    <div className={styles.serviceInfo}>
                      <h3>{service.name}</h3>
                      {service.category && (
                        <p className={styles.category}>🏷 {service.category}</p>
                      )}
                      <div className={styles.serviceDetails}>
                        <span className={styles.price}>{formatPrice(service.price)}</span>
                        {service.duration && (
                          <span className={styles.duration}>⏱ {service.duration} мин</span>
                        )}
                      </div>
                    </div>
                    <button 
                      className={styles.bookButton}
                      onClick={() => handleServiceSelect(service)}
                    >
                      Записаться
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <div className={styles.empty}>
                <p>📋 Услуги не найдены</p>
                <p className={styles.hint}>Попробуйте обновить страницу</p>
              </div>
            )}
          </div>
        )}

        {activeTab === 'book' && (
          <div className={styles.bookTab}>
            {/* Progress indicator */}
            <div className={styles.progress}>
              <div className={`${styles.step} ${bookingStep === 'service' || selectedService ? styles.completed : ''}`}>
                1. Услуга
              </div>
              <div className={`${styles.step} ${bookingStep === 'master' || selectedMaster ? styles.completed : ''}`}>
                2. Специалист
              </div>
              <div className={`${styles.step} ${bookingStep === 'datetime' || (selectedDate && selectedTime) ? styles.completed : ''}`}>
                3. Дата/Время
              </div>
              <div className={`${styles.step} ${bookingStep === 'confirm' ? styles.completed : ''}`}>
                4. Подтверждение
              </div>
            </div>

            {/* Step: Select Service */}
            {bookingStep === 'service' && (
              <div className={styles.stepContent}>
                <h3>Выберите услугу</h3>
                {services.length > 0 ? (
                  <div className={styles.optionsList}>
                    {services.map((service, idx) => (
                      <button
                        key={idx}
                        className={styles.optionCard}
                        onClick={() => handleServiceSelect(service)}
                      >
                        <span className={styles.optionName}>{service.name}</span>
                        <span className={styles.optionPrice}>{formatPrice(service.price)}</span>
                      </button>
                    ))}
                  </div>
                ) : (
                  <p className={styles.noOptions}>Услуги не найдены</p>
                )}
              </div>
            )}

            {/* Step: Select Master */}
            {bookingStep === 'master' && (
              <div className={styles.stepContent}>
                <div className={styles.selectedInfo}>
                  <span>✅ Услуга: {selectedService?.name}</span>
                </div>
                <h3>Выберите специалиста</h3>
                {masters.length > 0 ? (
                  <div className={styles.optionsList}>
                    {masters.map((master, idx) => (
                      <button
                        key={idx}
                        className={styles.optionCard}
                        onClick={() => handleMasterSelect(master)}
                      >
                        <span className={styles.optionName}>{master.name}</span>
                        {master.specialization && (
                          <span className={styles.optionSub}>{master.specialization}</span>
                        )}
                      </button>
                    ))}
                  </div>
                ) : (
                  <div className={styles.optionsList}>
                    <button
                      className={styles.optionCard}
                      onClick={() => handleMasterSelect({ id: 'anastasia', name: 'Анастасия Новосёлова' })}
                    >
                      <span className={styles.optionName}>Анастасия Новосёлова</span>
                      <span className={styles.optionSub}>HR-консультант</span>
                    </button>
                  </div>
                )}
                <button className={styles.backStepButton} onClick={() => setBookingStep('service')}>
                  ← Назад к услугам
                </button>
              </div>
            )}

            {/* Step: Select Date/Time */}
            {bookingStep === 'datetime' && (
              <div className={styles.stepContent}>
                <div className={styles.selectedInfo}>
                  <span>✅ Услуга: {selectedService?.name}</span>
                  <span>✅ Специалист: {selectedMaster?.name}</span>
                </div>
                <h3>Выберите дату и время</h3>
                
                <div className={styles.dateTimeForm}>
                  <label>Дата:</label>
                  <input
                    type="date"
                    value={selectedDate}
                    onChange={(e) => setSelectedDate(e.target.value)}
                    min={today}
                    className={styles.dateInput}
                  />
                  
                  <label>Время:</label>
                  <div className={styles.timeSlots}>
                    {timeSlots.map((time) => (
                      <button
                        key={time}
                        className={`${styles.timeSlot} ${selectedTime === time ? styles.selected : ''}`}
                        onClick={() => setSelectedTime(time)}
                      >
                        {time}
                      </button>
                    ))}
                  </div>
                </div>

                <button 
                  className={styles.nextButton}
                  onClick={handleDateTimeConfirm}
                  disabled={!selectedDate || !selectedTime}
                >
                  Далее →
                </button>
                <button className={styles.backStepButton} onClick={() => setBookingStep('master')}>
                  ← Назад к специалистам
                </button>
              </div>
            )}

            {/* Step: Confirm */}
            {bookingStep === 'confirm' && (
              <div className={styles.stepContent}>
                <h3>Подтверждение записи</h3>
                
                <div className={styles.confirmCard}>
                  <div className={styles.confirmRow}>
                    <span className={styles.confirmLabel}>📋 Услуга:</span>
                    <span className={styles.confirmValue}>{selectedService?.name}</span>
                  </div>
                  <div className={styles.confirmRow}>
                    <span className={styles.confirmLabel}>👤 Специалист:</span>
                    <span className={styles.confirmValue}>{selectedMaster?.name}</span>
                  </div>
                  <div className={styles.confirmRow}>
                    <span className={styles.confirmLabel}>📅 Дата:</span>
                    <span className={styles.confirmValue}>{selectedDate}</span>
                  </div>
                  <div className={styles.confirmRow}>
                    <span className={styles.confirmLabel}>🕐 Время:</span>
                    <span className={styles.confirmValue}>{selectedTime}</span>
                  </div>
                  <div className={styles.confirmRow}>
                    <span className={styles.confirmLabel}>💰 Стоимость:</span>
                    <span className={styles.confirmValue}>{selectedService && formatPrice(selectedService.price)}</span>
                  </div>
                </div>

                <button 
                  className={styles.confirmButton}
                  onClick={handleBookingSubmit}
                  disabled={loading}
                >
                  {loading ? '⏳ Создание записи...' : '✅ Подтвердить запись'}
                </button>
                <button className={styles.backStepButton} onClick={() => setBookingStep('datetime')}>
                  ← Изменить дату/время
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

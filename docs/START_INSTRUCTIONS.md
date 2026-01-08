# Инструкция по запуску Backend и Frontend

## Запуск в 2 отдельных терминалах

### Терминал 1 - Backend (FastAPI)

```bash
cd /Users/user/HR_Bot
python web_interface.py
```

Backend будет доступен на: http://localhost:8081

### Терминал 2 - Frontend (Next.js)

```bash
cd /Users/user/HR_Bot/frontend
npm run dev
```

Frontend будет доступен на: http://localhost:3000

---

## Альтернатива: Использовать скрипты

### Терминал 1
```bash
cd /Users/user/HR_Bot
./start_backend.sh
```

### Терминал 2
```bash
cd /Users/user/HR_Bot
./start_frontend.sh
```

---

## Проверка работы

- Backend: http://localhost:8081/health
- Frontend: http://localhost:3000
- RAG Dashboard: http://localhost:3000/rag

---

## Остановка

В каждом терминале нажмите `Ctrl+C`

Или используйте:
```bash
pkill -f "web_interface.py"
pkill -f "next dev"
```
























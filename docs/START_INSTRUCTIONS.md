# Инструкция по запуску Backend и AnythingLLM (Frontend)

## Запуск в 2 отдельных терминалах

### Терминал 1 - Backend (FastAPI)

```bash
cd /Users/user/HR_Bot
python web_interface.py
```

Backend будет доступен на: http://localhost:8081

### Терминал 2 - Frontend (AnythingLLM)

Сервис Frontend в репозитории — это AnythingLLM (не Next.js). Запуск через Docker:

```bash
cd /Users/user/HR_Bot
docker build -f frontend/Dockerfile -t anythingllm frontend/
docker run -d -p 3001:3001 -v anythingllm_storage:/app/server/storage --name anythingllm anythingllm
```

AnythingLLM будет доступен на: http://localhost:3001

---

## Альтернатива: Использовать скрипты

### Терминал 1
```bash
cd /Users/user/HR_Bot
./start_backend.sh
```

### Терминал 2 (AnythingLLM)
```bash
docker run -d -p 3001:3001 -v anythingllm_storage:/app/server/storage --name anythingllm mintplexlabs/anythingllm
```

---

## Проверка работы

- Backend: http://localhost:8081/health
- AnythingLLM (Web UI RAG): http://localhost:3001

---

## Остановка

- Backend: в терминале `Ctrl+C` или `pkill -f "web_interface.py"`
- AnythingLLM: `docker stop anythingllm`
























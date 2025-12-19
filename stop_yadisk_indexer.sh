#!/bin/sh
# Остановка Yandex Disk Indexer

if [ -f yadisk_indexer.pid ]; then
    PID=$(cat yadisk_indexer.pid)
    
    if ps -p $PID > /dev/null; then
        echo "🛑 Остановка Yandex Disk Indexer (PID: $PID)..."
        kill $PID
        sleep 2
        
        if ps -p $PID > /dev/null; then
            echo "⚠️ Принудительная остановка..."
            kill -9 $PID
        fi
        
        echo "✅ Yandex Disk Indexer остановлен"
    else
        echo "⚠️ Процесс не запущен"
    fi
    
    rm yadisk_indexer.pid
else
    echo "⚠️ PID файл не найден"
fi

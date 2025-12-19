#!/bin/bash
# Sprawdzenie zmiennych środowiskowych

echo "🔍 Sprawdzanie zmiennych w .env..."
echo ""

# Funkcja sprawdzająca zmienną
check_var() {
    local var_name=$1
    local var_value=$(grep "^${var_name}=" .env 2>/dev/null | cut -d= -f2-)
    
    if [ -n "$var_value" ]; then
        local length=${#var_value}
        echo "✅ $var_name: ustawiony ($length znaków)"
    else
        echo "❌ $var_name: BRAK!"
    fi
}

# Sprawdzamy wymagane zmienne
echo "📋 Zmienne dla Yandex Disk Indexer:"
echo "─────────────────────────────────────"
check_var "YANDEX_TOKEN"
check_var "QDRANT_URL"
check_var "QDRANT_API_KEY"

# Sprawdzamy embedding API (OpenRouter lub OpenAI)
if grep -q "^OPENROUTER_API_KEY=" .env 2>/dev/null; then
    check_var "OPENROUTER_API_KEY"
elif grep -q "^OPENAI_API_KEY=" .env 2>/dev/null; then
    check_var "OPENAI_API_KEY"
else
    echo "❌ OPENROUTER_API_KEY lub OPENAI_API_KEY: BRAK!"
fi

echo ""
echo "📋 Opcjonalne zmienne:"
echo "─────────────────────────────────────"
check_var "YADISK_WATCH_FOLDERS"
check_var "YADISK_SCAN_INTERVAL"
check_var "QDRANT_COLLECTION"

echo ""
echo "─────────────────────────────────────"

# Sprawdź czy wszystkie wymagane są ustawione
if grep -q "^YANDEX_TOKEN=" .env && \
   grep -q "^QDRANT_URL=" .env && \
   grep -q "^QDRANT_API_KEY=" .env && \
   (grep -q "^OPENROUTER_API_KEY=" .env || grep -q "^OPENAI_API_KEY=" .env); then
    echo "✅ Wszystkie wymagane zmienne ustawione!"
    echo ""
    echo "💡 Możesz uruchomić indexator:"
    echo "   ./start_yadisk_indexer.sh"
else
    echo "❌ Brakuje wymaganych zmiennych!"
    echo ""
    echo "📝 Dodaj do .env:"
    
    if ! grep -q "^QDRANT_URL=" .env; then
        echo "   QDRANT_URL=https://your-cluster.aws.cloud.qdrant.io"
    fi
    
    if ! grep -q "^QDRANT_API_KEY=" .env; then
        echo "   QDRANT_API_KEY=your_api_key_here"
    fi
    
    if ! grep -q "^YANDEX_TOKEN=" .env; then
        echo "   YANDEX_TOKEN=your_token_here"
    fi
    
    if ! grep -q "^OPENROUTER_API_KEY=" .env && ! grep -q "^OPENAI_API_KEY=" .env; then
        echo "   OPENROUTER_API_KEY=your_openrouter_key_here"
        echo "   # Lub:"
        echo "   # OPENAI_API_KEY=your_openai_key_here"
    fi
fi

echo ""

#!/bin/bash
# Eksport wszystkich zmiennych z Railway dla wszystkich serwisów

echo "🔍 Eksportowanie zmiennych z Railway..."
echo ""

# Pobierz listę serwisów
SERVICES=$(railway status --json | jq -r '.services.edges[].node.name' 2>/dev/null)

if [ -z "$SERVICES" ]; then
    echo "❌ Nie znaleziono serwisów"
    exit 1
fi

echo "📋 Znalezione serwisy:"
echo "$SERVICES"
echo ""

# Eksportuj zmienne dla każdego serwisu
ALL_VARS="{}"
for SERVICE in $SERVICES; do
    echo "📦 Eksportowanie zmiennych dla serwisu: $SERVICE"
    railway link -s "$SERVICE" > /dev/null 2>&1
    SERVICE_VARS=$(railway variables --json 2>/dev/null)
    
    if [ ! -z "$SERVICE_VARS" ]; then
        # Dodaj zmienne do głównego obiektu z nazwą serwisu jako kluczem
        ALL_VARS=$(echo "$ALL_VARS" | jq --arg svc "$SERVICE" --argjson vars "$SERVICE_VARS" '. + {($svc): $vars}' 2>/dev/null)
        VAR_COUNT=$(echo "$SERVICE_VARS" | jq 'length' 2>/dev/null)
        echo "  ✅ $SERVICE - $VAR_COUNT zmiennych"
    else
        echo "  ⚠️  $SERVICE - brak zmiennych"
    fi
done

# Zapisz do pliku
echo "$ALL_VARS" | jq '.' > railway-all-variables.json
echo ""
echo "✅ Wszystkie zmienne zapisane do: railway-all-variables.json"
echo "📊 Statystyki:"
jq 'to_entries | map({service: .key, count: (.value | length)})' railway-all-variables.json

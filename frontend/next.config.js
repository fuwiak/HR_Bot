/** @type {import('next').Config} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone', // Для Docker деплоя на Railway
  
  // Настройки для Telegram Mini App
  async headers() {
    return [
      {
        source: '/miniapp/:path*',
        headers: [
          {
            key: 'X-Frame-Options',
            value: 'SAMEORIGIN',
          },
          {
            key: 'Content-Security-Policy',
            value: "frame-ancestors 'self' https://web.telegram.org https://webk.telegram.org https://webz.telegram.org",
          },
        ],
      },
      // CORS для API
      {
        source: '/api/:path*',
        headers: [
          { key: 'Access-Control-Allow-Credentials', value: 'true' },
          { key: 'Access-Control-Allow-Origin', value: '*' },
          { key: 'Access-Control-Allow-Methods', value: 'GET,POST,PUT,DELETE,OPTIONS' },
          { key: 'Access-Control-Allow-Headers', value: 'Content-Type, Authorization' },
        ],
      },
    ];
  },
  
  async rewrites() {
    // Используем переменную окружения для backend URL
    // В Railway это будет URL backend сервиса
    let backendUrl = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL;
    
    // Логируем для отладки (только в development)
    if (process.env.NODE_ENV !== 'production') {
      console.log('🔍 Backend URL config:', {
        BACKEND_URL: process.env.BACKEND_URL,
        NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
        resolved: backendUrl
      });
    }
    
    // Если URL не начинается с http:// или https://, добавляем https://
    if (backendUrl && !backendUrl.startsWith('http://') && !backendUrl.startsWith('https://')) {
      backendUrl = `https://${backendUrl}`;
    }
    
    // Fallback для локальной разработки (только если не в production)
    if (!backendUrl) {
      if (process.env.NODE_ENV === 'production') {
        // В production на Railway не должно быть fallback - это ошибка конфигурации
        console.error('❌ ERROR: BACKEND_URL or NEXT_PUBLIC_API_URL не установлены в production!');
        // В production возвращаем пустой rewrites, чтобы не было ошибок
        // API будет использовать прямой URL из NEXT_PUBLIC_API_URL в api.ts
        return [];
      }
      backendUrl = 'http://localhost:8081';
    }
    
    // Убираем trailing slash
    backendUrl = backendUrl.replace(/\/$/, '');
    
    return [
      // Проксируем все API запросы на backend
      // Убираем /api из destination, так как в web_interface.py эндпоинты без префикса /api
      {
        source: '/api/:path*',
        destination: `${backendUrl}/:path*`, // Proxy to FastAPI backend
      },
    ];
  },
};

module.exports = nextConfig;


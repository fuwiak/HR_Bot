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
    const backendUrl = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8081';
    return [
      // Проксируем все API запросы на backend
      {
        source: '/api/:path*',
        destination: `${backendUrl}/api/:path*`, // Proxy to FastAPI backend
      },
    ];
  },
};

module.exports = nextConfig;


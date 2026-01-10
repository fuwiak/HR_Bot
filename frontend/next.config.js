/** @type {import('next').Config} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone', // Для Docker деплоя на Railway
  
  // Настройка путей для импортов
  webpack: (config) => {
    config.resolve.alias = {
      ...config.resolve.alias,
      '@': require('path').resolve(__dirname),
    };
    return config;
  },
  
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
    ];
  },
  
  async rewrites() {
    // Используем переменную окружения для backend URL
    // В Railway это будет URL backend сервиса
    const backendUrl = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8081';
    return [
      {
        source: '/api/:path*',
        destination: `${backendUrl}/:path*`, // Proxy to FastAPI backend
      },
    ];
  },
};

module.exports = nextConfig;


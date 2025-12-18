/** @type {import('next').Config} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone', // Для Docker деплоя на Railway
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


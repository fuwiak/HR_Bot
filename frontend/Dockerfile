# Dockerfile для Frontend (Next.js) сервиса
# Используется когда Dockerfile находится внутри frontend/ директории
# ВАЖНО: Railway строит из корня проекта, поэтому нужно указывать frontend/ в путях
FROM node:18-alpine AS base

# Install dependencies only when needed
FROM base AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app

# Copy package files (Railway строит из корня, поэтому указываем frontend/)
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci

# Rebuild the source code only when needed
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY frontend/ .

# Set environment variable for build
ENV NEXT_TELEMETRY_DISABLED=1

# Build Next.js (standalone output)
RUN npm run build

# Production image, copy all the files and run next
FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy built application from standalone output
# Next.js standalone включает все необходимое в .next/standalone
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Next.js standalone mode - запускаем server.js из корня standalone
CMD ["node", "server.js"]

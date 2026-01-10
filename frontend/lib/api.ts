// API client for FastAPI backend
// Использует NEXT_PUBLIC_API_URL для подключения к backend
// В development: использует прокси /api/ из next.config.js (если NEXT_PUBLIC_API_URL не установлен)
// В production: использует абсолютный URL из NEXT_PUBLIC_API_URL

// NEXT_PUBLIC_API_URL доступен и на клиенте, и на сервере в Next.js
// Если не установлен, используем относительный путь /api (будет работать через прокси)
const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api';

export async function sendEmail(recipient: string, subject: string, body: string) {
  const formData = new URLSearchParams();
  formData.append('recipient', recipient);
  formData.append('subject', subject);
  formData.append('body', body);

  const response = await fetch(`${API_BASE}/demo/email`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

export async function generateProposal(request: string) {
  const response = await fetch(`${API_BASE}/demo/proposal`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ request }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

export async function searchRAG(query: string, limit: number = 5) {
  const response = await fetch(`${API_BASE}/rag/search?query=${encodeURIComponent(query)}&limit=${limit}`);

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

export async function getRAGStats() {
  const response = await fetch(`${API_BASE}/rag/stats`);

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

export async function getRAGDocs(limit: number = 20) {
  const response = await fetch(`${API_BASE}/rag/docs?limit=${limit}`);

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

// RAG Dashboard API
export async function testRAGQuery(query: string, topK: number = 5) {
  const response = await fetch(`${API_BASE}/rag/test?query=${encodeURIComponent(query)}&top_k=${topK}`);

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

export async function runRAGEvaluation() {
  const response = await fetch(`${API_BASE}/rag/workflow/evaluate`, {
    method: 'POST',
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

export async function loadPDF(file: File) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE}/rag/workflow/load-pdf`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

export async function scrapeWebsites() {
  const response = await fetch(`${API_BASE}/rag/workflow/scrape`, {
    method: 'POST',
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

export async function getRAGMetrics() {
  const response = await fetch(`${API_BASE}/rag/metrics/latest`);

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

export async function getRAGParameters() {
  const response = await fetch(`${API_BASE}/rag/parameters`);

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

export async function updateRAGParameters(params: {
  chunk_size?: number;
  chunk_overlap?: number;
  top_k?: number;
  min_score?: number;
  temperature?: number;
  max_tokens?: number;
}) {
  const response = await fetch(`${API_BASE}/rag/parameters`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

// Email API
export async function checkEmails() {
  const response = await fetch(`${API_BASE}/email/check`);

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

export async function generateEmailDraft(request: string) {
  const response = await fetch(`${API_BASE}/email/draft`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ request }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

// WEEEK API
export async function getWEEEKProjects() {
  const response = await fetch(`${API_BASE}/weeek/projects`);

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

export async function getWEEEKTasks(projectId?: string) {
  const url = projectId 
    ? `${API_BASE}/weeek/tasks?project_id=${projectId}`
    : `${API_BASE}/weeek/tasks`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

export async function createWEEEKTask(projectName: string, taskName: string) {
  const response = await fetch(`${API_BASE}/weeek/task`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project: projectName, task: taskName }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

export async function getWEEEKStatus() {
  const response = await fetch(`${API_BASE}/weeek/status`);

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

// Tools API
export async function generateSummary(projectName: string) {
  const response = await fetch(`${API_BASE}/tools/summary`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project: projectName }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

export async function generateReport(projectName: string) {
  const response = await fetch(`${API_BASE}/tools/report`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project: projectName }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

export async function generateHypothesis(description: string) {
  const response = await fetch(`${API_BASE}/tools/hypothesis`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ description }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

// Chat API
export async function sendChatMessage(message: string, userId?: string) {
  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ 
      message,
      user_id: userId || 'miniapp_user',
      platform: 'miniapp'
    }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

export async function getChatHistory(userId: string, limit: number = 20) {
  const response = await fetch(`${API_BASE}/chat/history?user_id=${encodeURIComponent(userId)}&limit=${limit}`);

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

// Yandex Disk API
export async function getYadiskFiles(path: string = '/') {
  const response = await fetch(`${API_BASE}/yadisk/list?path=${encodeURIComponent(path)}`);

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

export async function searchYadiskFiles(query: string) {
  const response = await fetch(`${API_BASE}/yadisk/search?query=${encodeURIComponent(query)}`);

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

export async function getYadiskRecent() {
  const response = await fetch(`${API_BASE}/yadisk/recent`);

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

// Services & Booking API
export async function getServices() {
  const response = await fetch(`${API_BASE}/services`);

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

export async function getMasters() {
  const response = await fetch(`${API_BASE}/masters`);

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

export async function createBooking(data: {
  service: string;
  master: string;
  date: string;
  time: string;
  userId: string;
}) {
  const response = await fetch(`${API_BASE}/booking`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

// Admin check API
export async function checkAdminStatus(userId: string) {
  const response = await fetch(`${API_BASE}/admin/check?user_id=${userId}`);

  if (!response.ok) {
    return { is_admin: false };
  }

  return response.json();
}

// Notifications API
export async function getNotifications(userId: string, limit: number = 20) {
  const response = await fetch(`${API_BASE}/notifications?user_id=${encodeURIComponent(userId)}&limit=${limit}`);

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

export async function getUnreadNotificationCount(userId: string) {
  const response = await fetch(`${API_BASE}/notifications/unread-count?user_id=${encodeURIComponent(userId)}`);

  if (!response.ok) {
    // Возвращаем 0 вместо ошибки, чтобы не ломать UI
    return { unread_count: 0 };
  }

  return response.json();
}

export async function markNotificationAsRead(userId: string, notificationId?: string) {
  const response = await fetch(`${API_BASE}/notifications/mark-read`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ 
      user_id: userId,
      notification_id: notificationId
    }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

export async function getUnreadEmailCount(userId?: string) {
  const url = userId 
    ? `${API_BASE}/email/unread-count?user_id=${encodeURIComponent(userId)}`
    : `${API_BASE}/email/unread-count`;
  const response = await fetch(url);

  if (!response.ok) {
    // Возвращаем 0 вместо ошибки, чтобы не ломать UI
    return { unread_count: 0 };
  }

  return response.json();
}













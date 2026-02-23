/**
 * Weeeek Manager — custom agent skill для AnythingLLM.
 * Управление проектами и задачами в Weeeek (api.weeek.net).
 * Требует: WEEEEK_TOKEN или WEEEK_API_KEY в окружении AnythingLLM.
 */

const BASE_URL = (process.env.WEEEK_API_URL || "https://api.weeek.net/public/v1").replace(/\/$/, "");
const API_KEY = process.env.WEEEEK_TOKEN || process.env.WEEEK_API_KEY || process.env.WEEEK_TOKEN;

function getHeaders() {
  return {
    "Authorization": `Bearer ${API_KEY}`,
    "Content-Type": "application/json",
  };
}

async function request(method, path, body = null) {
  const url = path.startsWith("http") ? path : `${BASE_URL}${path}`;
  const opts = { method, headers: getHeaders() };
  if (body && (method === "POST" || method === "PUT")) {
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(url, opts);
  const text = await res.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch (_) {
    data = null;
  }
  if (res.status >= 400) {
    return { ok: false, status: res.status, data, text: text.slice(0, 500) };
  }
  return { ok: true, status: res.status, data };
}

async function getWorkspaceInfo() {
  const r = await request("GET", "/ws");
  if (!r.ok) return `Ошибка Weeeek: ${r.status}. ${r.text || ""}`;
  const ws = r.data?.workspace || r.data;
  if (!ws) return "Не удалось получить данные workspace.";
  return `Weeeek Workspace: ${ws.title || ws.name || "—"} (ID: ${ws.id}).`;
}

// GET /tm/projects — список проектов (команда: weeek проекты)
// API: https://api.weeek.net/public/v1/tm/projects, ответ: { success, projects: [{ id, name, ... }] }
async function getProjects() {
  const r = await request("GET", "/tm/projects");
  if (!r.ok) return `Ошибка Weeeek: ${r.status}. ${r.text || ""}`;
  const list = r.data?.projects || [];
  if (!list.length) return "Проектов пока нет.";
  return "Проекты:\n" + list.map((p) => `• ${p.id}: ${p.name || p.title || "—"}`).join("\n");
}

async function getTasks(projectId = null, completed = false) {
  let path = "/tm/tasks?perPage=50&offset=0";
  if (projectId) path += `&projectId=${encodeURIComponent(projectId)}`;
  path += `&completed=${completed ? "true" : "false"}`;
  const r = await request("GET", path);
  if (!r.ok) return `Ошибка Weeeek: ${r.status}. ${r.text || ""}`;
  const list = r.data?.tasks || [];
  if (!list.length) return projectId ? "В этом проекте нет активных задач." : "Активных задач нет.";
  return "Задачи:\n" + list.map((t) => {
    const name = t.name || t.title || "Без названия";
    const done = t.isCompleted || t.completed ? " ✅" : "";
    return `• ${t.id}: ${name} (проект ${t.projectId})${done}`;
  }).join("\n");
}

async function getTask(taskId) {
  const r = await request("GET", `/tm/tasks/${taskId}`);
  if (!r.ok) return `Ошибка Weeeek: ${r.status}. ${r.text || ""}`;
  const t = r.data?.task || r.data;
  if (!t) return "Задача не найдена.";
  const name = t.name || t.title || "—";
  const completed = t.isCompleted || t.completed ? "Да" : "Нет";
  return `Задача #${t.id}: ${name}\nПроект: ${t.projectId}, выполнена: ${completed}.`;
}

async function createTask(projectId, name, description = "", taskType = "action", day = null) {
  const body = {
    name: String(name).trim(),
    projectId: parseInt(projectId, 10),
    type: taskType,
  };
  if (description) body.description = description;
  if (day) body.day = day;
  const r = await request("POST", "/tm/tasks", body);
  if (!r.ok) return `Ошибка создания задачи: ${r.status}. ${r.text || ""}`;
  const task = r.data?.task || r.data;
  const id = task?.id || "?";
  return `Задача создана: "${name}" (ID: ${id}).`;
}

async function createProject(name, description = "", isPrivate = false) {
  const body = { name: String(name).trim(), isPrivate: !!isPrivate };
  if (description) body.description = description;
  const r = await request("POST", "/tm/projects", body);
  if (!r.ok) return `Ошибка создания проекта: ${r.status}. ${r.text || ""}`;
  const project = r.data?.project || r.data;
  const id = project?.id || "?";
  return `Проект создан: "${name}" (ID: ${id}).`;
}

async function completeTask(taskId) {
  const r = await request("POST", `/tm/tasks/${taskId}/complete`);
  if (!r.ok) return `Ошибка: ${r.status}. ${r.text || ""}`;
  return `Задача ${taskId} отмечена как выполненная.`;
}

async function uncompleteTask(taskId) {
  const r = await request("POST", `/tm/tasks/${taskId}/un-complete`);
  if (!r.ok) return `Ошибка: ${r.status}. ${r.text || ""}`;
  return `Задача ${taskId} возобновлена.`;
}

async function deleteTask(taskId) {
  const r = await request("DELETE", `/tm/tasks/${taskId}`);
  if (!r.ok) return `Ошибка удаления: ${r.status}. ${r.text || ""}`;
  return `Задача ${taskId} удалена.`;
}

function strip(s) {
  return (s || "").trim();
}

// Префикс всех команд — избегаем пересечения с обычным диалогом
const PREFIX = /^weeek\s+/i;

// Разбор текста пользователя и вызов нужного действия
async function handler({ prompt }) {
  const raw = strip(prompt || "");
  if (!API_KEY) {
    return "Weeeek не настроен: задайте WEEEEK_TOKEN или WEEEK_API_KEY в окружении AnythingLLM.";
  }

  // Все команды должны начинаться с "weeek "
  if (!PREFIX.test(raw)) {
    return (
      "Weeeek Manager. Все команды начинаются с префикса **weeek**.\n\n" +
      "• weeek info — информация о workspace\n" +
      "• weeek проекты — список проектов\n" +
      "• weeek задачи [id] — список задач (опционально: id проекта)\n" +
      "• weeek задача 123 — информация о задаче\n" +
      "• weeek добавь задачу: ID | Название — создать задачу\n" +
      "• weeek создай проект: Название — создать проект\n" +
      "• weeek заверши задачу: 123 — отметить выполненной\n" +
      "• weeek возобнови задачу: 123 — снять выполнение\n" +
      "• weeek удали задачу: 123 — удалить задачу"
    );
  }

  const text = strip(raw.replace(PREFIX, ""));
  const lower = text.toLowerCase();

  // Инфо workspace
  if (/^(info|workspace|инфо)$/i.test(lower) || lower === "") {
    return await getWorkspaceInfo();
  }

  // Список проектов
  if (/^(projects|проекты|список\s+проектов|покажи\s+проекты)$/i.test(lower)) {
    return await getProjects();
  }

  // Список задач: "задачи" или "задачи 123" или "tasks 123"
  const tasksMatchList = lower.match(/^(tasks|задачи|покажи\s+задачи)(?:\s+(?:проекта\s+)?(\d+))?$/i);
  const tasksMatchShort = text.match(/^задачи\s+(\d+)$/i);
  if (tasksMatchList) {
    const projectId = tasksMatchList[2] || null;
    return await getTasks(projectId, false);
  }
  if (tasksMatchShort) {
    return await getTasks(tasksMatchShort[1], false);
  }

  // Одна задача по ID: "задача 456" / "task 456"
  const oneTaskMatch = text.match(/^(?:задача|task)\s+(\d+)$/i);
  if (oneTaskMatch) {
    return await getTask(oneTaskMatch[1]);
  }

  // Добавить задачу: "добавь задачу: 1 | Название" / "add task: 1 | Title"
  const addTaskMatch = text.match(/^(?:add\s+task|create\s+task|добавь\s+задачу|создай\s+задачу)\s*:\s*(.+?)\s*\|\s*(.+)$/i)
    || text.match(/^(?:add\s+task|create\s+task|добавь\s+задачу|создай\s+задачу)\s+(\d+)\s+\|\s*(.+)$/i);
  if (addTaskMatch) {
    const projectId = strip(addTaskMatch[1]);
    const title = strip(addTaskMatch[2]);
    if (!projectId || !title) return "Пример: weeek добавь задачу: 1 | Купить молоко";
    return await createTask(projectId, title, "", "action", null);
  }

  // Создать проект
  const addProjectMatch = text.match(/^(?:create\s+project|создай\s+проект)\s*:\s*(.+)$/i);
  if (addProjectMatch) {
    const name = strip(addProjectMatch[1]);
    if (!name) return "Пример: weeek создай проект: Маркетинг";
    return await createProject(name, "", false);
  }

  // Завершить задачу
  const completeMatch = text.match(/^(?:complete\s+task|заверши\s+задачу|выполни\s+задачу)\s*:\s*(\d+)$/i)
    || text.match(/^(?:complete|заверши)\s+(\d+)$/i);
  if (completeMatch) {
    return await completeTask(completeMatch[1]);
  }

  // Возобновить задачу
  const uncompleteMatch = text.match(/^(?:uncomplete\s+task|возобнови\s+задачу)\s*:\s*(\d+)$/i)
    || text.match(/^uncomplete\s+(\d+)$/i);
  if (uncompleteMatch) {
    return await uncompleteTask(uncompleteMatch[1]);
  }

  // Удалить задачу
  const deleteMatch = text.match(/^(?:delete\s+task|удали\s+задачу)\s*:\s*(\d+)$/i)
    || text.match(/^(?:delete|удали)\s+задачу\s+(\d+)$/i);
  if (deleteMatch) {
    return await deleteTask(deleteMatch[1]);
  }

  return (
    "Weeeek Manager. Все команды с префиксом **weeek**:\n" +
    "• weeek info — информация о workspace\n" +
    "• weeek проекты — список проектов\n" +
    "• weeek задачи [id] — список задач\n" +
    "• weeek задача 123 — информация о задаче\n" +
    "• weeek добавь задачу: ID | Название — создать задачу\n" +
    "• weeek создай проект: Название — создать проект\n" +
    "• weeek заверши задачу: 123 / weeek возобнови задачу: 123 / weeek удали задачу: 123"
  );
}

module.exports = { handler };

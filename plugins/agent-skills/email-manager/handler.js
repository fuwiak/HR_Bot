/**
 * Email Manager — custom agent skill для AnythingLLM.
 * Просмотр писем Yandex (через HR_Bot backend) и отправка ответов.
 * Требует: HR_BOT_BACKEND_URL в окружении AnythingLLM (URL бэкенда без слэша в конце).
 */

const BASE = (process.env.HR_BOT_BACKEND_URL || process.env.BACKEND_URL || "").replace(/\/$/, "");
const MAX_LIST = 15;

function strip(s) {
  return (s || "").trim();
}

async function request(method, path, body = null) {
  if (!BASE) {
    return { ok: false, error: "HR_BOT_BACKEND_URL не задан в окружении AnythingLLM." };
  }
  const url = path.startsWith("http") ? path : `${BASE}${path}`;
  const opts = { method, headers: { "Content-Type": "application/json" } };
  if (body && (method === "POST" || method === "PUT")) {
    opts.body = JSON.stringify(body);
  }
  try {
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
  } catch (e) {
    return { ok: false, error: String(e.message || e) };
  }
}

async function getRecentEmails(limit = 10) {
  const r = await request("GET", `/api/email/recent?limit=${Math.min(limit, 20)}`);
  if (!r.ok) {
    return { ok: false, error: r.error || r.text || `Ошибка ${r.status}` };
  }
  const list = r.data?.emails || [];
  return { ok: true, emails: list };
}

async function sendReply(to_email, subject, content) {
  const r = await request("POST", "/api/email/reply", {
    to_email: String(to_email).trim(),
    subject: String(subject).trim(),
    content: String(content).trim(),
  });
  if (!r.ok) {
    return { ok: false, error: r.data?.error || r.text || `Ошибка ${r.status}` };
  }
  return { ok: true, message: r.data?.message || "Письмо отправлено" };
}

// Префиксы: mail ... или письм... (письма, письмо 1, ответь на письмо 2: текст)
const PREFIX_MAIL = /^mail\s+/i;
const PREFIX_PISMO = /^письм/i;

function matchPrefix(raw) {
  const t = strip(raw);
  if (PREFIX_MAIL.test(t)) return strip(t.replace(PREFIX_MAIL, ""));
  if (PREFIX_PISMO.test(t)) return t; // "письма", "письмо 1", "ответь на письмо 2: ..."
  return null;
}

async function handler({ prompt }) {
  const raw = strip(prompt || "");
  const cmd = matchPrefix(raw);
  if (cmd === null) {
    return (
      "Email Manager. Команды для просмотра и ответов на письма (префикс **mail** или **письм**).\n\n" +
      "• mail письма / письма — список последних писем\n" +
      "• mail письмо 1 / письмо 1 — показать полный текст письма №1\n" +
      "• mail ответь на письмо 2: ваш текст ответа — отправить ответ на письмо №2\n\n" +
      "В окружении AnythingLLM должен быть задан **HR_BOT_BACKEND_URL** (URL бэкенда HR_Bot без слэша в конце)."
    );
  }

  const lower = cmd.toLowerCase();

  // Список писем: "письма" / "покажи письма" / пусто после "mail"
  if (!cmd || /^(письма|покажи\s+письма|list|emails?)$/i.test(lower)) {
    const out = await getRecentEmails(MAX_LIST);
    if (!out.ok) return `Ошибка при получении писем: ${out.error}`;
    const emails = out.emails || [];
    if (!emails.length) return "Писем не найдено (или почта недоступна).";
    const lines = emails.map((e, i) => {
      const n = i + 1;
      const subj = (e.subject || "Без темы").slice(0, 60);
      const from = (e.from || "—").slice(0, 40);
      return `${n}. От: ${from} | Тема: ${subj}`;
    });
    return "Последние письма:\n\n" + lines.join("\n") + "\n\nНапишите **письмо N** (например: письмо 1), чтобы увидеть текст письма, или **ответь на письмо N: текст**, чтобы отправить ответ.";
  }

  // Одно письмо по номеру: "письмо 1" / "mail письмо 2"
  const oneMatch = cmd.match(/^(?:письмо|mail|email)\s*(\d+)$/i) || cmd.match(/^(\d+)$/);
  if (oneMatch) {
    const num = parseInt(oneMatch[1], 10);
    if (num < 1) return "Укажите номер письма от 1.";
    const out = await getRecentEmails(Math.max(num, MAX_LIST));
    if (!out.ok) return `Ошибка: ${out.error}`;
    const emails = out.emails || [];
    const email = emails[num - 1];
    if (!email) return `Письмо №${num} не найдено (в списке ${emails.length} писем).`;
    const from = email.from || "—";
    const subject = email.subject || "Без темы";
    const date = email.date || "";
    const body = email.body || email.preview || "(нет текста)";
    return `Письмо №${num}\nОт: ${from}\nТема: ${subject}\nДата: ${date}\n\n---\n${body}\n\n---\nЧтобы ответить, напишите: **ответь на письмо ${num}: ваш текст ответа**`;
  }

  // Ответ на письмо: "ответь на письмо 2: текст" / "mail ответь на письмо 1: привет, высылаю..."
  const replyMatch = cmd.match(/^(?:ответь|ответить|reply)\s+(?:на\s+)?(?:письмо?|mail|email)\s*(\d+)\s*:\s*(.+)$/is)
    || cmd.match(/^(?:ответь|reply)\s*(\d+)\s*:\s*(.+)$/is);
  if (replyMatch) {
    const num = parseInt(replyMatch[1], 10);
    const content = strip(replyMatch[2]);
    if (num < 1) return "Укажите номер письма от 1.";
    if (!content) return "Напишите текст ответа после двоеточия.";
    const out = await getRecentEmails(Math.max(num, MAX_LIST));
    if (!out.ok) return `Ошибка при получении писем: ${out.error}`;
    const emails = out.emails || [];
    const email = emails[num - 1];
    if (!email) return `Письмо №${num} не найдено.`;
    const to_email = email.from || "";
    const subject = email.subject || "Без темы";
    const send = await sendReply(to_email, subject, content);
    if (!send.ok) return `Ошибка отправки: ${send.error}`;
    return `✅ Ответ на письмо №${num} (${to_email}) отправлен.`;
  }

  return (
    "Email Manager. Примеры:\n" +
    "• **mail письма** — список писем\n" +
    "• **письмо 1** — показать письмо №1\n" +
    "• **mail ответь на письмо 2: Добрый день, высылаю информацию...** — отправить ответ"
  );
}

module.exports = { handler };

/**
 * Email Manager — custom agent skill для AnythingLLM (формат runtime + entrypoint).
 * Проверка последних N писем Yandex и ответы на них через backend HR_Bot.
 * В setup_args задайте HR_BOT_BACKEND_URL (URL бэкенда без слэша в конце).
 */

function getBase(ctx) {
  const url = (ctx && ctx.runtimeArgs && ctx.runtimeArgs.HR_BOT_BACKEND_URL) || process.env.HR_BOT_BACKEND_URL || process.env.BACKEND_URL || "";
  return String(url).trim().replace(/\/$/, "");
}

async function request(base, method, path, body = null) {
  if (!base) {
    return { ok: false, error: "HR_BOT_BACKEND_URL не задан. Укажите в настройках скилла (Setup) или в переменных окружения AnythingLLM." };
  }
  const url = path.startsWith("http") ? path : `${base}${path}`;
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

async function getRecentEmails(base, limit = 10) {
  const r = await request(base, "GET", `/api/email/recent?limit=${Math.min(Number(limit) || 10, 20)}`);
  if (!r.ok) {
    return { ok: false, error: r.error || r.text || `Ошибка ${r.status}` };
  }
  const list = r.data?.emails || [];
  return { ok: true, emails: list };
}

async function sendReply(base, to_email, subject, content) {
  const r = await request(base, "POST", "/api/email/reply", {
    to_email: String(to_email).trim(),
    subject: String(subject).trim(),
    content: String(content).trim(),
  });
  if (!r.ok) {
    return { ok: false, error: r.data?.error || r.text || `Ошибка ${r.status}` };
  }
  return { ok: true, message: r.data?.message || "Письмо отправлено" };
}

module.exports.runtime = {
  handler: async function ({ action, limit, email_number, reply_text }) {
    const self = this;
    const base = getBase(self);
    try {
      if (self.introspect) {
        self.introspect(`Email Manager: action=${action || "list"}, limit=${limit}, email_number=${email_number}`);
      }
      if (self.logger) {
        self.logger(`Email Manager invoked: action=${action}, limit=${limit}, email_number=${email_number}`);
      }

      const act = String(action || "list").toLowerCase().trim();
      const lim = Math.min(Math.max(1, parseInt(limit, 10) || 10), 20);
      const num = parseInt(email_number, 10);
      const text = reply_text != null ? String(reply_text).trim() : "";

      // list — список последних N писем
      if (act === "list" || act === "") {
        const out = await getRecentEmails(base, lim);
        if (!out.ok) return `Ошибка при получении писем: ${out.error}`;
        const emails = out.emails || [];
        if (!emails.length) return "Писем не найдено (или почта недоступна). Проверьте настройки Yandex на бэкенде.";
        const lines = emails.map((e, i) => {
          const n = i + 1;
          const subj = (e.subject || "Без темы").slice(0, 60);
          const from = (e.from || "—").slice(0, 40);
          return `${n}. От: ${from} | Тема: ${subj}`;
        });
        return "Последние письма:\n\n" + lines.join("\n") + "\n\nЧтобы прочитать письмо, вызовите скилл с action=get и email_number=N. Чтобы ответить — action=reply, email_number=N и reply_text=ваш текст.";
      }

      // get — показать одно письмо по номеру
      if (act === "get") {
        if (!num || num < 1) return "Укажите email_number от 1 (номер письма в списке).";
        const out = await getRecentEmails(base, Math.max(num, 15));
        if (!out.ok) return `Ошибка: ${out.error}`;
        const emails = out.emails || [];
        const email = emails[num - 1];
        if (!email) return `Письмо №${num} не найдено (в списке ${emails.length} писем).`;
        const from = email.from || "—";
        const subject = email.subject || "Без темы";
        const date = email.date || "";
        const body = email.body || email.preview || "(нет текста)";
        return `Письмо №${num}\nОт: ${from}\nТема: ${subject}\nДата: ${date}\n\n---\n${body}\n\n---\nЧтобы ответить, вызовите скилл с action=reply, email_number=${num} и reply_text=ваш текст.`;
      }

      // reply — отправить ответ на письмо
      if (act === "reply") {
        if (!num || num < 1) return "Укажите email_number (номер письма, на которое отвечаете).";
        if (!text) return "Укажите reply_text (текст ответа).";
        const out = await getRecentEmails(base, Math.max(num, 15));
        if (!out.ok) return `Ошибка при получении писем: ${out.error}`;
        const emails = out.emails || [];
        const email = emails[num - 1];
        if (!email) return `Письмо №${num} не найдено.`;
        const to_email = email.from || "";
        const subject = email.subject || "Без темы";
        const send = await sendReply(base, to_email, subject, text);
        if (!send.ok) return `Ошибка отправки: ${send.error}`;
        return `Ответ на письмо №${num} (${to_email}) отправлен.`;
      }

      return `Неизвестное действие: ${action}. Используйте action: list (список писем), get (показать письмо по email_number), reply (ответить — нужны email_number и reply_text).`;
    } catch (e) {
      const msg = e.message || String(e);
      if (self.logger) self.logger("Email Manager error: " + msg);
      return "Ошибка Email Manager: " + msg;
    }
  },
};

// static/app.js — CodeDreamers frontend

const ROLE_SELECT = document.getElementById("roleSelect");

function getRole() { return ROLE_SELECT.value; }

async function apiFetch(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "X-Role": getRole(), "Content-Type": "application/json", ...(opts.headers || {}) },
    ...opts,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err.error || res.statusText);
  }
  return res.json();
}

function escHtml(str = "") {
  return String(str).replace(/&/g,"&amp;").replace(/"/g,"&quot;")
    .replace(/</g,"&lt;").replace(/>/g,"&gt;");
}

// ── Pages ─────────────────────────────────────────────────────────────────

const pages = {
  courses: document.getElementById("page-courses"),
  my:      document.getElementById("page-my"),
  detail:  document.getElementById("page-detail"),
  learn:   document.getElementById("page-learn"),
  create:  document.getElementById("page-create"),
  vector:  document.getElementById("page-vector"),
  admin:   document.getElementById("page-admin"),
};

function showPage(name) {
  Object.values(pages).forEach(p => p.classList.remove("active"));
  if (pages[name]) pages[name].classList.add("active");
  document.querySelectorAll(".nav-btn").forEach(b =>
    b.classList.toggle("active", b.dataset.page === name)
  );
}

document.querySelectorAll(".nav-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    showPage(btn.dataset.page);
    if (btn.dataset.page === "courses") loadCourses();
    if (btn.dataset.page === "my")      loadMyCourses();
  });
});

document.getElementById("backBtn").addEventListener("click", () => {
  showPage("courses"); loadCourses();
});

document.getElementById("backLearnBtn").addEventListener("click", () => {
  showPage("my"); loadMyCourses();
});

ROLE_SELECT.addEventListener("change", () => {
  const active = document.querySelector(".page.active");
  if (active?.id === "page-courses") loadCourses();
  if (active?.id === "page-my")      loadMyCourses();
  applyRoleUI();
});

function applyRoleUI() {
  const role = getRole();
  const canCreate = role === "admin" || role === "mentor";
  const isAdmin   = role === "admin";

  // Кнопка "+ Курс" в навбаре
  document.querySelector('.nav-btn[data-page="create"]').style.display = canCreate ? "" : "none";

  // Если студент на странице create — отправить на каталог
  if (!canCreate && document.getElementById("page-create").classList.contains("active")) {
    showPage("courses"); loadCourses();
  }

  // Админ-карточки
  document.getElementById("adminCardCmd").style.display    = isAdmin ? "" : "none";
  document.getElementById("adminCardState").style.display  = isAdmin ? "" : "none";
  document.getElementById("adminCardUsers").style.display  = isAdmin ? "" : "none";
  document.getElementById("adminCardNotify").style.display = isAdmin ? "" : "none";
}

// ── Skeleton ──────────────────────────────────────────────────────────────

function renderSkeletons(container, count = 6) {
  container.innerHTML = Array(count)
    .fill('<div class="skeleton skeleton-card"></div>').join("");
}

// ── SSE Push ──────────────────────────────────────────────────────────────

let notifCount = 0;
const notifCountEl   = document.getElementById("notifCount");
const toastContainer = document.getElementById("toastContainer");
const notifDropdown  = document.getElementById("notifDropdown");
const notifList      = document.getElementById("notifList");
const pendingNotifs  = [];

function renderNotifList() {
  if (!pendingNotifs.length) {
    notifList.innerHTML = '<p class="notif-empty">Нет уведомлений</p>';
    return;
  }
  notifList.innerHTML = pendingNotifs.map(n =>
    `<div class="notif-item"><span class="notif-item__msg">${escHtml(n.message)}</span><span class="notif-item__time">${n.timestamp}</span></div>`
  ).join("");
}

function showToast(msg, type = "info") {
  const t = document.createElement("div");
  t.className = `toast toast--${type}`;
  t.textContent = msg;
  toastContainer.appendChild(t);
  setTimeout(() => t.classList.add("show"), 10);
  setTimeout(() => { t.classList.remove("show"); setTimeout(() => t.remove(), 300); }, 4000);
}

function initSSE() {
  const es = new EventSource("/api/events");
  es.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      if (data.type === "connected") return;
      notifCount++;
      notifCountEl.textContent = notifCount;
      notifCountEl.classList.remove("hidden");
      if (data.type === "NotificationEvent") {
        pendingNotifs.unshift({ message: data.message, timestamp: data.timestamp });
        notifCount++;
        notifCountEl.textContent = notifCount;
        notifCountEl.classList.remove("hidden");
        return;
      }
      const msgs = {
        EnrollEvent:       `📚 ${data.user_name} записался на «${data.course_title}»`,
        CompleteEvent:     `✅ ${data.user_name} завершил «${data.course_title}»`,
        UnenrollEvent:     `❌ ${data.user_name} отписался от «${data.course_title}»`,
        StateChangedEvent: `🔄 ${data.label}: ${data.from_state} → ${data.to_state}`,
        LessonAddedEvent:  `📝 Новый урок в «${data.course_title}»: ${data.lesson_title}`,
      };
      notifCount++;
      notifCountEl.textContent = notifCount;
      notifCountEl.classList.remove("hidden");
      showToast(msgs[data.type] || data.type, data.type === "CompleteEvent" ? "success" : "info");
    } catch {}
  };
  es.onerror = () => setTimeout(initSSE, 5000);
}

document.getElementById("notifBell").addEventListener("click", (e) => {
  e.stopPropagation();
  notifDropdown.classList.toggle("hidden");
  if (!notifDropdown.classList.contains("hidden")) {
    notifCount = 0;
    notifCountEl.classList.add("hidden");
    renderNotifList();
  }
});

document.getElementById("notifClear").addEventListener("click", (e) => {
  e.stopPropagation();
  pendingNotifs.length = 0;
  renderNotifList();
});

document.addEventListener("click", () => notifDropdown.classList.add("hidden"));

initSSE();

// ── State chips ───────────────────────────────────────────────────────────

const STATE_LABELS = {
  new:             { label: "Новый",       cls: "state--new" },
  assigned_mentor: { label: "Ментор",      cls: "state--mentor" },
  assigned_user:   { label: "Назначен",    cls: "state--user" },
  in_progress:     { label: "В процессе", cls: "state--progress" },
  completed:       { label: "Завершён",    cls: "state--done" },
};

function stateChip(state) {
  const s = STATE_LABELS[state] || { label: state, cls: "" };
  return `<span class="state-chip ${s.cls}">${s.label}</span>`;
}

// ── Courses page ──────────────────────────────────────────────────────────

async function loadCourses() {
  const grid = document.getElementById("courseGrid");
  renderSkeletons(grid);
  try {
    const courses = await apiFetch("/api/courses");
    if (!courses.length) { grid.innerHTML = '<p class="empty">Курсы не найдены.</p>'; return; }
    grid.innerHTML = courses.map(c => `
      <div class="course-card" data-id="${c.id}">
        <div class="course-card__title">${escHtml(c.title)}</div>
        <div class="course-card__desc">${escHtml(c.description || "")}</div>
        <div class="course-card__tags">${(c.tags||[]).map(t=>`<span class="tag">${t}</span>`).join("")}</div>
        <div class="course-card__footer">
          <span class="course-card__price">$${c.price.toFixed(2)}</span>
          <span class="badge badge--${c.difficulty_level}">${c.difficulty_level}</span>
          ${stateChip(c.state || "new")}
          ${getRole() === "admin" ? `<button class="btn-delete" data-course-id="${c.id}" onclick="deleteCourse(${c.id})">🗑️</button>` : ""}
        </div>
      </div>
    `).join("");
    grid.querySelectorAll(".course-card").forEach(card =>
      card.addEventListener("click", () => loadDetail(+card.dataset.id))
    );
  } catch (e) { grid.innerHTML = `<p class="empty">${e.message}</p>`; }
}

// ── My courses ────────────────────────────────────────────────────────────

async function loadMyCourses() {
  const list = document.getElementById("myList");
  renderSkeletons(list, 3);
  try {
    const items = await apiFetch("/api/users/1/enrollments");
    if (!items.length) { list.innerHTML = '<p class="empty">Нет записей.</p>'; return; }

    const progressMap = {};
    await Promise.all(items.map(async e => {
      try { progressMap[e.course_id] = await apiFetch(`/api/users/1/courses/${e.course_id}/progress`); }
      catch { progressMap[e.course_id] = null; }
    }));

    list.innerHTML = items.map(e => {
      const stateInfo = e.state || { display_name: 'Новый', color: '#6c757d' };
      const prog = progressMap[e.course_id];
      const pct = prog ? prog.progress_percentage : 0;
      const done = prog ? prog.completed_lessons : 0;
      const total = prog ? prog.total_lessons : 0;
      return `
        <div class="my-item" data-id="${e.course_id}">
          <div class="my-item__content">
            <span class="my-item__title">${escHtml(e.title)}</span>
            <div class="my-item__meta">
              <span class="my-item__status status--${e.status}">${e.status}</span>
              <span class="course-state-badge" style="background-color:${stateInfo.color}">${stateInfo.display_name}</span>
            </div>
            <div class="progress-bar-wrap"><div class="progress-bar" style="width:${pct}%"></div></div>
            <span class="progress-label">${done}/${total} уроков (${pct}%)</span>
          </div>
          <div class="my-item__actions">
            ${e.status === 'active' ? `<button class="btn-sm btn-primary" onclick="loadLearn(${e.course_id})">&#9654; Продолжить</button>` : ''}
            ${e.status === 'completed' ? `<span class="state-chip state--done">&#10003; Пройден</span>` : ''}
            <button class="btn-sm btn-secondary" onclick="loadDetail(${e.course_id})">О курсе</button>
          </div>
        </div>
      `;
    }).join("");
  } catch (e) { list.innerHTML = `<p class="empty">${e.message}</p>`; }
}

// ── Learn page ────────────────────────────────────────────────────────────

async function loadLearn(courseId) {
  showPage("learn");
  const container = document.getElementById("learnContent");
  container.innerHTML = '<div class="skeleton skeleton-card" style="height:60px"></div>';
  try {
    const [course, progress] = await Promise.all([
      apiFetch(`/api/courses/${courseId}`),
      apiFetch(`/api/users/1/courses/${courseId}/progress`),
    ]);
    const pct = progress.progress_percentage;
    container.innerHTML = `
      <div class="learn__header">
        <div class="learn__title">${escHtml(course.title)}</div>
        <div class="progress-bar-wrap" style="margin:10px 0">
          <div class="progress-bar" style="width:${pct}%"></div>
        </div>
        <span class="progress-label">${progress.completed_lessons}/${progress.total_lessons} уроков &mdash; ${pct}%</span>
      </div>
      <div class="learn__lessons">
        ${progress.lessons.map(l => `
          <div class="learn-lesson ${l.completed ? 'learn-lesson--done' : ''}">
            <div class="learn-lesson__left">
              <span class="learn-lesson__num">${l.order_num}</span>
              <span class="learn-lesson__title">${escHtml(l.title)}</span>
            </div>
            <div class="learn-lesson__right">
              ${l.completed
                ? `<span class="state-chip state--done">&#10003; Готово</span>`
                : `<button class="btn-sm btn-primary complete-btn" data-lesson-id="${l.id}">Отметить</button>`
              }
            </div>
          </div>
        `).join('')}
      </div>
      ${progress.is_completed ? `<div class="learn__complete-banner">Курс полностью пройден!</div>` : ''}
    `;
    container.querySelectorAll(".complete-btn").forEach(btn => {
      btn.addEventListener("click", async () => {
        try {
          const res = await apiFetch(`/api/users/1/lessons/${btn.dataset.lessonId}/complete`, { method: "POST" });
          showToast(res.result, "success");
          loadLearn(courseId);
        } catch (e) { showToast(e.message, "error"); }
      });
    });
  } catch (e) { container.innerHTML = `<p class="empty">${e.message}</p>`; }
}

// ── Detail page ───────────────────────────────────────────────────────────

async function loadDetail(courseId) {
  showPage("detail");
  const container = document.getElementById("detailContent");
  container.innerHTML = '<div class="skeleton skeleton-card" style="height:80px;margin-bottom:24px"></div>';
  try {
    const [course, program] = await Promise.all([
      apiFetch(`/api/courses/${courseId}`),
      apiFetch(`/api/courses/${courseId}/program`),
    ]);
    const tags = (course.tags || []).map(t => `<span class="tag">${t}</span>`).join("");

    // Проверяем, записан ли текущий пользователь (user_id=1)
    let enrollment = null;
    try {
      const enrollments = await apiFetch("/api/users/1/enrollments");
      enrollment = enrollments.find(e => e.course_id === courseId) || null;
    } catch {}

    const isEnrolled = enrollment && enrollment.status === "active";
    const isCompleted = enrollment && enrollment.status === "completed";

    let actionBtn = "";
    if (!enrollment) {
      actionBtn = `<button class="btn-primary" id="enrollBtn">+ Записаться</button>`;
    } else if (isEnrolled) {
      actionBtn = `
        <button class="btn-primary" id="learnBtn">▶ Начать обучение</button>
        <button class="btn-secondary" id="unenrollBtn">Отписаться</button>
      `;
    } else if (isCompleted) {
      actionBtn = `<span class="state-chip state--done">✅ Курс пройден</span>`;
    }

    container.innerHTML = `
      <div class="detail__header">
        <div>
          <div class="detail__title">${escHtml(course.title)}</div>
          <div class="detail__meta">
            <span class="badge badge--${course.difficulty_level}">${course.difficulty_level}</span>
            <span class="detail__price">$${course.price.toFixed(2)}</span>
            ${stateChip(course.state || "new")}
          </div>
          <div class="detail__tags">${tags}</div>
          <p style="color:var(--muted);margin-top:10px;font-size:.9rem">${escHtml(course.description||"")}</p>
          <div class="detail__actions" style="margin-top:16px;display:flex;gap:10px">${actionBtn}</div>
        </div>
      </div>
      <div class="program">${renderProgram(program)}</div>
    `;

    // Кнопка записи
    container.querySelector("#enrollBtn")?.addEventListener("click", async () => {
      try {
        const res = await apiFetch(`/api/users/1/courses/${courseId}/enroll`, { method: "POST" });
        showToast(res.result, "success");
        loadDetail(courseId);
      } catch (e) { showToast(e.message, "error"); }
    });

    // Кнопка отписки
    container.querySelector("#unenrollBtn")?.addEventListener("click", async () => {
      if (!confirm("Отписаться от курса?")) return;
      try {
        const res = await apiFetch(`/api/users/1/courses/${courseId}/unenroll`, { method: "POST" });
        showToast(res.result, "info");
        loadDetail(courseId);
      } catch (e) { showToast(e.message, "error"); }
    });

    // Кнопка начать обучение
    container.querySelector("#learnBtn")?.addEventListener("click", () => loadLearn(courseId));

    container.querySelectorAll(".program__block-header").forEach(h => {
      h.addEventListener("click", () => {
        h.nextElementSibling.classList.toggle("open");
        h.querySelector(".chevron").classList.toggle("open");
      });
    });
    container.querySelectorAll(".lesson-item").forEach(item =>
      item.addEventListener("click", () => openModal(item.dataset.title, item.dataset.content))
    );
  } catch (e) { container.innerHTML = `<p class="empty">${e.message}</p>`; }
}

function renderProgram(node) {
  if (!node || !node.children) return '<p class="empty">Программа пуста.</p>';
  return node.children.map((block, bi) => `
    <div class="program__block">
      <div class="program__block-header">
        <div class="program__block-title">
          <div class="block-icon">B${bi+1}</div>${escHtml(block.title)}
        </div>
        <span class="chevron">&#9660;</span>
      </div>
      <div class="program__lessons">
        ${(block.children||[]).map(l => `
          <div class="lesson-item"
               data-title="${escHtml(l.title)}"
               data-content="${escHtml(l.content||'')}">
            <div class="lesson-num">${l.order_num}</div>
            <div>
              <div class="lesson-title">${escHtml(l.title)}</div>
              <div class="lesson-content">${escHtml(l.content||"")}</div>
            </div>
          </div>
        `).join("")}
      </div>
    </div>
  `).join("");
}

// ── Create course ─────────────────────────────────────────────────────────

let modules = [];

document.getElementById("addModuleBtn").addEventListener("click", () => {
  modules.push({ title: "", content: "", order_num: modules.length + 1 });
  renderModules();
});

function renderModules() {
  const list = document.getElementById("moduleList");
  list.innerHTML = modules.map((m, i) => `
    <div class="module-row">
      <span class="module-num">${i+1}</span>
      <input class="module-title" data-i="${i}" placeholder="Название урока" value="${escHtml(m.title)}" />
      <input class="module-content" data-i="${i}" placeholder="Содержание" value="${escHtml(m.content)}" />
      <button class="btn-icon" data-del="${i}">✕</button>
    </div>
  `).join("");
  list.querySelectorAll(".module-title").forEach(inp =>
    inp.addEventListener("input", e => { modules[+e.target.dataset.i].title = e.target.value; })
  );
  list.querySelectorAll(".module-content").forEach(inp =>
    inp.addEventListener("input", e => { modules[+e.target.dataset.i].content = e.target.value; })
  );
  list.querySelectorAll("[data-del]").forEach(btn =>
    btn.addEventListener("click", e => {
      modules.splice(+e.target.dataset.del, 1);
      modules.forEach((m, i) => m.order_num = i + 1);
      renderModules();
    })
  );
}

document.getElementById("suggestTagsBtn").addEventListener("click", async () => {
  const desc = document.getElementById("cDesc").value;
  if (!desc) return;
  try {
    const res = await apiFetch("/api/tags/suggest", {
      method: "POST", body: JSON.stringify({ description: desc })
    });
    document.getElementById("cTags").value = res.tags.join(", ");
    renderTagPreview(res.tags);
  } catch (e) { showToast(e.message, "error"); }
});

document.getElementById("cTags").addEventListener("input", e => {
  renderTagPreview(e.target.value.split(",").map(t => t.trim()).filter(Boolean));
});

function renderTagPreview(tags) {
  document.getElementById("tagPreview").innerHTML =
    tags.map(t => `<span class="tag">${escHtml(t)}</span>`).join("");
}

document.getElementById("createCourseBtn").addEventListener("click", async () => {
  const title    = document.getElementById("cTitle").value.trim();
  const desc     = document.getElementById("cDesc").value.trim();
  const price    = parseFloat(document.getElementById("cPrice").value);
  const category = document.getElementById("cCategory").value;
  const tags     = document.getElementById("cTags").value.split(",").map(t => t.trim()).filter(Boolean);
  const resultEl = document.getElementById("createResult");

  if (!title) { resultEl.innerHTML = '<span class="error">Введите название</span>'; return; }
  try {
    // Используем Command API для создания курса
    const courseResult = await apiFetch("/api/command/execute", {
      method: "POST",
      body: JSON.stringify({
        type: "CreateCourse",
        params: { title, description: desc, price, category, tags }
      }),
    });
    resultEl.innerHTML = `<span class="success">✅ ${escHtml(courseResult.result)}</span>`;
    
    // Добавляем уроки через Command API
    if (courseResult.course_id && modules.length > 0) {
      for (const m of modules) {
        if (!m.title) continue;
        await apiFetch("/api/command/execute", {
          method: "POST",
          body: JSON.stringify({
            type: "AddLesson",
            params: { course_id: courseResult.course_id, title: m.title, content: m.content, order_num: m.order_num }
          }),
        });
      }
      resultEl.innerHTML += `<br><span class="success">📚 Добавлено ${modules.length} уроков</span>`;
    }
    modules = []; renderModules();
    showToast(`Курс создан! Можно отменить в админ-панели.`, "success");
  } catch (e) { resultEl.innerHTML = `<span class="error">${e.message}</span>`; }
});

// ── Vector Canvas (полярний графік similarity) ────────────────────────────

document.getElementById("loadVectorBtn").addEventListener("click", async () => {
  const userId = +document.getElementById("vectorUserId").value;
  try {
    const data = await apiFetch(`/api/users/${userId}/vector`);
    drawVectorCanvas(data);
  } catch (e) { showToast(e.message, "error"); }
});

function drawVectorCanvas(data) {
  const canvas = document.getElementById("vectorCanvas");
  const ctx = canvas.getContext("2d");
  const W = canvas.width, H = canvas.height;
  const cx = W / 2, cy = H / 2;
  const maxR = Math.min(cx, cy) - 40;

  ctx.clearRect(0, 0, W, H);
  ctx.fillStyle = "#1a1d27";
  ctx.fillRect(0, 0, W, H);

  // Сітка
  ctx.strokeStyle = "#2d3148"; ctx.lineWidth = 1;
  for (let r = maxR / 4; r <= maxR; r += maxR / 4) {
    ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.stroke();
  }
  ctx.strokeStyle = "#3a3f5c";
  ctx.beginPath(); ctx.moveTo(0, cy); ctx.lineTo(W, cy); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(cx, 0); ctx.lineTo(cx, H); ctx.stroke();

  ctx.fillStyle = "#8892a4"; ctx.font = "12px Segoe UI";
  ctx.fillText("similarity →", W - 90, cy - 8);
  ctx.fillText("↑ relevance", cx + 8, 20);

  const vectors = data.vectors || [];
  const colors = ["#6c63ff","#a78bfa","#34d399","#fbbf24","#f87171","#60a5fa","#fb923c","#e879f9"];

  vectors.forEach((v, i) => {
    const angle = (i / vectors.length) * Math.PI * 2 - Math.PI / 2;
    const len = v.similarity * maxR;
    const x = cx + Math.cos(angle) * len;
    const y = cy + Math.sin(angle) * len;
    const color = colors[i % colors.length];

    ctx.strokeStyle = v.enrolled ? color : color + "66";
    ctx.lineWidth = v.enrolled ? 2.5 : 1.5;
    ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(x, y); ctx.stroke();

    const headLen = 10;
    const ang = Math.atan2(y - cy, x - cx);
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(x - headLen * Math.cos(ang - 0.4), y - headLen * Math.sin(ang - 0.4));
    ctx.lineTo(x - headLen * Math.cos(ang + 0.4), y - headLen * Math.sin(ang + 0.4));
    ctx.closePath(); ctx.fill();

    ctx.beginPath(); ctx.arc(x, y, 5, 0, Math.PI * 2);
    ctx.fillStyle = color; ctx.fill();

    if (len > 20) {
      ctx.fillStyle = "#e2e8f0"; ctx.font = "11px Segoe UI";
      const lx = cx + Math.cos(angle) * (len + 16);
      const ly = cy + Math.sin(angle) * (len + 16);
      ctx.fillText(v.title.slice(0, 14), lx - 20, ly + 4);
    }
  });

  const legend = document.getElementById("vectorLegend");
  legend.innerHTML = vectors.map((v, i) => `
    <div class="legend-item">
      <span class="legend-dot" style="background:${colors[i % colors.length]}"></span>
      <span>${escHtml(v.title)}</span>
      <span class="legend-sim">${(v.similarity * 100).toFixed(1)}%</span>
      ${v.enrolled ? '<span class="tag" style="font-size:.7rem">enrolled</span>' : ""}
    </div>
  `).join("");
}

// ── Admin panel ───────────────────────────────────────────────────────────

// Кнопка отмены команд
document.getElementById("undoBtn").addEventListener("click", async () => {
  const result = document.getElementById("undoResult");
  result.innerHTML = '<span class="muted">Отменяем...</span>';
  try {
    const data = await apiFetch("/api/command/undo", { method: "POST" });
    result.innerHTML = `<span class="success">✅ ${escHtml(data.result)}</span>`;
    showToast("Команда отменена", "info");
  } catch (e) {
    result.innerHTML = `<span class="error">${e.message}</span>`;
  }
});

document.querySelectorAll(".cmd-btn").forEach(btn => {
  btn.addEventListener("click", async () => {
    const result = document.getElementById("cmdResult");
    result.innerHTML = '<span class="muted">Загрузка...</span>';
    try {
      let data;
      if (btn.dataset.cmd === "revenue") {
        data = await apiFetch("/api/analytics/revenue");
        result.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
      } else if (btn.dataset.cmd === "top") {
        data = await apiFetch("/api/analytics/top-students");
        result.innerHTML = data.map(s =>
          `<div>🏆 ${escHtml(s.uname)} — ${s.ucompleted} завершено</div>`
        ).join(""); // уже по-русски
      } else if (btn.dataset.cmd === "events") {
        data = await apiFetch("/api/events/log");
        result.innerHTML = data.slice(-10).reverse().map(e =>
          `<div class="event-row"><span class="muted">${e.timestamp}</span> <b>${e.type}</b></div>`
        ).join("");
      }
    } catch (e) { result.innerHTML = `<span class="error">${e.message}</span>`; }
  });
});

document.getElementById("stateBtn").addEventListener("click", async () => {
  const courseId = document.getElementById("stateCourseId").value;
  const action   = document.getElementById("stateAction").value;
  const result   = document.getElementById("stateResult");
  if (!courseId) { result.innerHTML = '<span class="error">Введите Course ID</span>'; return; }
  try {
    const data = await apiFetch(`/api/courses/${courseId}/state`, {
      method: "POST", body: JSON.stringify({ action }),
    });
    result.innerHTML = `<span class="success">${escHtml(data.message)}</span><br>Состояние: ${stateChip(data.state)}`;
    showToast(data.message, "info");
  } catch (e) { result.innerHTML = `<span class="error">${e.message}</span>`; }
});

document.getElementById("quizBtn").addEventListener("click", async () => {
  const topic  = document.getElementById("quizTopic").value.trim();
  const result = document.getElementById("quizResult");
  if (!topic) return;
  try {
    const data = await apiFetch("/api/quiz", {
      method: "POST", body: JSON.stringify({ topic, count: 3 }),
    });
    result.innerHTML = data.map((q, i) => `
      <div class="quiz-item">
        <b>Q${i+1}:</b> ${escHtml(q.question)}<br>
        <span class="muted">A: ${escHtml(q.answer)}</span>
      </div>
    `).join("");
  } catch (e) { result.innerHTML = `<span class="error">${e.message}</span>`; }
});

document.getElementById("loadUsersBtn").addEventListener("click", async () => {
  const result = document.getElementById("usersResult");
  try {
    const users = await apiFetch("/api/users");
    result.innerHTML = users.map(u => `
      <div class="event-row">
        <b>${escHtml(u.name)}</b>
        <span class="badge badge--${u.role}">${u.role}</span>
        <span class="muted">${escHtml(u.email)}</span>
      </div>
    `).join("");
  } catch (e) { result.innerHTML = `<span class="error">${e.message}</span>`; }
});

document.getElementById("notifyBtn").addEventListener("click", async () => {
  const message = document.getElementById("notifyMessage").value.trim();
  const result  = document.getElementById("notifyResult");
  if (!message) { result.innerHTML = '<span class="error">Введите текст уведомления</span>'; return; }
  try {
    await apiFetch("/api/notify", { method: "POST", body: JSON.stringify({ message }) });
    result.innerHTML = '<span class="success">✅ Отправлено!</span>';
    document.getElementById("notifyMessage").value = "";
    showToast(`🔔 Рассылка: ${message.slice(0, 40)}`, "info");
  } catch (e) { result.innerHTML = `<span class="error">${e.message}</span>`; }
});

// ── AI Widget ─────────────────────────────────────────────────────────────

let aiOpen = true;
document.getElementById("aiToggle").addEventListener("click", () => {
  aiOpen = !aiOpen;
  document.getElementById("aiBody").classList.toggle("hidden", !aiOpen);
  document.getElementById("aiChevron").textContent = aiOpen ? "▲" : "▼";
});

async function sendAiQuestion() {
  const question = document.getElementById("aiQuestion").value.trim();
  if (!question) return;
  const messages = document.getElementById("aiMessages");
  messages.innerHTML += `<div class="ai-msg ai-msg--user">${escHtml(question)}</div>`;
  document.getElementById("aiQuestion").value = "";
  messages.innerHTML += `<div class="ai-msg ai-msg--bot" id="aiTyping">...</div>`;
  messages.scrollTop = messages.scrollHeight;
  try {
    const res = await apiFetch("/api/chat", {
      method: "POST", body: JSON.stringify({ message: question }),
    });
    document.getElementById("aiTyping").textContent = res.reply;
    document.getElementById("aiTyping").removeAttribute("id");
  } catch (e) {
    document.getElementById("aiTyping").textContent = `Ошибка: ${e.message}`;
    document.getElementById("aiTyping").removeAttribute("id");
  }
  messages.scrollTop = messages.scrollHeight;
}

document.getElementById("aiSendBtn").addEventListener("click", sendAiQuestion);
document.getElementById("aiQuestion").addEventListener("keydown", e => {
  if (e.key === "Enter") sendAiQuestion();
});

// ── Modal ─────────────────────────────────────────────────────────────────

const overlay = document.getElementById("modalOverlay");
overlay.addEventListener("click", e => { if (e.target === overlay) closeModal(); });
document.getElementById("modalClose").addEventListener("click", closeModal);

function openModal(title, content) {
  document.getElementById("modalTitle").textContent = title;
  document.getElementById("modalContent").textContent = content || "Нет описания.";
  overlay.classList.add("open");
}
function closeModal() { overlay.classList.remove("open"); }

// ── Delete course function ──────────────────────────────────────────────

async function deleteCourse(courseId) {
  if (!confirm('Удалить курс? Это действие можно будет отменить.')) return;
  try {
    const result = await apiFetch(`/api/courses/${courseId}`, { method: "DELETE" });
    showToast(result.result + " (можно отменить)", "info");
    loadCourses(); // Перезагружаем список
  } catch (e) {
    showToast(e.message, "error");
  }
}

// ── Init ──────────────────────────────────────────────────────────────────

loadCourses();
applyRoleUI();

// Делаем функции глобальными для onclick
window.deleteCourse = deleteCourse;
window.loadLearn = loadLearn;
window.loadDetail = loadDetail;

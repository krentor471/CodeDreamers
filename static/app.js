// static/app.js — CodeDreamers frontend

const ROLE_SELECT = document.getElementById("roleSelect");

// ── Helpers ───────────────────────────────────────────────────────────────

function getRole() { return ROLE_SELECT.value; }

async function apiFetch(path) {
  const res = await fetch(path, { headers: { "X-Role": getRole() } });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err.error || res.statusText);
  }
  return res.json();
}

// ── Pages ─────────────────────────────────────────────────────────────────

const pages = {
  courses: document.getElementById("page-courses"),
  my:      document.getElementById("page-my"),
  detail:  document.getElementById("page-detail"),
};

function showPage(name) {
  Object.values(pages).forEach(p => p.classList.remove("active"));
  pages[name].classList.add("active");
  document.querySelectorAll(".nav-btn").forEach(b => {
    b.classList.toggle("active", b.dataset.page === name);
  });
}

document.querySelectorAll(".nav-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    showPage(btn.dataset.page);
    if (btn.dataset.page === "courses") loadCourses();
    if (btn.dataset.page === "my")      loadMyCourses();
  });
});

document.getElementById("backBtn").addEventListener("click", () => {
  showPage("courses");
  loadCourses();
});

ROLE_SELECT.addEventListener("change", () => {
  const active = document.querySelector(".page.active");
  if (active?.id === "page-courses") loadCourses();
  if (active?.id === "page-my")      loadMyCourses();
});

// ── Skeleton ──────────────────────────────────────────────────────────────

function renderSkeletons(container, count = 6) {
  container.innerHTML = Array(count)
    .fill('<div class="skeleton skeleton-card"></div>')
    .join("");
}

// ── Courses page ──────────────────────────────────────────────────────────

async function loadCourses() {
  const grid = document.getElementById("courseGrid");
  renderSkeletons(grid);
  try {
    const courses = await apiFetch("/api/courses");
    if (!courses.length) {
      grid.innerHTML = '<p class="empty">Курсы не найдены.</p>';
      return;
    }
    grid.innerHTML = courses.map(c => `
      <div class="course-card" data-id="${c.id}">
        <div class="course-card__title">${c.title}</div>
        <div class="course-card__desc">${c.description || ""}</div>
        <div class="course-card__footer">
          <span class="course-card__price">$${c.price.toFixed(2)}</span>
          <span class="badge badge--${c.difficulty_level}">${c.difficulty_level}</span>
        </div>
      </div>
    `).join("");
    grid.querySelectorAll(".course-card").forEach(card => {
      card.addEventListener("click", () => loadDetail(+card.dataset.id));
    });
  } catch (e) {
    grid.innerHTML = `<p class="empty">${e.message}</p>`;
  }
}

// ── My courses page ───────────────────────────────────────────────────────

async function loadMyCourses() {
  const list = document.getElementById("myList");
  renderSkeletons(list, 3);
  // user_id=1 — первый студент из seed (Alice)
  try {
    const items = await apiFetch("/api/users/1/enrollments");
    if (!items.length) {
      list.innerHTML = '<p class="empty">Нет записей на курсы.</p>';
      return;
    }
    list.innerHTML = items.map(e => `
      <div class="my-item" data-id="${e.course_id}">
        <span class="my-item__title">${e.title}</span>
        <span class="my-item__status status--${e.status}">${e.status}</span>
      </div>
    `).join("");
    list.querySelectorAll(".my-item").forEach(item => {
      item.addEventListener("click", () => loadDetail(+item.dataset.id));
    });
  } catch (e) {
    list.innerHTML = `<p class="empty">${e.message}</p>`;
  }
}

// ── Detail page (Composite tree) ──────────────────────────────────────────

async function loadDetail(courseId) {
  showPage("detail");
  const container = document.getElementById("detailContent");
  container.innerHTML = '<div class="skeleton skeleton-card" style="height:80px;margin-bottom:24px"></div>';

  try {
    const [course, program] = await Promise.all([
      apiFetch(`/api/courses/${courseId}`),
      apiFetch(`/api/courses/${courseId}/program`),
    ]);

    container.innerHTML = `
      <div class="detail__header">
        <div>
          <div class="detail__title">${course.title}</div>
          <div class="detail__meta">
            <span class="badge badge--${course.difficulty_level}">${course.difficulty_level}</span>
            <span class="detail__price">$${course.price.toFixed(2)}</span>
          </div>
          <p style="color:var(--muted);margin-top:10px;font-size:.9rem">${course.description || ""}</p>
        </div>
      </div>
      <div class="program">${renderProgram(program)}</div>
    `;

    // Аккордеон для блоков
    container.querySelectorAll(".program__block-header").forEach(header => {
      header.addEventListener("click", () => {
        const lessons = header.nextElementSibling;
        const chevron = header.querySelector(".chevron");
        lessons.classList.toggle("open");
        chevron.classList.toggle("open");
      });
    });

    // Клик по уроку — модалка
    container.querySelectorAll(".lesson-item").forEach(item => {
      item.addEventListener("click", () => openModal(
        item.dataset.title,
        item.dataset.content
      ));
    });

  } catch (e) {
    container.innerHTML = `<p class="empty">${e.message}</p>`;
  }
}

// ── Composite tree renderer ───────────────────────────────────────────────

function renderProgram(node) {
  if (!node || !node.children) return '<p class="empty">Программа пуста.</p>';

  return node.children.map((block, bi) => `
    <div class="program__block">
      <div class="program__block-header">
        <div class="program__block-title">
          <div class="block-icon">B${bi + 1}</div>
          ${block.title}
        </div>
        <span class="chevron">&#9660;</span>
      </div>
      <div class="program__lessons">
        ${(block.children || []).map(lesson => `
          <div class="lesson-item"
               data-title="${escHtml(lesson.title)}"
               data-content="${escHtml(lesson.content || '')}">
            <div class="lesson-num">${lesson.order_num}</div>
            <div>
              <div class="lesson-title">${lesson.title}</div>
              <div class="lesson-content">${lesson.content || ""}</div>
            </div>
          </div>
        `).join("")}
      </div>
    </div>
  `).join("");
}

// ── Modal ─────────────────────────────────────────────────────────────────

const overlay = document.createElement("div");
overlay.className = "modal-overlay";
overlay.innerHTML = `
  <div class="modal">
    <div class="modal__title" id="modalTitle"></div>
    <div class="modal__content" id="modalContent"></div>
    <button class="modal__close" id="modalClose">Закрыть</button>
  </div>
`;
document.body.appendChild(overlay);

overlay.addEventListener("click", e => { if (e.target === overlay) closeModal(); });
document.getElementById("modalClose").addEventListener("click", closeModal);

function openModal(title, content) {
  document.getElementById("modalTitle").textContent = title;
  document.getElementById("modalContent").textContent = content || "Нет описания.";
  overlay.classList.add("open");
}
function closeModal() { overlay.classList.remove("open"); }

// ── Utils ─────────────────────────────────────────────────────────────────

function escHtml(str) {
  return str.replace(/&/g,"&amp;").replace(/"/g,"&quot;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}

// ── Init ──────────────────────────────────────────────────────────────────

loadCourses();

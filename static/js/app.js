const root = document.documentElement;
const themeToggle = document.querySelector("[data-theme-toggle]");

function applyTheme(theme) {
  root.setAttribute("data-theme", theme);
  if (themeToggle) {
    themeToggle.setAttribute("aria-pressed", theme === "dark");
  }
}

const savedTheme = localStorage.getItem("naumur-theme");
if (savedTheme) {
  applyTheme(savedTheme);
} else {
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  applyTheme(prefersDark ? "dark" : "light");
}

if (themeToggle) {
  themeToggle.addEventListener("click", () => {
    const current = root.getAttribute("data-theme") || "light";
    const next = current === "dark" ? "light" : "dark";
    applyTheme(next);
    localStorage.setItem("naumur-theme", next);
  });
}

document.querySelectorAll(".toggle-password").forEach((button) => {
  button.addEventListener("click", () => {
    const targetId = button.getAttribute("data-target");
    const input = document.getElementById(targetId);
    if (!input) return;
    const isPassword = input.getAttribute("type") === "password";
    input.setAttribute("type", isPassword ? "text" : "password");
    button.setAttribute("aria-pressed", isPassword);
  });
});

const modal = document.getElementById("employee-modal");
const modalClose = document.querySelector("[data-modal-close]");
const modalTitle = document.getElementById("modal-title");
const modalSubtitle = document.getElementById("modal-subtitle");
const modalStart = document.getElementById("modal-start");
const modalStatus = document.getElementById("modal-status");
const modalHours = document.getElementById("modal-hours");
const modalAbsences = document.getElementById("modal-absences");
const modalAbsentHours = document.getElementById("modal-absent-hours");

function closeModal() {
  if (!modal) return;
  modal.classList.remove("active");
  modal.setAttribute("aria-hidden", "true");
}

function openModal(card) {
  if (!modal || !card || !modalTitle) return;
  const name = card.dataset.name || "";
  modalTitle.textContent = name || modalTitle.textContent;
  if (modalSubtitle) modalSubtitle.textContent = card.dataset.status || "";
  if (modalStart) modalStart.textContent = card.dataset.start || "--";
  if (modalStatus) modalStatus.textContent = card.dataset.status || "--";
  if (modalHours) modalHours.textContent = card.dataset.hours || "0";
  if (modalAbsences) modalAbsences.textContent = card.dataset.absences || "0";
  if (modalAbsentHours) modalAbsentHours.textContent = card.dataset.absentHours || "0";
  modal.classList.add("active");
  modal.setAttribute("aria-hidden", "false");
}

document.querySelectorAll(".employee-card").forEach((card) => {
  card.addEventListener("click", () => openModal(card));
});

if (modalClose) {
  modalClose.addEventListener("click", closeModal);
}

if (modal) {
  modal.addEventListener("click", (event) => {
    if (event.target === modal) {
      closeModal();
    }
  });
}

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeModal();
  }
});

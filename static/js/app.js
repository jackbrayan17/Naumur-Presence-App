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

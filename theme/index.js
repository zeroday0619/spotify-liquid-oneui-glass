import { Registrar } from "/modules/stdlib/mod.js";
import { installAppleIcons } from "./icons.js";
import { installLightModeLock } from "./light-mode.js";

const storageKey = "liquid-glass-local:tint";
const defaultTint = 65;
const modeStorageKey = "liquid-glass-local:mode";
const icon = '<path d="M2 4h12v1H2zm0 7h12v1H2z"/><circle cx="6" cy="4.5" r="2"/><circle cx="10" cy="11.5" r="2"/>';

export function load() {
  const root = document.documentElement;
  const designStyle = document.createElement("link");
  designStyle.rel = "stylesheet";
  designStyle.href = "/modules/liquid-glass-local/oneui.css";
  document.head.appendChild(designStyle);
  const paletteStyle = document.createElement("link");
  paletteStyle.rel = "stylesheet";
  paletteStyle.href = "/modules/liquid-glass-local/sakura.css";
  document.head.appendChild(paletteStyle);
  const coverageStyle = document.createElement("link");
  coverageStyle.rel = "stylesheet";
  coverageStyle.href = "/modules/liquid-glass-local/coverage.css";
  document.head.appendChild(coverageStyle);
  const interactionStyles = ["interaction-fixes.css", "iv-sakura.css", "npv-contrast.css", "player-contrast.css", "npv-details.css", "regression-contrast.css", "artist-page-contrast.css", "settings-contrast.css"].map((name) => {
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = `/modules/liquid-glass-local/${name}`;
    document.head.appendChild(link);
    return link;
  });
  const originalNativeThemes = ["encore-dark-theme", "encore-light-theme"]
    .filter((name) => root.classList.contains(name));
  const registrar = new Registrar("liquid-glass-local");
  const listeners = new AbortController();
  let tint = defaultTint;
  try {
    localStorage.setItem(modeStorageKey, "light");
    const saved = localStorage.getItem(storageKey);
    if (saved !== null && saved.trim() !== "" && Number.isFinite(Number(saved))) {
      tint = Math.min(100, Math.max(0, Number(saved)));
    }
  } catch {
    // The theme remains usable when browser storage is unavailable.
  }

  const dialog = document.createElement("dialog");
  dialog.className = "lg-settings-dialog";
  dialog.setAttribute("aria-labelledby", "lg-settings-title");
  dialog.setAttribute("aria-describedby", "lg-settings-description");
  const title = document.createElement("h2");
  title.id = "lg-settings-title";
  title.textContent = "Liquid One UI Glass 설정";
  const description = document.createElement("p");
  description.id = "lg-settings-description";
  description.textContent = "틴트 강도를 높이면 배경이 더 진해져 글자를 읽기 편해집니다.";
  const label = document.createElement("label");
  label.htmlFor = "lg-tint-slider";
  label.textContent = "틴트 강도";
  const slider = document.createElement("input");
  slider.type = "range";
  slider.id = "lg-tint-slider";
  slider.min = "0";
  slider.max = "100";
  slider.step = "1";
  slider.value = String(tint);
  const value = document.createElement("output");
  value.htmlFor = slider.id;
  const closeButton = document.createElement("button");
  closeButton.type = "button";
  closeButton.textContent = "닫기";
  dialog.append(title, description, label, slider, value, closeButton);
  document.body.appendChild(dialog);

  function applyTint() {
    root.style.setProperty("--lg-tint", String(tint));
    root.style.setProperty("--lg-glass-alpha", (0.12 + tint * 0.0083).toFixed(4));
    root.style.setProperty("--lg-panel-alpha", (0.12 + tint * 0.0084).toFixed(4));
    value.textContent = `${tint}%`;
    slider.setAttribute("aria-valuetext", `${tint}%`);
  }

  slider.addEventListener("input", () => {
    tint = Number(slider.value);
    applyTint();
    try {
      localStorage.setItem(storageKey, String(tint));
    } catch {
      // The current session still applies changes without persistent storage.
    }
  }, { signal: listeners.signal });
  closeButton.addEventListener("click", () => dialog.close(), { signal: listeners.signal });
  root.classList.add("liquid-glass-local");
  const disposeLightMode = installLightModeLock(root);
  applyTint();
  const disposeIcons = installAppleIcons();
  registrar.placeButton("topbar-right", {
    label: "Liquid One UI Glass 설정",
    icon,
    onClick: () => {
      if (!dialog.open) dialog.showModal();
      slider.focus();
    },
  });

  return () => {
    disposeLightMode();
    interactionStyles.forEach((link) => link.remove());
    coverageStyle.remove();
    paletteStyle.remove();
    designStyle.remove();
    disposeIcons();
    registrar.dispose();
    listeners.abort();
    if (dialog.open) dialog.close();
    dialog.remove();
    root.classList.remove("liquid-glass-local");
    delete root.dataset.lgMode;
    root.classList.remove("encore-dark-theme", "encore-light-theme");
    root.classList.add(...originalNativeThemes);
    for (const property of ["--lg-tint", "--lg-glass-alpha", "--lg-panel-alpha"]) {
      root.style.removeProperty(property);
    }
  };
}

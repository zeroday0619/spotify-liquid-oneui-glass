/* Spotify may replace its root theme while navigating or restoring preferences. */
export function installLightModeLock(root) {
  function enforceLightMode() {
    if (root.dataset.lgMode !== "light") root.dataset.lgMode = "light";
    if (root.classList.contains("encore-dark-theme")) root.classList.remove("encore-dark-theme");
    if (!root.classList.contains("encore-light-theme")) root.classList.add("encore-light-theme");
  }
  enforceLightMode();
  const observer = new MutationObserver(enforceLightMode);
  observer.observe(root, { attributes: true, attributeFilter: ["class", "data-lg-mode"] });
  return () => observer.disconnect();
}

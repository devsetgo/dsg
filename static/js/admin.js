// App shell behavior for templates/base.html (MDB UI Kit shell).
// The initial theme is applied by a tiny inline script at the top of <head>
// (before first paint, to avoid a flash of the wrong theme) - this file only
// handles the toggle switch's own UI state and persisting a change.
(function () {
  var toggle = document.getElementById("themeToggle");
  if (!toggle) return;

  toggle.checked = document.documentElement.dataset.mdbTheme === "dark";

  toggle.addEventListener("change", function () {
    var theme = toggle.checked ? "dark" : "light";
    document.documentElement.dataset.mdbTheme = theme;
    try {
      localStorage.setItem("dsg-theme", theme);
    } catch (e) {
      // localStorage unavailable (private browsing, blocked storage) - the
      // toggle still works for this page load, it just won't persist.
    }
  });
})();

// Copy buttons: <button data-copy-target="#id"> copies that element's text.
document.addEventListener("click", function (event) {
  var button = event.target.closest("[data-copy-target]");
  if (!button) return;
  var source = document.querySelector(button.getAttribute("data-copy-target"));
  if (!source || !navigator.clipboard) return;
  navigator.clipboard.writeText(source.innerText).then(function () {
    var original = button.innerHTML;
    button.innerHTML = '<i class="fa-solid fa-check me-1"></i>Copied';
    setTimeout(function () { button.innerHTML = original; }, 1500);
  });
});

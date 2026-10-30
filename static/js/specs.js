// The specs page (spec §5.3, templates/specs.html): the "Show only the N differences" toggle, nothing else. The server
// renders every row; this hides the rows without a difference (class "diff") and the groups left empty.
const btn = document.getElementById("only");
if (btn) {
  btn.hidden = false;   // without JS the button would do nothing, so it starts hidden
  const apply = (only) => {
    document.querySelectorAll("#sheet tr").forEach((tr) => { tr.hidden = only && !tr.classList.contains("diff"); });
    document.querySelectorAll("#sheet .sgroup").forEach((g) => { g.hidden = only && !g.querySelector("tr.diff"); });
    btn.setAttribute("aria-pressed", String(only));
    btn.textContent = only ? btn.dataset.all : btn.dataset.only;
  };
  btn.addEventListener("click", () => apply(btn.getAttribute("aria-pressed") !== "true"));
}

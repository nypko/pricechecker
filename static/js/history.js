// History page (spec §5.6, templates/history.html): the version switch. Without JS both versions show stacked; with it,
// one shows at a time (the one the page marks as default) and the chips under the intro swap them.
import { wireShare } from "./share.js";

const root = document.getElementById("history");
if (root) {
  const chips = [...root.querySelectorAll("#hver button")];
  const show = (e) => {
    root.querySelectorAll("section.hv").forEach((s) => { s.hidden = s.dataset.e !== e; });
    chips.forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.e === e)));
  };
  chips.forEach((b) => b.addEventListener("click", () => show(b.dataset.e)));
  wireShare(root.querySelector(".share"));
  if (chips.length) show(root.dataset.default);
}

// Stores list (spec §5.7, templates/stores.html): the delivery chips. Every store row is in the HTML; a chip hides the rows
// without that property (data-f-<key> on the row, worked out from stores.yaml for delivery to the EU). Chips combine
// (a store must have every chosen property). Nothing here touches a price.

/** True when a row's flags include every chosen key: keeps({tax: true}, ["tax"]). */
export const keeps = (flags, chosen) => chosen.every((k) => flags[k]);

const root = document.getElementById("stores");
if (root) {
  const rows = [...root.querySelectorAll("#list > li.st")];
  const chips = [...root.querySelectorAll("#chips button")];
  const chosen = new Set();
  const flags = (li) => Object.fromEntries(chips.map((b) => [b.dataset.f, li.hasAttribute(`data-f-${b.dataset.f}`)]));
  const apply = () => {
    let n = 0;
    rows.forEach((li) => { const on = keeps(flags(li), [...chosen]); li.hidden = !on; n += on; });
    chips.forEach((b) => b.setAttribute("aria-pressed", String(chosen.has(b.dataset.f))));
    const none = root.querySelector("#no-results");
    if (none) none.hidden = n > 0;
    const c = root.querySelector("#count");
    if (c) c.textContent = chosen.size ? `${n} of ${rows.length} stores. Counts on the chips are for delivery to the EU.` : "Counts are for delivery to the EU. Other regions are in each store's row.";
  };
  chips.forEach((b) => b.addEventListener("click", () => { const k = b.dataset.f; chosen.has(k) ? chosen.delete(k) : chosen.add(k); apply(); }));
}

// "Checked ... ago": the build stamps each page with its time; the browser says how long ago that was.
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** "just now" (under 2 min, or a time ahead of the visitor's clock), "N min ago", "N h ago" (under 24 h), else "on 9 Nov"
 *  (UTC day); null when iso is not a date. */
export function agoText(iso, nowMs) {
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return null;
  const min = Math.floor((nowMs - t) / 60000);
  if (min < 2) return "just now";
  if (min < 60) return `${min} min ago`;
  if (min < 1440) return `${Math.floor(min / 60)} h ago`;
  const d = new Date(t);
  return `on ${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}`;
}

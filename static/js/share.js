// The Share button (phone and history pages): the device's share sheet, else copy the canonical link.
// wireShare(button, suffix) shows the button when either works; suffix() adds to the link (the phone page's "#16-512-china" pick).
export function wireShare(sb, suffix = () => "") {
  const canCopy = navigator.clipboard && window.isSecureContext;
  if (!sb || !(navigator.share || canCopy)) return;
  sb.hidden = false;
  sb.addEventListener("click", () => {
    const canon = document.querySelector('link[rel="canonical"]');
    const url = (canon ? canon.href : location.href.split("#")[0]) + suffix();
    if (navigator.share) { navigator.share({ title: document.title, url }).catch(() => {}); return; }   // closed without sharing: fine
    navigator.clipboard.writeText(url).then(() => { sb.textContent = "Link copied"; setTimeout(() => { sb.textContent = "Share"; }, 2000); });
  });
}

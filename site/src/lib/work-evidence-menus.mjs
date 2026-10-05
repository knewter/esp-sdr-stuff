/** Share the immutable modal proof list with its card's native details menu. */
export function populateWorkEvidenceMenu(details, root) {
  if (!details.open || details.dataset.evidenceLoaded === "true") return;
  const template = root.getElementById(`work-detail-${details.dataset.workEvidence}`);
  const evidence = template?.content?.querySelector(".detail-evidence");
  const menu = details.querySelector("nav");
  // Keep the ordinary same-detail fallback if a proof list is unavailable.
  if (!menu || !evidence?.childElementCount) return;
  menu.replaceChildren(...Array.from(evidence.childNodes, (node) => node.cloneNode(true)));
  details.dataset.evidenceLoaded = "true";
}

export function installWorkEvidenceMenus(root) {
  root.querySelectorAll(".card-evidence").forEach((details) => {
    details.addEventListener("toggle", () => populateWorkEvidenceMenu(details, root));
    // Preserve native restored/open state as well as later keyboard/tap toggles.
    populateWorkEvidenceMenu(details, root);
  });
}

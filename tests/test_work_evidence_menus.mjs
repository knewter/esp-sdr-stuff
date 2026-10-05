import assert from "node:assert/strict";
import fs from "node:fs";
import { installWorkEvidenceMenus, populateWorkEvidenceMenu } from "../site/src/lib/work-evidence-menus.mjs";

// Minimal structural DOM model. Real keyboard/focus/layout checks belong to the
// production browser suite; this checks exact clone, event and URL conservation.
class Node {
  constructor(tag, attrs = {}, children = [], text = "") {
    this.tag = tag; this.attrs = { ...attrs }; this.childNodes = children; this.text = text;
  }
  get childElementCount() { return this.childNodes.filter((node) => node.tag).length; }
  cloneNode(deep) { return new Node(this.tag, this.attrs, deep ? this.childNodes.map((node) => node.cloneNode(true)) : [], this.text); }
  replaceChildren(...children) { this.childNodes = children; }
}
const text = (value) => new Node(null, {}, [], value);
const link = (href, label, attrs = {}) => new Node("a", { href, ...attrs }, [text(label)]);
const snapshot = (node) => ({ tag: node.tag, attrs: node.attrs, children: node.childNodes.map(snapshot), text: node.text });
const details = (id, open = false) => {
  const menu = new Node("nav", { "aria-label": `Evidence for ${id}` }, [link(`./?work=${encodeURIComponent(id)}`, "Open proposal and evidence")]);
  return { open, dataset: { workEvidence: id }, menu, listeners: [],
    querySelector: (selector) => selector === "nav" ? menu : null,
    addEventListener(event, callback) { assert.equal(event, "toggle"); this.listeners.push(callback); },
    toggle(open) { this.open = open; this.listeners.forEach((callback) => callback()); },
  };
};
const root = (cards, groups) => ({
  querySelectorAll(selector) { assert.equal(selector, ".card-evidence"); return cards; },
  getElementById(id) { return groups[id] === undefined ? null : { content: { querySelector(selector) { assert.equal(selector, ".detail-evidence"); return groups[id]; } } }; },
});
let groupsPassed = 0;
const group = new Node("span", { class: "detail-evidence" }, [
  link("../evidence/a/?download=1#bytes", "proof / README.md", { title: "A & B", "data-original": "" }),
  text("\n"),
  link("../source/abc/docs/raw%20samples.json?#", "raw / samples.json", { download: "", rel: "noopener" }),
]);
const original = structuredClone(snapshot(group));
const card = details("fixture:α"); const document = root([card], { "work-detail-fixture:α": group });
installWorkEvidenceMenus(document);
assert.equal(card.listeners.length, 1);
assert.equal(card.dataset.evidenceLoaded, undefined);
assert.equal(card.menu.childNodes[0].childNodes[0].text, "Open proposal and evidence");
groupsPassed++;
card.toggle(true);
assert.equal(card.dataset.evidenceLoaded, "true");
assert.deepEqual(card.menu.childNodes.map(snapshot), group.childNodes.map(snapshot));
assert.notEqual(card.menu.childNodes[0], group.childNodes[0]);
assert.notEqual(card.menu.childNodes[0].attrs, group.childNodes[0].attrs);
assert.notEqual(card.menu.childNodes[0].childNodes[0], group.childNodes[0].childNodes[0]);
assert.deepEqual(snapshot(group), original);
groupsPassed++;
for (const base of ["https://example.com/work/", "https://example.com/esp-sdr-stuff/work/?work=fixture&doc=2"]) {
  card.menu.childNodes.filter((node) => node.tag === "a").forEach((node, index) => {
    assert.equal(new URL(node.attrs.href, base).href, new URL(group.childNodes.filter((entry) => entry.tag === "a")[index].attrs.href, base).href);
  });
}
groupsPassed++;
const retained = card.menu.childNodes[0];
card.toggle(false); card.toggle(true); card.toggle(true);
assert.equal(card.menu.childNodes[0], retained); // reopen preserves link/focus node identity
groupsPassed++;
const missing = details("missing"); missing.toggle(true);
const fallback = missing.menu.childNodes[0];
populateWorkEvidenceMenu(missing, root([], {}));
assert.equal(missing.menu.childNodes[0], fallback); assert.equal(missing.dataset.evidenceLoaded, undefined);
populateWorkEvidenceMenu(missing, root([], { "work-detail-missing": null }));
assert.equal(missing.menu.childNodes[0], fallback);
groupsPassed++;
const empty = details("empty", true);
populateWorkEvidenceMenu(empty, root([], { "work-detail-empty": new Node("span") }));
assert.equal(empty.dataset.evidenceLoaded, undefined);
const noMenu = { open: true, dataset: { workEvidence: "fixture:α" }, querySelector: () => null };
populateWorkEvidenceMenu(noMenu, document); assert.equal(noMenu.dataset.evidenceLoaded, undefined);
groupsPassed++;
const other = details("other", true);
const otherGroup = new Node("span", {}, [link("../evidence/other/", "separate proof")]);
installWorkEvidenceMenus(root([other], { "work-detail-other": otherGroup }));
assert.deepEqual(other.menu.childNodes.map(snapshot), otherGroup.childNodes.map(snapshot));
assert.notEqual(other.menu.childNodes[0].attrs.href, card.menu.childNodes[0].attrs.href);
groupsPassed++;
const coalesced = details("coalesced"); installWorkEvidenceMenus(root([coalesced], { "work-detail-coalesced": group }));
coalesced.open = true; coalesced.open = false; coalesced.listeners[0]();
assert.equal(coalesced.dataset.evidenceLoaded, undefined);
coalesced.toggle(true); assert.equal(coalesced.dataset.evidenceLoaded, "true");
groupsPassed++;
let fixtureCards = 0, fixtureLinks = 0;
if (process.env.WORK_EVIDENCE_FIXTURE) {
  const fixture = JSON.parse(fs.readFileSync(process.env.WORK_EVIDENCE_FIXTURE, "utf8"));
  for (const item of fixture) {
    const proof = new Node("span", {}, item.links.map((record) => link(record.attrs.href, record.text, record.attrs)));
    const menu = details(item.id); const frozen = structuredClone(snapshot(proof));
    installWorkEvidenceMenus(root([menu], { [`work-detail-${item.id}`]: proof })); menu.toggle(true);
    assert.deepEqual(menu.menu.childNodes.map(snapshot), proof.childNodes.map(snapshot));
    assert.deepEqual(snapshot(proof), frozen);
    for (const base of ["https://example.com/work/", "https://example.com/esp-sdr-stuff/work/?work=fixture&doc=2"]) {
      menu.menu.childNodes.forEach((entry, index) => assert.equal(new URL(entry.attrs.href, base).href, new URL(item.links[index].attrs.href, base).href));
    }
    fixtureCards++; fixtureLinks += item.links.length;
  }
}
console.log(JSON.stringify({ groupsPassed, fixtureCards, fixtureLinks, scope: "structural DOM model; production browser validation remains required" }));

import assert from "node:assert/strict";
import { workMarkdownLinks } from "../site/src/lib/work-markdown.mjs";

const source = "openspec/changes/example/design.md";
const evidence = [
  { path: "docs/evidence/example/README.md", slug: "docs-evidence-example-readme-md", kind: "text" },
  { path: "docs/evidence/example/image.png", slug: "docs-evidence-example-image-png", kind: "image", asset: "assets/example.png" },
];
const documents = [{ path: "openspec/changes/example/tasks.md", workId: "example", section: 2 }];
const rewrite = workMarkdownLinks(source, evidence, documents, ["docs/evidence/example/README.md", "docs/evidence/example/image.png", "openspec/changes/example/tasks.md"], "/esp32-sdr-stuff/", "1234567");
const link = (href, tagName = "a") => ({ type: "element", tagName, properties: { [tagName === "a" ? "href" : "src"]: href }, children: [] });
const render = (node) => { rewrite()({ type: "root", children: [node] }); return node.properties.href ?? node.properties.src; };

assert.equal(render(link("docs/evidence/example/README.md")), "/esp32-sdr-stuff/evidence/docs-evidence-example-readme-md/");
assert.equal(render(link("tasks.md")), "/esp32-sdr-stuff/work/?work=example&doc=2");
assert.equal(render(link("https://github.com/omacom/omarchy")), "https://github.com/omacom/omarchy");
assert.equal(render(link("https://docs.example.com/new-public-reference")), "https://docs.example.com/new-public-reference");
assert.equal(render(link("#section")), "#section");
assert.equal(render(link("docs/evidence/example/image.png", "img")), "/esp32-sdr-stuff/assets/example.png");
assert.throws(() => render(link("missing.md")), /no committed target/);
assert.throws(() => render(link("docs/evidence/example/README.md", "img")), /no published asset/);
for (const href of ["javascript:alert(1)", "data:text/html,evil", "//private.example/", "http://example.com/", "https://127.0.0.1/private", "https://localhost/private", "https://tool.local/x", "https://private.invalid/x", "https://user:pass@example.com/", "https://example.com:8443/", "/tmp/hidden"])
  assert.throws(() => render(link(href)), /unsupported work Markdown link/);
assert.throws(() => render(link("https://github.com/image.png", "img")), /unsupported work Markdown link/);
// The same template URLs must target the same resources before and after modal
// cloning at both the development root and the GitHub Pages project prefix.
const rawPath = "docs/evidence/example/raw samples.bin";
const sourcePath = "docs/research/example.md";
const paths = [...evidence.map((file) => file.path), documents[0].path, rawPath, sourcePath];
let relativeCases = 0;
for (const base of ["/", "/esp-sdr-stuff/"]) {
  const page = `${base}work/`;
  const absolute = workMarkdownLinks(source, evidence, documents, paths, base, "1234567");
  const compact = workMarkdownLinks(source, evidence, documents, paths, base, "1234567", page);
  const rewriteWith = (plugin, href, tag = "a") => {
    const node = link(href, tag);
    plugin()({ type: "root", children: [node] });
    return node.properties.href ?? node.properties.src;
  };
  const cases = [
    ["docs/evidence/example/README.md", "a", "../evidence/docs-evidence-example-readme-md/"],
    ["docs/evidence/example/README.md?download=1#details", "a", "../evidence/docs-evidence-example-readme-md/?download=1#details"],
    ["tasks.md", "a", "./?work=example&doc=2"],
    ["docs/evidence/example/image.png?size=large#crop", "img", "../assets/example.png?size=large#crop"],
    ["docs/evidence/example/image.png#image", "a", "../evidence/docs-evidence-example-image-png/#image"],
    [rawPath + "?download=1#bytes", "a", "https://github.com/knewter/esp-sdr-stuff/blob/1234567/docs/evidence/example/raw%20samples.bin?download=1#bytes"],
    [sourcePath + "?plain=1#method", "a", "https://github.com/knewter/esp-sdr-stuff/blob/1234567/docs/research/example.md?plain=1#method"],
    ["#section", "a", "#section"],
    ["https://github.com/example/project?tab=readme#usage", "a", "https://github.com/example/project?tab=readme#usage"],
  ];
  for (const [input, tag, expected] of cases) {
    const original = rewriteWith(absolute, input, tag);
    const serialized = rewriteWith(compact, input, tag);
    assert.equal(serialized, expected);
    for (const origin of ["http://localhost:4321", "https://knewter.github.io"]) {
      const documentUrl = `${origin}${page}`;
      assert.equal(new URL(serialized, documentUrl).href, new URL(original, documentUrl).href);
      // A cloned template has this same owner-document base, including query state.
      assert.equal(new URL(serialized, `${documentUrl}?work=example&doc=1`).href,
        new URL(original, `${documentUrl}?work=example&doc=1`).href);
    }
    relativeCases++;
  }
  assert.equal(rewriteWith(absolute, "tasks.md"), `${base}work/?work=example&doc=2`);
}
console.log(`work Markdown links: original 20 assertions and ${relativeCases} relative URL cases passed`);

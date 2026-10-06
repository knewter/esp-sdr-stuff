import path from "node:path";
import { url, type EvidenceFile } from "./specs";
import { SELF_HOSTED, githubBlobUrl } from "./repository.mjs";

type Node = { type?: string; tagName?: string; properties?: Record<string, unknown>; children?: Node[] };



function encodedPath(value: string): string {
  return value.split("/").map(encodeURIComponent).join("/");
}

/** Images are self-hosted; every other committed file links to GitHub. */
export function rawEvidenceUrl(revision: string, filePath: string): string {
  return SELF_HOSTED.test(filePath)
    ? url(`source/${revision}/${encodedPath(filePath)}`)
    : githubBlobUrl(revision, filePath);
}

/** Serialize an internal URL relative to the document that renders it. */
export function relativeEvidenceUrl(value: string, pagePath: string): string {
  if (/^[a-z][a-z\d+.-]*:/i.test(value)) return value; // external (GitHub) link
  const [, pathname, suffix = ""] = /^([^?#]+)([?#].*)?$/.exec(value)!;
  const directory = pagePath.endsWith("/") ? pagePath : path.posix.dirname(pagePath);
  let relative = path.posix.relative(directory, pathname);
  if (pathname.endsWith("/")) relative = relative ? `${relative}/` : "./";
  else if (!relative) relative = `../${path.posix.basename(pathname)}`;
  return `${relative}${suffix}`;
}

/** Repoint repository-relative Markdown links after Astro has parsed them. */
export function evidenceMarkdownLinks(
  sourcePath: string,
  files: EvidenceFile[],
  base: string,
  revision: string,
  pagePath?: string,
) {
  const pages = new Map(files.map((file) => [file.path, file]));
  const siteBase = base.endsWith("/") ? base : `${base}/`;
  const localUrl = (value: string) => pagePath === undefined ? value : relativeEvidenceUrl(value, pagePath);
  return () => (tree: Node) => {
    function visit(node: Node): void {
      if (node.type === "element" && (node.tagName === "a" || node.tagName === "img")) {
        const key = node.tagName === "a" ? "href" : "src";
        const value = node.properties?.[key];
        if (typeof value === "string" && !/^(?:[a-z][a-z\d+.-]*:|\/|#)/i.test(value)) {
          const match = /^([^?#]+)([?#].*)?$/.exec(value);
          if (match) {
            let relative: string;
            try { relative = decodeURIComponent(match[1]); }
            catch { relative = match[1]; }
            const repositoryRootPath = /^(?:docs|openspec|tools|scripts|tests|\.skills)\//.test(relative);
            const target = path.posix.normalize(repositoryRootPath ? relative : path.posix.join(path.posix.dirname(sourcePath), relative));
            if (target !== ".." && !target.startsWith("../")) {
              const page = pages.get(target);
              const targetUrl = page && (node.tagName === "a" || page.kind !== "image")
                ? `${siteBase}evidence/${page.slug}/${match[2] ?? ""}`
                : page?.asset
                  ? `${siteBase}${page.asset}${match[2] ?? ""}`
                  : `${rawEvidenceUrl(revision, target)}${match[2] ?? ""}`;
              node.properties![key] = localUrl(targetUrl);
            }
          }
        }
      }
      node.children?.forEach(visit);
    }
    visit(tree);
  };
}

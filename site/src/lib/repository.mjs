// The site links repository files to the public GitHub repository at the
// published revision instead of copying them. Only images are self-hosted,
// because GitHub's raw host serves SVG as text/plain and pages embed them.
export const REPOSITORY = "knewter/esp-sdr-stuff";
export const SELF_HOSTED = /\.(png|svg|jpe?g|gif|webp)$/i;

const encoded = (filePath) => filePath.split("/").map(encodeURIComponent).join("/");

/** Browsable GitHub page for a committed file at one revision. */
export const githubBlobUrl = (revision, filePath) =>
  `https://github.com/${REPOSITORY}/blob/${revision}/${encoded(filePath)}`;

/** CORS-enabled raw bytes for in-browser previews. */
export const githubRawUrl = (revision, filePath) =>
  `https://raw.githubusercontent.com/${REPOSITORY}/${revision}/${encoded(filePath)}`;

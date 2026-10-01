import { defineConfig } from "astro/config";
export default defineConfig({
  site: process.env.SITE_ORIGIN ?? "http://localhost:4321",
  base: process.env.ASTRO_BASE ?? "/",
  trailingSlash: "always",
  build: { format: "directory" },
  devToolbar: { enabled: false },
  compressHTML: true,
});

import { defineConfig } from "astro/config";
export default defineConfig({
  site: process.env.SITE_ORIGIN ?? "http://localhost:4321",
  base: process.env.ASTRO_BASE ?? "/",
  trailingSlash: "always",
  build: { format: "directory" },
  devToolbar: { enabled: false },
  compressHTML: true,
  vite: { build: {
    assetsInlineLimit: 0,
    // The hash still identifies exact JS bytes; long compiler entry names
    // need not be repeated in every static page's script URL.
    rollupOptions: { output: {
      entryFileNames: "_astro/[hash].js",
      chunkFileNames: "_astro/[hash].js",
    } },
  } },
});

import { defineConfig } from "astro/config";
export default defineConfig({
  site: process.env.SITE_ORIGIN ?? "http://localhost:4321",
  base: process.env.ASTRO_BASE ?? "/",
  trailingSlash: "always",
  build: { format: "directory" },
  devToolbar: { enabled: false },
  compressHTML: true,
  vite: { build: { assetsInlineLimit: 0 } },
  integrations: [{
    name: "compact-client-script-names",
    hooks: {
      "astro:build:setup": ({ target, updateConfig }) => {
        if (target !== "client") return;
        // Keep exact content hashes without repeating compiler entry names.
        // Server chunk paths retain Astro's normal build and cleanup rules.
        updateConfig({ build: { rollupOptions: { output: {
          entryFileNames: "_astro/[hash].js",
          chunkFileNames: "_astro/[hash].js",
        } } } });
      },
    },
  }],
});

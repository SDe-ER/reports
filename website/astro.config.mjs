// SDCE Reports documentation site — Astro Starlight, published to GitHub Pages (https://sde-er.github.io/reports/).
import { defineConfig } from "astro/config";
import starlight from "@astrojs/starlight";

export default defineConfig({
  site: "https://sde-er.github.io",
  base: "/reports",
  integrations: [
    starlight({
      title: "SDCE Reports",
      description: "Reports for Frappe / ERPNext — documentation",
      logo: { src: "./src/assets/logo.svg", alt: "SDCE Reports" },
      favicon: "/favicon.svg",
      defaultLocale: "root",
      locales: {
        root: { label: "English", lang: "en" },
        ar: { label: "العربية", lang: "ar", dir: "rtl" },
      },
      social: [
        {
          icon: "github",
          label: "GitHub",
          href: "https://github.com/SDe-ER/reports",
        },
      ],
      customCss: ["./src/styles/custom.css"],
      lastUpdated: false,
      editLink: {
        baseUrl: "https://github.com/SDe-ER/reports/edit/main/website/",
      },
      sidebar: [
        {
          label: "Getting Started",
          translations: { ar: "البداية" },
          items: [{ autogenerate: { directory: "getting-started" } }],
        },
        {
          label: "Reports",
          translations: { ar: "التقارير" },
          items: [{ autogenerate: { directory: "reports" } }],
        },
        {
          label: "Releases",
          translations: { ar: "الإصدارات" },
          items: [{ autogenerate: { directory: "releases" } }],
        },
      ],
    }),
  ],
});

import { defineConfig } from "vitepress";

const GITHUB_URL = "https://github.com/Kibertum/tausik-core";

export default defineConfig({
  title: "TAUSIK",
  description:
    "AI development framework — plan, build, ship with quality control. Sessions, tasks, decisions, and dead-ends tracked locally; quality gates the agent can't skip.",
  cleanUrls: true,
  head: [
    ["meta", { name: "theme-color", content: "#5e6ad2" }],
    ["meta", { property: "og:type", content: "website" }],
    ["meta", { property: "og:site_name", content: "TAUSIK" }],
    ["meta", { property: "og:title", content: "TAUSIK — AI agents that can't fake \"done\"" }],
    [
      "meta",
      {
        property: "og:description",
        content:
          "A discipline layer for AI coding agents. Hard quality gates the agent can't skip, plus ed25519-signed verify receipts — when the agent says green, you get a receipt.",
      },
    ],
    ["meta", { property: "og:url", content: "https://tausik.tech/" }],
    ["meta", { property: "og:image", content: "https://tausik.tech/og.png" }],
    ["meta", { name: "twitter:card", content: "summary_large_image" }],
    ["meta", { name: "twitter:title", content: "TAUSIK — AI agents that can't fake \"done\"" }],
    [
      "meta",
      {
        name: "twitter:description",
        content:
          "Hard quality gates AI coding agents can't skip, plus ed25519-signed verify receipts. Plan before code, ship with proof.",
      },
    ],
    ["meta", { name: "twitter:image", content: "https://tausik.tech/og.png" }],
  ],
  // lastUpdated disabled: relies on `git log` which isn't available in the Docker build stage.
  // Can be enabled later by either copying .git into the build context or running git inside the image.
  lastUpdated: false,
  // Dead links are a build error. After sync to site/{docs,ru/docs}, any cross-language
  // link (../en/X) or source-code link (../../scripts/Y.py) must resolve. Source-code
  // refs go to github.com/Kibertum/tausik-core/blob/main/*; cross-file refs stay within
  // the locale. See site-dead-links-cleanup task for the original 103-link sweep.
  ignoreDeadLinks: false,
  // Working docs that live inside site/ but should not be rendered as public pages.
  srcExclude: ["README.md", "brief.md"],
  locales: {
    root: {
      label: "English",
      lang: "en",
      title: "TAUSIK",
      description:
        "AI development framework — plan, build, ship with quality control.",
      themeConfig: {
        nav: [
          { text: "Quickstart", link: "/docs/quickstart" },
          { text: "Architecture", link: "/docs/architecture" },
          { text: "CLI", link: "/docs/cli" },
          { text: "GitHub", link: GITHUB_URL },
        ],
        sidebar: {
          "/docs/": [
            {
              text: "Getting started",
              items: [
                { text: "Quickstart", link: "/docs/quickstart" },
                { text: "Workflow", link: "/docs/workflow" },
                { text: "Adding a new IDE", link: "/docs/adding-new-ide" },
                { text: "Upgrade guide", link: "/docs/upgrade" },
                { text: "Customization", link: "/docs/customization" },
              ],
            },
            {
              text: "Concepts",
              items: [
                { text: "Architecture", link: "/docs/architecture" },
                { text: "SENAR", link: "/docs/senar" },
                { text: "SENAR compliance matrix", link: "/docs/senar-compliance-matrix" },
                { text: "Session active time", link: "/docs/session-active-time" },
                { text: "Skills", link: "/docs/skills" },
                { text: "Skill ecosystem", link: "/docs/skill-ecosystem" },
                { text: "Skill profiles", link: "/docs/skill-profiles" },
                { text: "Skill adaptation", link: "/docs/skill-adaptation" },
                { text: "Skill bundles", link: "/docs/skill-bundles" },
                { text: "Skill bundles migration", link: "/docs/skill-bundles-migration" },
                { text: "Vendor skills", link: "/docs/vendor-skills" },
                { text: "Stacks", link: "/docs/stacks" },
                { text: "Roles", link: "/docs/roles" },
                { text: "Hooks", link: "/docs/hooks" },
                { text: "MCP", link: "/docs/mcp" },
                { text: "CLAUDE.md guide", link: "/docs/claude-md-guide" },
              ],
            },
            {
              text: "Quality & verification",
              items: [
                { text: "Signed receipts", link: "/docs/receipts" },
                { text: "Verify glossary", link: "/docs/verify-glossary" },
                { text: "Zero-defect", link: "/docs/zero-defect" },
                { text: "Testing principles", link: "/docs/testing-principles" },
                { text: "Doctor", link: "/docs/doctor" },
                { text: "Security", link: "/docs/security" },
                { text: "Security checklist", link: "/docs/security-checklist" },
                { text: "Task archive spec", link: "/docs/task-archive-spec" },
              ],
            },
            {
              text: "Memory & Brain",
              items: [
                { text: "Memory merge guidelines", link: "/docs/memory-merge-guidelines" },
                { text: "Shared brain", link: "/docs/shared-brain" },
                { text: "Brain artifact taxonomy", link: "/docs/brain-artifact-taxonomy" },
                { text: "Brain DB schema", link: "/docs/brain-db-schema" },
                { text: "Brain search ranking", link: "/docs/brain-search-ranking" },
              ],
            },
            {
              text: "Reference",
              items: [
                { text: "CLI", link: "/docs/cli" },
                { text: "Configuration", link: "/docs/configuration" },
                { text: "Environment", link: "/docs/environment" },
                { text: "Permissions", link: "/docs/permissions" },
                { text: "Cost telemetry", link: "/docs/cost-telemetry" },
                { text: "Model providers", link: "/docs/model-providers" },
                { text: "Troubleshooting", link: "/docs/troubleshooting" },
              ],
            },
            {
              text: "Internals",
              collapsed: true,
              items: [
                { text: "Plan review protocol", link: "/docs/plan-review" },
                { text: "Plan stacks tables", link: "/docs/plan-stacks" },
                { text: "Skill spec", link: "/docs/skill-spec" },
                { text: "Skill patterns", link: "/docs/skill-patterns" },
                { text: "Dev doc checks", link: "/docs/dev-doc-checks" },
                { text: "i18n strategy", link: "/docs/i18n-strategy" },
              ],
            },
          ],
        },
        socialLinks: [{ icon: "github", link: GITHUB_URL }],
      },
    },
    ru: {
      label: "Русский",
      lang: "ru",
      link: "/ru/",
      title: "TAUSIK",
      description:
        "Фреймворк AI-разработки — планируй, кодируй, релизь с контролем качества.",
      themeConfig: {
        nav: [
          { text: "Быстрый старт", link: "/ru/docs/quickstart" },
          { text: "Архитектура", link: "/ru/docs/architecture" },
          { text: "CLI", link: "/ru/docs/cli" },
          { text: "GitHub", link: GITHUB_URL },
        ],
        sidebar: {
          "/ru/docs/": [
            {
              text: "Начало",
              items: [
                { text: "Быстрый старт", link: "/ru/docs/quickstart" },
                { text: "Workflow", link: "/ru/docs/workflow" },
                { text: "Добавление нового IDE", link: "/ru/docs/adding-new-ide" },
                { text: "Гайд по апгрейду", link: "/ru/docs/upgrade" },
                { text: "Customization", link: "/ru/docs/customization" },
              ],
            },
            {
              text: "Концепции",
              items: [
                { text: "Архитектура", link: "/ru/docs/architecture" },
                { text: "SENAR", link: "/ru/docs/senar" },
                { text: "SENAR матрица соответствия", link: "/ru/docs/senar-compliance-matrix" },
                { text: "Активное время сессии", link: "/ru/docs/session-active-time" },
                { text: "Skills", link: "/ru/docs/skills" },
                { text: "Skill ecosystem", link: "/ru/docs/skill-ecosystem" },
                { text: "Skill profiles", link: "/ru/docs/skill-profiles" },
                { text: "Skill adaptation", link: "/ru/docs/skill-adaptation" },
                { text: "Skill bundles", link: "/ru/docs/skill-bundles" },
                { text: "Skill bundles migration", link: "/ru/docs/skill-bundles-migration" },
                { text: "Vendor skills", link: "/ru/docs/vendor-skills" },
                { text: "Стеки", link: "/ru/docs/stacks" },
                { text: "Роли", link: "/ru/docs/roles" },
                { text: "Hooks", link: "/ru/docs/hooks" },
                { text: "MCP", link: "/ru/docs/mcp" },
                { text: "CLAUDE.md guide", link: "/ru/docs/claude-md-guide" },
                { text: "Agent contract", link: "/ru/docs/agent-contract" },
              ],
            },
            {
              text: "Качество и верификация",
              items: [
                { text: "Подписанные чеки", link: "/ru/docs/receipts" },
                { text: "Verify-глоссарий", link: "/ru/docs/verify-glossary" },
                { text: "Zero-defect", link: "/ru/docs/zero-defect" },
                { text: "Принципы тестирования", link: "/ru/docs/testing-principles" },
                { text: "Doctor", link: "/ru/docs/doctor" },
                { text: "Безопасность", link: "/ru/docs/security" },
                { text: "Чек-лист безопасности", link: "/ru/docs/security-checklist" },
                { text: "Task archive spec", link: "/ru/docs/task-archive-spec" },
              ],
            },
            {
              text: "Память и Brain",
              items: [
                { text: "Memory merge guidelines", link: "/ru/docs/memory-merge-guidelines" },
                { text: "Shared brain", link: "/ru/docs/shared-brain" },
                { text: "Brain artifact taxonomy", link: "/ru/docs/brain-artifact-taxonomy" },
                { text: "Brain DB schema", link: "/ru/docs/brain-db-schema" },
                { text: "Brain search ranking", link: "/ru/docs/brain-search-ranking" },
              ],
            },
            {
              text: "Справочник",
              items: [
                { text: "CLI", link: "/ru/docs/cli" },
                { text: "Конфигурация", link: "/ru/docs/configuration" },
                { text: "Environment", link: "/ru/docs/environment" },
                { text: "Permissions", link: "/ru/docs/permissions" },
                { text: "Cost telemetry", link: "/ru/docs/cost-telemetry" },
                { text: "Model providers", link: "/ru/docs/model-providers" },
                { text: "Troubleshooting", link: "/ru/docs/troubleshooting" },
              ],
            },
            {
              text: "Internals",
              collapsed: true,
              items: [
                { text: "Plan review protocol", link: "/ru/docs/plan-review" },
                { text: "Plan stacks tables", link: "/ru/docs/plan-stacks" },
                { text: "Skill spec", link: "/ru/docs/skill-spec" },
                { text: "Skill patterns", link: "/ru/docs/skill-patterns" },
                { text: "Dev doc checks", link: "/ru/docs/dev-doc-checks" },
                { text: "i18n strategy", link: "/ru/docs/i18n-strategy" },
              ],
            },
          ],
        },
        socialLinks: [{ icon: "github", link: GITHUB_URL }],
      },
    },
  },
  themeConfig: {
    search: { provider: "local" },
  },
});

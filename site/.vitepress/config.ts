import { defineConfig } from "vitepress";

const GITHUB_URL = "https://github.com/Kibertum/tausik-core";

export default defineConfig({
  title: "TAUSIK",
  description:
    "AI development framework — plan, build, ship with quality control. Sessions, tasks, decisions, and dead-ends tracked locally; quality gates the agent can't skip.",
  cleanUrls: true,
  // lastUpdated disabled: relies on `git log` which isn't available in the Docker build stage.
  // Can be enabled later by either copying .git into the build context or running git inside the image.
  lastUpdated: false,
  // MVP: исходные docs/{en,ru}/*.md содержат относительные ссылки на код (../../scripts/*.py)
  // и cross-language (../en/stacks). После sync в site/docs/ они ломаются. Чистка ссылок —
  // отдельный follow-up; пока не блокируем сборку.
  ignoreDeadLinks: true,
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
              ],
            },
            {
              text: "Concepts",
              items: [
                { text: "Architecture", link: "/docs/architecture" },
                { text: "SENAR", link: "/docs/senar" },
                { text: "Session active time", link: "/docs/session-active-time" },
                { text: "Skills", link: "/docs/skills" },
                { text: "Skill ecosystem", link: "/docs/skill-ecosystem" },
                { text: "Stacks", link: "/docs/stacks" },
                { text: "Roles", link: "/docs/roles" },
                { text: "Hooks", link: "/docs/hooks" },
                { text: "MCP", link: "/docs/mcp" },
              ],
            },
            {
              text: "Quality & verification",
              items: [
                { text: "Verify glossary", link: "/docs/verify-glossary" },
                { text: "Zero-defect", link: "/docs/zero-defect" },
                { text: "Testing principles", link: "/docs/testing-principles" },
                { text: "Doctor", link: "/docs/doctor" },
                { text: "Security", link: "/docs/security" },
                { text: "Security checklist", link: "/docs/security-checklist" },
              ],
            },
            {
              text: "Memory & Brain",
              items: [
                { text: "Memory merge guidelines", link: "/docs/memory-merge-guidelines" },
                { text: "Shared brain", link: "/docs/shared-brain" },
                { text: "Brain artifact taxonomy", link: "/docs/brain-artifact-taxonomy" },
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
              ],
            },
            {
              text: "Концепции",
              items: [
                { text: "Архитектура", link: "/ru/docs/architecture" },
                { text: "SENAR", link: "/ru/docs/senar" },
                { text: "Активное время сессии", link: "/ru/docs/session-active-time" },
                { text: "Skills", link: "/ru/docs/skills" },
                { text: "Skill ecosystem", link: "/ru/docs/skill-ecosystem" },
                { text: "Стеки", link: "/ru/docs/stacks" },
                { text: "Роли", link: "/ru/docs/roles" },
                { text: "Hooks", link: "/ru/docs/hooks" },
                { text: "MCP", link: "/ru/docs/mcp" },
                { text: "Agent contract", link: "/ru/docs/agent-contract" },
              ],
            },
            {
              text: "Качество и верификация",
              items: [
                { text: "Verify-глоссарий", link: "/ru/docs/verify-glossary" },
                { text: "Zero-defect", link: "/ru/docs/zero-defect" },
                { text: "Принципы тестирования", link: "/ru/docs/testing-principles" },
                { text: "Doctor", link: "/ru/docs/doctor" },
                { text: "Безопасность", link: "/ru/docs/security" },
                { text: "Чек-лист безопасности", link: "/ru/docs/security-checklist" },
              ],
            },
            {
              text: "Память и Brain",
              items: [
                { text: "Memory merge guidelines", link: "/ru/docs/memory-merge-guidelines" },
                { text: "Shared brain", link: "/ru/docs/shared-brain" },
                { text: "Brain artifact taxonomy", link: "/ru/docs/brain-artifact-taxonomy" },
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

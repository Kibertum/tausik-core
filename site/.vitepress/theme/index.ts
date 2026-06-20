import type { Theme } from "vitepress";
import DefaultTheme from "vitepress/theme";
import HomeLanding from "./components/HomeLanding.vue";
import "./style.css";

const theme: Theme = {
  ...DefaultTheme,
  enhanceApp({ app }) {
    app.component("HomeLanding", HomeLanding);
  },
};

export default theme;

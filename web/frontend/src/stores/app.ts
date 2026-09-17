import { defineStore } from "pinia";
import { ref } from "vue";

export const useAppStore = defineStore("app", () => {
  const sideMenuCollapsed = ref(false);

  function toggleMenu() {
    sideMenuCollapsed.value = !sideMenuCollapsed.value;
  }

  return {
    sideMenuCollapsed,
    toggleMenu,
  };
});

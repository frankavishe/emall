// Plain (non-"use client") module so the server root layout can inline the script string.

// Namespaced: other localhost projects share this origin's storage.
export const THEME_STORAGE_KEY = "emall.theme";

/** Runs in <head> before first paint: applies the saved theme, else the OS preference, so the
 * page never flashes light before switching. Kept tiny and dependency-free. */
export const themeInitScript = `(function(){try{var t=localStorage.getItem("${THEME_STORAGE_KEY}");if(t!=="light"&&t!=="dark")t=matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light";document.documentElement.setAttribute("data-theme",t)}catch(e){}})()`;

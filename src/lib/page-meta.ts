import { useEffect } from "react";

export const DEFAULT_TITLE = "Flight Price Notifier";
export const DEFAULT_DESCRIPTION = "機票降價通知 — your next journey, within your budget.";

function setMeta(attr: "name" | "property", key: string, content: string) {
  let el = document.head.querySelector<HTMLMetaElement>(`meta[${attr}="${key}"]`);
  if (!el) {
    el = document.createElement("meta");
    el.setAttribute(attr, key);
    document.head.appendChild(el);
  }
  el.setAttribute("content", content);
}

/** Per-page <title> and description/Open Graph tags, set on the client. */
export function usePageMeta({ title, description }: { title: string; description: string }) {
  useEffect(() => {
    document.title = title;
    setMeta("name", "description", description);
    setMeta("property", "og:title", title);
    setMeta("property", "og:description", description);
    setMeta("property", "og:type", "website");
    setMeta("name", "twitter:card", "summary_large_image");
  }, [title, description]);
}

/** Same page titles as before: "<page> | Flight Price Notifier". */
export function pageMeta(title: string, description: string) {
  return { title: `${title} | ${DEFAULT_TITLE}`, description };
}

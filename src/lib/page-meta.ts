export function pageMeta(title: string, description: string) {
  return { meta: [
    { title: `${title} | Flight Price Notifier` },
    { name: 'description', content: description },
    { property: 'og:title', content: `${title} | Flight Price Notifier` },
    { property: 'og:description', content: description },
    { property: 'og:type', content: 'website' },
    { name: 'twitter:card', content: 'summary_large_image' },
  ] };
}
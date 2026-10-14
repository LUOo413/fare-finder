import { Plane, Clock3 } from 'lucide-react';
import { pageMeta, usePageMeta } from '@/lib/page-meta';
import { useAuthenticatedUser } from '@/components/RequireAuth';
const meta = pageMeta('Your app / 我的航線', 'Your private Flight Price Notifier account. Route subscriptions are coming in the next milestone.');
export function AppShell() {
  usePageMeta(meta);
  const user = useAuthenticatedUser();
  return <main className="shell-main site-width fade-in"><span className="eyebrow">YOUR NEXT JOURNEY</span><h1>Hi {user.email}</h1><div className="coming-soon"><span className="feature-icon"><Plane /></span><span className="eyebrow"><Clock3 size={13} /> COMING SOON / 即將上線</span><h2>你的航線追蹤儀表板即將上線 — 下一個里程碑會加上訂閱航線的功能。</h2><p>Your dashboard is coming soon. Route-subscription will be added in the next milestone.</p></div></main>;
}
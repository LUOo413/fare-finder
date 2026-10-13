import { createFileRoute, Link } from '@tanstack/react-router';
import { ArrowRight, Radar, Mail, CircleCheck, Check } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAuthState } from '@/components/AuthProvider';
import { pageMeta } from '@/lib/page-meta';
import flightHero from '@/assets/flight-hero.jpg';

export const Route = createFileRoute('/')({
  head: () => pageMeta('機票降價通知', '設定航線與目標價，機票降價就通知你。 Set a route and a target price — we email you when the fare drops.'),
  component: Index,
});

const features = [
  { icon: Radar, title: '盯緊熱門航線', english: 'Always-on route watching', description: '持續監控台北出發的熱門航線（東京、首爾），自動抓最低票價。' },
  { icon: Mail, title: '達標自動通知', english: 'Target-price email alerts', description: '低於你設定的目標價，就寄 email 提醒你，附上立即訂購連結。' },
  { icon: CircleCheck, title: '隨時取消', english: 'Cancel anytime', description: '月訂閱制，不想用隨時停，沒有綁約。' },
];

function Index() {
  const { user } = useAuthState();
  return <main>
    <section className="hero">
      <img src={flightHero} alt="An airplane wing above the clouds at sunset" width={1920} height={1024} className="hero-image" fetchPriority="high" />
      <div className="site-width hero-content fade-in">
        <span className="eyebrow"><span className="eyebrow-dot" /> TAIPEI DEPARTURES. ENDLESS POSSIBILITIES.</span>
        <h1><span>Flight Price</span><span className="accent-text">Notifier.</span></h1>
        <p className="hero-value">設定航線與目標價，<br />機票降價就通知你</p>
        <p className="hero-english">Set a route and a target price — we email you<br className="hidden sm:block" /> when the fare drops.</p>
        <Button variant="hero" asChild><Link to={user ? '/app' : '/signup'}>{user ? 'My app / 我的航線' : 'Get started / 開始旅程'}<ArrowRight /></Link></Button>
        <p className="hero-note"><Check size={13} /> 你的預算，你的旅程。好價格，我們幫你等。</p>
      </div>
    </section>
    <section className="features site-width">
      <div className="section-heading"><div><span className="eyebrow">LESS SEARCHING. MORE TRAVELING.</span><h2>好票價，不必每天自己找。</h2></div><p>我們盯價格，你期待下一趟旅程。</p></div>
      <div className="feature-grid">{features.map(({ icon: Icon, title, english, description }, index) => <article className="feature-card" key={title}><div className="feature-top"><span className="feature-icon"><Icon aria-hidden="true" /></span><span className="feature-number">0{index + 1}</span></div><h3>{title}</h3><p className="english">{english}</p><p className="description">{description}</p></article>)}</div>
    </section>
  </main>;
}

import { pageMeta, usePageMeta } from "@/lib/page-meta";
import { useAuthenticatedUser } from "@/components/RequireAuth";
import { PlanCards } from "@/components/PlanCards";
const meta = pageMeta(
  "Your app / 我的航線",
  "Pick a route and a target price. We email you when the fare drops below it.",
);
export function AppShell() {
  usePageMeta(meta);
  const user = useAuthenticatedUser();
  return (
    <main className="shell-main site-width fade-in">
      <span className="eyebrow">YOUR NEXT JOURNEY</span>
      <h1>Hi {user.email}</h1>
      <p className="plans-intro">
        選一條航線、設定目標價，票價低於目標價時我們會寄 email 通知你。
        <br />
        <span>Pick a route and a TWD target. We email you when the fare drops below it.</span>
      </p>
      {user.email ? (
        <PlanCards email={user.email} />
      ) : (
        <p className="form-error">你的帳號沒有 email，無法訂閱通知。</p>
      )}
    </main>
  );
}

import { useSearchParams } from "react-router";
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
  // ECPay sends the shopper back to /app?purchase=success|failed (via the flight-ecpay-result redirect).
  const [params] = useSearchParams();
  const purchase = params.get("purchase");
  return (
    <main className="shell-main site-width fade-in">
      <span className="eyebrow">YOUR NEXT JOURNEY</span>
      <h1>Hi {user.email}</h1>
      <p className="plans-intro">
        選一條航線、設定目標價，票價低於目標價時我們會寄 email 通知你。
        <br />
        <span>Pick a route and a TWD target. We email you when the fare drops below it.</span>
        <br />
        月費 NT$300，透過綠界信用卡每月自動扣款，可隨時取消。
      </p>
      {purchase === "success" && (
        <p className="purchase-notice" role="status">
          付款完成！訂閱狀態會在幾秒內更新成「已訂閱（有效）」。
        </p>
      )}
      {purchase === "failed" && (
        <p className="purchase-notice purchase-notice-error" role="status">
          付款沒有成功，沒有扣款。你可以按「完成付款」再試一次。
        </p>
      )}
      {user.email ? (
        <PlanCards email={user.email} refreshAfterPurchase={purchase === "success"} />
      ) : (
        <p className="form-error">你的帳號沒有 email，無法訂閱通知。</p>
      )}
    </main>
  );
}

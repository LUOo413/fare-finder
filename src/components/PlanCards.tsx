import { useEffect, useState, type FormEvent } from "react";
import { BadgeCheck, CircleAlert, CircleSlash, Clock, Plane } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  MONTHLY_PRICE_TWD,
  PLANS,
  cancelSubscription,
  effectiveStatus,
  goToCheckout,
  listSubscriptions,
  subscribe,
  type PlanName,
  type Subscription,
  type SubscriptionStatus,
} from "@/lib/flight-api";

const twd = (n: number) => `NT$${n.toLocaleString("en-US")}`;

const BADGES: Record<SubscriptionStatus, { label: string; icon: typeof BadgeCheck; tone: string }> =
  {
    active: { label: "已訂閱（有效）", icon: BadgeCheck, tone: "" },
    pending_payment: { label: "未完成付款", icon: CircleAlert, tone: "plan-badge-warn" },
    cancelled: { label: "已取消", icon: Clock, tone: "plan-badge-muted" },
    expired: { label: "已結束", icon: CircleSlash, tone: "plan-badge-muted" },
  };

function PlanCard({
  plan,
  email,
  current,
  onSaved,
}: {
  plan: (typeof PLANS)[number];
  email: string;
  current?: Subscription | undefined;
  onSaved: (s: Subscription) => void;
}) {
  const [price, setPrice] = useState(current ? String(current.target_price) : "");
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [confirmCancel, setConfirmCancel] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (current) setPrice(String(current.target_price));
  }, [current]);

  const status = current ? effectiveStatus(current) : undefined;
  // Paid, or cancelled but still inside the paid period: target changes need no payment.
  const paid = status === "active" || status === "cancelled";

  async function save(value: number) {
    setSaving(true);
    setError(null);
    try {
      const result = await subscribe(email, plan.name as PlanName, Math.round(value));
      if (result.kind === "checkout") {
        goToCheckout(result.html);
        return;
      }
      onSaved(result.subscription);
      setEditing(false);
    } catch (err) {
      setError(err instanceof Error ? `儲存失敗：${err.message}` : "儲存失敗，請稍後再試。");
    }
    setSaving(false);
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const value = Number(price);
    if (!Number.isFinite(value) || value <= 0) {
      setError("請輸入大於 0 的目標價（新台幣）。");
      return;
    }
    void save(value);
  }

  async function handleCancel() {
    if (!current) return;
    setSaving(true);
    setError(null);
    try {
      onSaved({ ...current, ...(await cancelSubscription(email, current.route)) });
      setConfirmCancel(false);
    } catch (err) {
      setError(err instanceof Error ? `取消失敗：${err.message}` : "取消失敗，請稍後再試。");
    }
    setSaving(false);
  }

  const showForm = !current || editing || status === "expired";
  const badge = status ? BADGES[status] : undefined;
  return (
    <div className="feature-card plan-card">
      <div className="feature-top">
        <span className="feature-icon">
          <Plane />
        </span>
        {badge && (
          <span className={`plan-badge ${badge.tone}`}>
            <badge.icon size={14} /> {badge.label}
          </span>
        )}
      </div>
      <h3>{plan.title}</h3>
      <p className="english">{plan.english}</p>
      {current && !showForm && (
        <>
          <p className="plan-target">
            目前目標價 <strong>{twd(current.target_price)}</strong>
          </p>
          {status === "active" && (
            <p className="description">
              票價低於這個價格時，我們會寄 email 通知你。月費 {twd(MONTHLY_PRICE_TWD)}
              {current.current_period_end_date && `，本期到 ${current.current_period_end_date}`}。
            </p>
          )}
          {status === "cancelled" && (
            <p className="description">
              已取消，不會再扣款。有效至 {current.current_period_end_date ?? "本期結束"}
              ，在那之前仍會收到降價通知。
            </p>
          )}
          {status === "pending_payment" && (
            <p className="description">
              付款完成後才會開始通知。月費 {twd(MONTHLY_PRICE_TWD)}，綠界信用卡每月自動扣款。
            </p>
          )}
          {error && <p className="form-error">{error}</p>}
          {confirmCancel ? (
            <div className="plan-confirm">
              <p className="description">確定要取消訂閱嗎？已付費的這一期仍然有效。</p>
              <div className="plan-actions">
                <Button variant="destructive" size="sm" disabled={saving} onClick={handleCancel}>
                  {saving ? "取消中…" : "確定取消"}
                </Button>
                <Button variant="ghost" size="sm" onClick={() => setConfirmCancel(false)}>
                  先不要
                </Button>
              </div>
            </div>
          ) : (
            <div className="plan-actions">
              {status === "pending_payment" && (
                <Button size="sm" disabled={saving} onClick={() => save(current.target_price)}>
                  {saving ? "前往付款…" : "完成付款"}
                </Button>
              )}
              <Button variant="secondary" size="sm" onClick={() => setEditing(true)}>
                更新目標價
              </Button>
              {status === "active" && (
                <Button variant="ghost" size="sm" onClick={() => setConfirmCancel(true)}>
                  取消訂閱
                </Button>
              )}
            </div>
          )}
        </>
      )}
      {showForm && (
        <form className="plan-form" onSubmit={handleSubmit}>
          <label htmlFor={`target-${plan.name}`}>目標價（新台幣）</label>
          <Input
            id={`target-${plan.name}`}
            type="number"
            inputMode="numeric"
            min={1}
            step={1}
            placeholder={`例如 ${plan.hint + 1000}`}
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            required
          />
          <p className="description">
            最近最低價約 {twd(plan.hint)}，可以設高一點比較容易收到通知。
            {!paid && ` 月費 ${twd(MONTHLY_PRICE_TWD)}，下一步會前往綠界付款。`}
          </p>
          {error && <p className="form-error">{error}</p>}
          <div className="plan-actions">
            <Button type="submit" disabled={saving}>
              {saving
                ? paid
                  ? "儲存中…"
                  : "前往付款…"
                : paid
                  ? "儲存目標價"
                  : status === "expired"
                    ? "重新訂閱並付款"
                    : "訂閱並付款"}
            </Button>
            {current && editing && (
              <Button
                type="button"
                variant="ghost"
                onClick={() => {
                  setEditing(false);
                  setPrice(String(current.target_price));
                }}
              >
                取消
              </Button>
            )}
          </div>
        </form>
      )}
    </div>
  );
}

export function PlanCards({
  email,
  refreshAfterPurchase = false,
}: {
  email: string;
  refreshAfterPurchase?: boolean;
}) {
  const [subs, setSubs] = useState<Record<string, Subscription>>({});
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const load = () =>
      listSubscriptions(email)
        .then((rows) => {
          if (active) setSubs(Object.fromEntries(rows.map((r) => [r.plan_name, r])));
        })
        .catch(() => {
          if (active) setLoadError("暫時讀不到你的訂閱，請重新整理頁面。");
        })
        .finally(() => {
          if (active) setLoading(false);
        });
    void load();
    // ECPay's server-to-server callback can land a few seconds after the browser returns.
    const timers = refreshAfterPurchase ? [3000, 8000].map((ms) => setTimeout(load, ms)) : [];
    return () => {
      active = false;
      timers.forEach(clearTimeout);
    };
  }, [email, refreshAfterPurchase]);

  return (
    <section className="plans">
      {loadError && <p className="form-error">{loadError}</p>}
      <div className="plan-grid">
        {PLANS.map((plan) => (
          <PlanCard
            key={plan.name}
            plan={plan}
            email={email}
            current={loading ? undefined : subs[plan.name]}
            onSaved={(s) => setSubs((prev) => ({ ...prev, [s.plan_name]: s }))}
          />
        ))}
      </div>
    </section>
  );
}

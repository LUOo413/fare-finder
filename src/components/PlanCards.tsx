import { useEffect, useState, type FormEvent } from "react";
import { BadgeCheck, Plane } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  PLANS,
  listSubscriptions,
  subscribe,
  type PlanName,
  type Subscription,
} from "@/lib/flight-api";

const twd = (n: number) => `NT$${n.toLocaleString("en-US")}`;

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
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (current) setPrice(String(current.target_price));
  }, [current]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const value = Number(price);
    if (!Number.isFinite(value) || value <= 0) {
      setError("請輸入大於 0 的目標價（新台幣）。");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      onSaved(await subscribe(email, plan.name as PlanName, Math.round(value)));
      setEditing(false);
    } catch (err) {
      setError(err instanceof Error ? `儲存失敗：${err.message}` : "儲存失敗，請稍後再試。");
    } finally {
      setSaving(false);
    }
  }

  const showForm = !current || editing;
  return (
    <div className="feature-card plan-card">
      <div className="feature-top">
        <span className="feature-icon">
          <Plane />
        </span>
        {current && (
          <span className="plan-badge">
            <BadgeCheck size={14} /> 已訂閱
          </span>
        )}
      </div>
      <h3>{plan.title}</h3>
      <p className="english">{plan.english}</p>
      {current && !editing && (
        <>
          <p className="plan-target">
            目前目標價 <strong>{twd(current.target_price)}</strong>
          </p>
          <p className="description">票價低於這個價格時，我們會寄 email 通知你。</p>
          <Button variant="secondary" size="sm" onClick={() => setEditing(true)}>
            更新目標價
          </Button>
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
          </p>
          {error && <p className="form-error">{error}</p>}
          <div className="plan-actions">
            <Button type="submit" disabled={saving}>
              {saving ? "儲存中…" : current ? "儲存目標價" : "開始追蹤"}
            </Button>
            {current && (
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

export function PlanCards({ email }: { email: string }) {
  const [subs, setSubs] = useState<Record<string, Subscription>>({});
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
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
    return () => {
      active = false;
    };
  }, [email]);

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

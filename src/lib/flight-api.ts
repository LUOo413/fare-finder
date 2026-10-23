// Public API Gateway endpoint for the AWS side (DynamoDB behind Lambdas). Not a secret:
// the browser holds no AWS credentials and only calls these routes.
const API_URL = (
  import.meta.env.VITE_FLIGHT_API_URL ?? "https://hyyhuk76jc.execute-api.us-east-1.amazonaws.com"
).replace(/\/$/, "");

export type PlanName = "tokyo" | "seoul" | "london";

// Monthly price shown in the UI. The amount actually charged comes from the flight/ecpay secret.
export const MONTHLY_PRICE_TWD = 300;

export type SubscriptionStatus = "pending_payment" | "active" | "cancelled" | "expired";

export type Subscription = {
  email: string;
  route: string;
  plan_name: PlanName;
  target_price: number;
  currency: "TWD";
  updated_at?: string;
  // Missing on rows saved before M2 (never paid): treated like pending_payment.
  subscription_status?: SubscriptionStatus;
  current_period_end?: string;
  current_period_end_date?: string;
};

/** What a card should show: cancelled rows past their paid period count as expired. */
export function effectiveStatus(s: Subscription, now = new Date()): SubscriptionStatus {
  const status = s.subscription_status ?? "pending_payment";
  if (status === "cancelled" && s.current_period_end && new Date(s.current_period_end) < now) {
    return "expired";
  }
  return status;
}

export type SubscribeResult =
  { kind: "checkout"; html: string } | { kind: "saved"; subscription: Subscription };

export const PLANS: {
  name: PlanName;
  title: string;
  english: string;
  route: string;
  hint: number;
}[] = [
  { name: "tokyo", title: "台北 ✈ 東京", english: "Taipei → Tokyo", route: "TPE-TYO", hint: 9325 },
  { name: "seoul", title: "台北 ✈ 首爾", english: "Taipei → Seoul", route: "TPE-SEL", hint: 5989 },
  {
    name: "london",
    title: "台北 ✈ 倫敦",
    english: "Taipei → London",
    route: "TPE-LON",
    hint: 30443,
  },
];

async function readJson(res: Response) {
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body?.error ?? `HTTP ${res.status}`);
  return body;
}

export async function listSubscriptions(email: string): Promise<Subscription[]> {
  const res = await fetch(`${API_URL}/subscriptions?email=${encodeURIComponent(email)}`);
  return (await readJson(res)).subscriptions ?? [];
}

// Paid (or cancelled but still in the paid period) rows are updated in place and come back as JSON.
// Everything else comes back as ECPay's auto-submit checkout form (text/html).
export async function subscribe(
  email: string,
  plan_name: PlanName,
  target_price: number,
): Promise<SubscribeResult> {
  const res = await fetch(`${API_URL}/subscribe`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ email, plan_name, target_price }),
  });
  if (res.ok && (res.headers.get("content-type") ?? "").includes("text/html")) {
    return { kind: "checkout", html: await res.text() };
  }
  return { kind: "saved", subscription: await readJson(res) };
}

/** Replace the page with ECPay's checkout form; its inline script posts the shopper to the cashier. */
export function goToCheckout(html: string) {
  document.open();
  document.write(html);
  document.close();
}

export async function cancelSubscription(
  email: string,
  route: string,
): Promise<
  Pick<Subscription, "subscription_status" | "current_period_end" | "current_period_end_date">
> {
  const res = await fetch(`${API_URL}/cancel`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ email, route }),
  });
  return readJson(res);
}

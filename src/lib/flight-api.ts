// Public API Gateway endpoint for the AWS side (DynamoDB behind Lambdas). Not a secret:
// the browser holds no AWS credentials and only calls these two routes.
const API_URL = (
  import.meta.env.VITE_FLIGHT_API_URL ?? "https://hyyhuk76jc.execute-api.us-east-1.amazonaws.com"
).replace(/\/$/, "");

export type PlanName = "tokyo" | "seoul";

export type Subscription = {
  email: string;
  route: string;
  plan_name: PlanName;
  target_price: number;
  currency: "TWD";
  updated_at?: string;
};

export const PLANS: {
  name: PlanName;
  title: string;
  english: string;
  route: string;
  hint: number;
}[] = [
  { name: "tokyo", title: "台北 ✈ 東京", english: "Taipei → Tokyo", route: "TPE-TYO", hint: 9325 },
  { name: "seoul", title: "台北 ✈ 首爾", english: "Taipei → Seoul", route: "TPE-SEL", hint: 5989 },
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

export async function subscribe(
  email: string,
  plan_name: PlanName,
  target_price: number,
): Promise<Subscription> {
  const res = await fetch(`${API_URL}/subscribe`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ email, plan_name, target_price }),
  });
  return readJson(res);
}

import { AuthForm } from '@/components/AuthForm';
import { pageMeta, usePageMeta } from '@/lib/page-meta';
const meta = pageMeta('Sign up / 註冊', 'Create your Flight Price Notifier account for your next budget-friendly journey.');
export function SignUp() { usePageMeta(meta); return <AuthForm mode="signup" />; }

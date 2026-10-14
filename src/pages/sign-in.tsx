import { AuthForm } from '@/components/AuthForm';
import { pageMeta, usePageMeta } from '@/lib/page-meta';
const meta = pageMeta('Sign in / 登入', 'Sign in to Flight Price Notifier with your email and password.');
export function SignIn() { usePageMeta(meta); return <AuthForm mode="signin" />; }

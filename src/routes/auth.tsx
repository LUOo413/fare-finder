import { createFileRoute } from '@tanstack/react-router';
import { AuthForm } from '@/components/AuthForm';
import { pageMeta } from '@/lib/page-meta';
export const Route = createFileRoute('/auth')({ head: () => pageMeta('Sign in / 登入', 'Sign in to Flight Price Notifier with your email and password.'), component: SignIn });
function SignIn() { return <AuthForm mode="signin" />; }
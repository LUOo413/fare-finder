import { createFileRoute } from '@tanstack/react-router';
import { AuthForm } from '@/components/AuthForm';
import { pageMeta } from '@/lib/page-meta';
export const Route = createFileRoute('/signup')({ head: () => pageMeta('Sign up / 註冊', 'Create your Flight Price Notifier account for your next budget-friendly journey.'), component: SignUp });
function SignUp() { return <AuthForm mode="signup" />; }
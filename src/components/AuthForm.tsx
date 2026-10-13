import { useEffect, useState, type FormEvent } from 'react';
import { Link, useNavigate } from '@tanstack/react-router';
import { ArrowRight, Eye, EyeOff, Plane } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { supabase } from '@/integrations/supabase/client';
import { useAuthState } from './AuthProvider';

export function AuthForm({ mode }: { mode: 'signin' | 'signup' }) {
  const signup = mode === 'signup';
  const navigate = useNavigate();
  const { user } = useAuthState();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [visible, setVisible] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  useEffect(() => { if (user) void navigate({ to: '/app', replace: true }); }, [user, navigate]);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError(''); setMessage('');
    try {
      const result = signup
        ? await supabase.auth.signUp({ email: email.trim(), password, options: { emailRedirectTo: window.location.origin } })
        : await supabase.auth.signInWithPassword({ email: email.trim(), password });
      if (result.error) { setError(result.error.message); return; }
      if (!result.data.session) { setMessage('請查看你的 email 並確認帳號。 Check your email to confirm your account.'); return; }
      const { data, error: verificationError } = await supabase.auth.getUser();
      if (verificationError || !data.user) { setError('Unable to verify your account. Please try again.'); return; }
      await navigate({ to: '/app', replace: true });
    } catch { setError('Unable to connect. Please try again.'); }
    finally { setBusy(false); }
  }
  return <main className="auth-page"><div className="auth-panel fade-in">
    <span className="feature-icon"><Plane /></span>
    <h1>{signup ? 'Create your account' : 'Welcome back'}<span className="block text-lg text-muted-foreground mt-2">{signup ? '註冊帳號' : '登入你的帳號'}</span></h1>
    <p className="auth-subtitle">{signup ? 'Your next journey starts here. 下一趟旅程，從這裡開始。' : 'A little closer to your next getaway. 離下一趟旅程更近一步。'}</p>
    <form className="auth-form" onSubmit={submit}>
      <div className="form-field"><label htmlFor="email">Email / 電子信箱</label><Input id="email" type="email" autoComplete="email" placeholder="you@example.com" required value={email} onChange={e => setEmail(e.target.value)} className="h-12" /></div>
      <div className="form-field"><label htmlFor="password">Password / 密碼</label><div className="password-wrap"><Input id="password" type={visible ? 'text' : 'password'} autoComplete={signup ? 'new-password' : 'current-password'} placeholder={signup ? 'At least 6 characters / 至少 6 個字元' : 'Enter your password'} minLength={signup ? 6 : undefined} required value={password} onChange={e => setPassword(e.target.value)} className="h-12" /><Button type="button" variant="ghost" size="icon" className="password-toggle" aria-label={visible ? 'Hide password' : 'Show password'} onClick={() => setVisible(!visible)}>{visible ? <EyeOff /> : <Eye />}</Button></div></div>
      {error && <p className="form-error" role="alert">{error}</p>}
      {message && <p className="form-success" role="status">{message}</p>}
      <Button variant="hero" type="submit" disabled={busy}>{busy ? 'Please wait…' : signup ? 'Sign Up / 註冊' : 'Sign In / 登入'}<ArrowRight /></Button>
    </form>
    <p className="auth-switch">{signup ? 'Already have an account? ' : 'New here? '}{signup ? <Link to="/auth">Sign in / 登入</Link> : <Link to="/signup">Create an account / 註冊</Link>}</p>
  </div></main>;
}
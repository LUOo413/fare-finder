import { Link, useNavigate } from '@tanstack/react-router';
import { useQueryClient } from '@tanstack/react-query';
import { Plane, ArrowUpRight, LogOut } from 'lucide-react';
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { useAuthState } from './AuthProvider';
import { supabase } from '@/integrations/supabase/client';

export function SiteHeader() {
  const { user, loading } = useAuthState();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function signOut() {
    setBusy(true); setError('');
    await queryClient.cancelQueries();
    queryClient.clear();
    const { error } = await supabase.auth.signOut();
    if (error) { setError('Sign out failed. Please try again.'); setBusy(false); return; }
    await navigate({ to: '/auth', replace: true });
    setBusy(false);
  }
  return <header className="site-header site-width">
    <Link to="/" className="brand"><span className="brand-mark"><Plane aria-hidden="true" /></span><span>Flight Price Notifier<small>機票降價通知</small></span></Link>
    <div className="flex items-center gap-3">
      {error && <span className="form-error" role="alert">{error}</span>}
      {user ? <><Button variant="ghost" size="sm" asChild><Link to="/app">My app</Link></Button><Button variant="header" onClick={signOut} disabled={busy}><LogOut />{busy ? 'Signing out…' : 'Sign Out'}</Button></> : <Button variant="header" asChild><Link to="/auth" aria-busy={loading}>Sign in / 登入<ArrowUpRight /></Link></Button>}
    </div>
  </header>;
}

export function SiteFooter() {
  return <footer className="site-footer site-width"><span>© 2026 Flight Price Notifier</span><span className="footer-note"><Plane size={12} aria-hidden="true" /> More journeys. Less spending.</span></footer>;
}
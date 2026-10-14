import { useEffect, useState } from 'react';
import { Navigate, Outlet, useOutletContext } from 'react-router';
import type { User } from '@supabase/supabase-js';
import { supabase } from '@/integrations/supabase/client';
import { useAuthState } from './AuthProvider';

type AuthenticatedContext = { user: User };

// Client-only guard for signed-in pages (replaces the old `/_authenticated` beforeLoad).
// Verifies the session with Supabase, then redirects to /auth if there is no user.
export function RequireAuth() {
  const { user: liveUser, loading } = useAuthState();
  const [status, setStatus] = useState<'checking' | 'ok' | 'denied'>('checking');
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    let active = true;
    void supabase.auth.getUser().then(({ data, error }) => {
      if (!active) return;
      if (error || !data.user) setStatus('denied');
      else { setUser(data.user); setStatus('ok'); }
    }).catch(() => { if (active) setStatus('denied'); });
    return () => { active = false; };
  }, []);

  // Signed out (in this tab or another) after the check passed.
  const signedOut = status === 'ok' && !loading && !liveUser;
  if (status === 'denied' || signedOut) return <Navigate to="/auth" replace />;
  if (status === 'checking' || !user) return null;
  return <Outlet context={{ user: liveUser ?? user } satisfies AuthenticatedContext} />;
}

export function useAuthenticatedUser() {
  return useOutletContext<AuthenticatedContext>().user;
}

import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import type { User } from '@supabase/supabase-js';
import { supabase } from '@/integrations/supabase/client';

const AuthContext = createContext<{ user: User | null; loading: boolean }>({ user: null, loading: true });

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const queryClient = useQueryClient();
  useEffect(() => {
    let active = true;
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (!active) return;
      setUser(session?.user ?? null);
      setLoading(false);
      if (event === 'SIGNED_IN' || event === 'SIGNED_OUT' || event === 'USER_UPDATED') {
        if (event !== 'SIGNED_OUT') void queryClient.invalidateQueries();
      }
    });
    void supabase.auth.getUser().then(({ data }) => {
      if (active) { setUser(data.user); setLoading(false); }
    }).catch(() => { if (active) setLoading(false); });
    return () => { active = false; subscription.unsubscribe(); };
  }, [queryClient]);
  return <AuthContext.Provider value={{ user, loading }}>{children}</AuthContext.Provider>;
}

export function useAuthState() { return useContext(AuthContext); }
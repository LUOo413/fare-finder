import { render, screen, waitFor } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

// Stand-in for the Supabase browser client so pages render without a network.
const auth = vi.hoisted(() => ({ user: null as null | { id: string; email: string } }));
vi.mock("@/integrations/supabase/client", () => ({
  supabase: {
    auth: {
      getUser: async () => ({ data: { user: auth.user }, error: null }),
      onAuthStateChange: (cb: (event: string, session: unknown) => void) => {
        queueMicrotask(() => cb("INITIAL_SESSION", auth.user ? { user: auth.user } : null));
        return { data: { subscription: { unsubscribe: () => {} } } };
      },
      signOut: async () => ({ error: null }),
    },
  },
}));

const { routes } = await import("@/router");

function renderAt(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  render(<RouterProvider router={router} />);
  return router;
}

describe("App pages render client-side", () => {
  beforeEach(() => {
    auth.user = null;
  });

  it("renders the landing page at /", async () => {
    renderAt("/");
    expect(await screen.findByText("設定航線與目標價，", { exact: false })).toBeInTheDocument();
    expect(screen.getByText("© 2026 Flight Price Notifier")).toBeInTheDocument();
    await waitFor(() => expect(document.title).toBe("機票降價通知 | Flight Price Notifier"));
  });

  it("renders sign in at /auth", async () => {
    renderAt("/auth");
    expect(await screen.findByRole("button", { name: /Sign In \/ 登入/ })).toBeInTheDocument();
  });

  it("renders sign up at /signup", async () => {
    renderAt("/signup");
    expect(await screen.findByRole("button", { name: /Sign Up \/ 註冊/ })).toBeInTheDocument();
  });

  it("redirects /app to /auth when signed out", async () => {
    const router = renderAt("/app");
    await waitFor(() => expect(router.state.location.pathname).toBe("/auth"));
  });

  it("shows the app shell at /app when signed in", async () => {
    auth.user = { id: "u1", email: "traveler@example.com" };
    const router = renderAt("/app");
    expect(await screen.findByText("Hi traveler@example.com")).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/app");
  });

  it("shows the 404 page for unknown paths", async () => {
    renderAt("/does-not-exist");
    expect(await screen.findByText("Page not found")).toBeInTheDocument();
  });
});

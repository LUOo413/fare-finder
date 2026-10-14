import { createBrowserRouter, type RouteObject } from "react-router";
import { RootLayout, RootErrorBoundary, NotFound } from "./pages/root-layout";
import { RequireAuth } from "./components/RequireAuth";
import { Home } from "./pages/home";
import { SignIn } from "./pages/sign-in";
import { SignUp } from "./pages/sign-up";
import { AppShell } from "./pages/app";

// Client-side routes. Paths are unchanged from the previous TanStack Start app:
// /, /auth (sign in), /signup (sign up) and /app (requires a signed-in user).
export const routes: RouteObject[] = [
  {
    id: "root",
    element: <RootLayout />,
    errorElement: <RootErrorBoundary />,
    children: [
      { id: "home", index: true, element: <Home /> },
      { id: "sign-in", path: "auth", element: <SignIn /> },
      { id: "sign-up", path: "signup", element: <SignUp /> },
      {
        id: "authenticated",
        element: <RequireAuth />,
        children: [{ id: "app", path: "app", element: <AppShell /> }],
      },
      { id: "not-found", path: "*", element: <NotFound /> },
    ],
  },
];

export const router = createBrowserRouter(routes);

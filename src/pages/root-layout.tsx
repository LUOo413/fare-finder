import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, Outlet, ScrollRestoration, useRouteError } from "react-router";
import { reportLovableError } from "@/lib/lovable-error-reporting";
import { AuthProvider } from "@/components/AuthProvider";
import { SiteHeader, SiteFooter } from "@/components/SiteHeader";
import { usePageMeta, DEFAULT_TITLE, DEFAULT_DESCRIPTION } from "@/lib/page-meta";

export function NotFound() {
  usePageMeta({ title: DEFAULT_TITLE, description: DEFAULT_DESCRIPTION });
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-md text-center">
        <h1 className="text-7xl font-bold text-foreground">404</h1>
        <h2 className="mt-4 text-xl font-semibold text-foreground">Page not found</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          The page you're looking for doesn't exist or has been moved.
        </p>
        <div className="mt-6">
          <Link
            to="/"
            className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          >
            Go home
          </Link>
        </div>
      </div>
    </div>
  );
}

export function RootErrorBoundary() {
  const error = useRouteError();
  console.error(error);
  useEffect(() => {
    reportLovableError(error, { boundary: "root_error_boundary" });
  }, [error]);
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-md text-center">
        <h1 className="text-xl font-semibold tracking-tight text-foreground">
          This page didn't load
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Something went wrong on our end. You can try refreshing or head back home.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-2">
          <button
            onClick={() => window.location.reload()}
            className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          >
            Try again
          </button>
          <a
            href="/"
            className="inline-flex items-center justify-center rounded-md border border-input bg-background px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-accent"
          >
            Go home
          </a>
        </div>
      </div>
    </div>
  );
}

export function RootLayout() {
  const [queryClient] = useState(() => new QueryClient());
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <SiteHeader />
        <Outlet />
        <SiteFooter />
      </AuthProvider>
      <ScrollRestoration />
    </QueryClientProvider>
  );
}

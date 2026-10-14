<!-- LOVABLE:BEGIN -->
> [!IMPORTANT]
> This project is connected to [Lovable](https://lovable.dev). Avoid rewriting
> published git history — force pushing, or rebasing/amending/squashing commits
> that are already pushed — as it rewrites history on Lovable's side and the
> user will likely lose their project history.
>
> Commits you push to the connected branch sync back to Lovable and show up in
> the editor, so keep the branch in a working state.
<!-- LOVABLE:END -->

## Architecture
- Authentication is the only Cloud usage; never create custom tables, RPCs or application-data queries, because later flight data belongs in AWS DynamoDB behind Lambdas.
- The app is a static Vite + React Router SPA (no SSR). Routes are defined in src/router.tsx: public pages at /, /auth and /signup; /app sits behind the RequireAuth guard. vercel.json rewrites every path to index.html so deep links resolve client-side.
- AuthProvider owns the single auth state listener and identity invalidation; use it for session-aware navigation to avoid competing subscriptions.
- Reusable feature component filenames use PascalCase; route and generated UI filenames follow their framework conventions for compatibility.
- Use the generated browser auth client and semantic global CSS tokens, so account-provider changes and theme values stay centralized.

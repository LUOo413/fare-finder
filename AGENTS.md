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
- Public pages live at /, /auth and /signup; the /app shell lives under the client-only authenticated layout, because browser sessions are unavailable during SSR.
- AuthProvider owns the single auth state listener and identity invalidation; use it for session-aware navigation to avoid competing subscriptions.
- Reusable feature component filenames use PascalCase; route and generated UI filenames follow their framework conventions for compatibility.
- Use the generated browser auth client and semantic global CSS tokens, so account-provider changes and theme values stay centralized.

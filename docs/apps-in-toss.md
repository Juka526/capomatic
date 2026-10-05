# Apps in Toss delivery

Understood as: prepare a guest-only Toss build on branch `v1/apps-in-toss` in worktree `/private/tmp/capomatic-ait`, preserving the ordinary web build; validate locally before any console creation, bundle upload, review submission, or HF Space changes.

## Build

Use Node.js 24 or newer. From `frontend/`:

```sh
npm ci
npm run check
AIT_APP_NAME=capomatic-local npm run check:toss
```

`check:toss` runs `npm run check` with the Toss target, audits the static export, and packages it with `ait build`. For subsequent packaging, use `AIT_APP_NAME='<existing-console-app-name>' npm run build:toss`. Next exports to `out/`; `apps-in-toss.config.ts` uses that folder as `webBundleDir`. `.ait` files and `out/` are ignored by git. These commands do not upload or release anything.

The console app name is unconfirmed; obtain it from the existing app’s information page in the Apps in Toss console. `capomatic-local` is only a local verification name, and CI uses `capomatic-ci`. Neither represents a registered app. Use the existing app name before producing an upload candidate; do not create a second app. `AIT_APP_NAME` must be supplied in the shell environment; the CLI config does not load Next's `.env.local`.

`npm run dev:toss` starts the Next webpack development server with official AIT Devtools. Its navigation and file APIs are mocks. Production bundles exclude the devtools.

## Runtime

The Toss build disables Auth0 even when Auth0 environment variables exist, hides login and job history, blocks direct `/history/` access, and does not save job-history entries. It does not need a user identifier, so it does not call `getAnonymousKey`. Language and guide preferences remain local to the device. Vercel Analytics is disabled; existing optional Sentry error reporting remains.

The SDK provides the light navigation bar. In-page back handling closes the guide or result before closing the mini app from its initial screen. Legal and missing-page back actions return to `/`. The ordinary web navigation is replaced by a guide/language/upload toolbar. Legal pages stay within the mini app and point support requests to the SDK More menu. The customer-service destination is still unconfirmed. Configure that menu's customer-service destination in the existing console app before review.

Result images use SDK `File.saveBase64`. The existing browser file picker supplies image uploads. Verify both flows on iOS and Android; development mocks and static builds do not validate native permissions or actual device saving.

## Backend and approval boundary

The default Toss API is `https://juka526-capomatic.hf.space`; override it with HTTPS-only `NEXT_PUBLIC_API_URL` at build time. After the user explicitly approves an HF CORS change, use the confirmed existing console app name to append these entries to the HF Space's existing `CORS_ORIGINS`, preserving its current entries:

```text
https://<appName>.apps.tossmini.com
https://<appName>.private-apps.tossmini.com
```

Do not change the HF Space, create a console app, upload a bundle, or submit review without the user's explicit confirmation. Code changes go through a branch and PR; never push or merge directly to `main`.

To unlock device QA, first confirm the existing app name and ask the user to approve a specific bundle upload and the two CORS additions.

Before review, verify home/deep links, native and Android back buttons, light mode, guide controls, image selection, OCR, transposition, file saving, support, and privacy/terms in the actual Toss app. Without approved CORS changes, OCR calls from Toss origins may fail. No mTLS setup is needed for this guest-only client calling its own backend; it does not call Toss server APIs.

## Verification status

On 2026-10-06, the ordinary web and Toss `npm run check` flows passed 60 tests and TypeScript/build checks. The Toss check also passed the export audit and produced a local `capomatic-local.ait` bundle. Fake Auth0 environment variables were set during the Toss check to confirm they do not enable external login. The existing npm security gate passed with its existing Tailwind/braces exception.

HTTP checks against the Toss development server returned 200 for `/` and `/privacy/`, and 404 for `/history/`. Browser interaction could not be tested because the browser automation connection failed. Native back behavior, photo selection, actual image saving, OCR from Toss origins, and customer support remain device/console checks. No HF configuration, console app, uploaded bundle, or review submission was changed.

## References

- [SDK 3.x configuration and packaging](https://developers-apps-in-toss.toss.im/documentation/integration/sdk-3.x)
- [Non-game release checklist](https://developers-apps-in-toss.toss.im/checklist/app-nongame)
- [Server API and current CORS origins](https://developers-apps-in-toss.toss.im/documentation/integration/server-api)
- [Navigation](https://developers-apps-in-toss.toss.im/documentation/common/navigationbar)
- [Back events](https://developers-apps-in-toss.toss.im/documentation/common/screen/event)

# Apps in Toss delivery

Understood as: maintain the guest-only Toss build on `v1/apps-in-toss`. The 2026-10-12 update removes guide videos and replaces them with the same three-step text/icon cards as the web guide; the user requested the Toss update and release.

## Build

Use Node.js 24 or newer. From `frontend/`:

```sh
npm ci
npm run check
npm run check:toss
```

`check:toss` runs `npm run check` with the Toss target, audits the static export, and packages it with `ait build`. For subsequent packaging, use `npm run build:toss`. Next exports to `out/`; `apps-in-toss.config.ts` uses that folder as `webBundleDir`. `.ait` files and `out/` are ignored by git. These commands do not upload or release anything.

The user confirmed the existing console app name as `capomatic`. Its canonical value is in `frontend/apps-in-toss.config.ts`; local and CI builds both produce `frontend/capomatic.ait`. Do not create a second app.

`npm run dev:toss` starts the Next webpack development server with official AIT Devtools. Its navigation and file APIs are mocks. Production bundles exclude the devtools.

## Runtime

The Toss build disables Auth0 even when Auth0 environment variables exist, hides login and job history, blocks direct `/history/` access, and does not save job-history entries. It does not need a user identifier, so it does not call `getAnonymousKey`. Language and guide preferences remain local to the device. Vercel Analytics is disabled; existing optional Sentry error reporting remains.

The Toss build omits manual chord correction, addition, deletion, position picking, and re-rendering with edits. Transposition, capo controls, and image saving remain available; the ordinary web build keeps its chord editor.

The SDK provides the light navigation bar. In-page back handling closes the guide or result before closing the mini app from its initial screen. Legal and missing-page back actions return to `/`. The ordinary web navigation is replaced by a guide/language/upload toolbar. Legal pages stay within the mini app and point support requests to the SDK More menu. The customer-service destination is still unconfirmed. Configure that menu's customer-service destination in the existing console app before review.

Result images use SDK `File.saveBase64`. The existing browser file picker supplies image uploads. Verify both flows on iOS and Android; development mocks and static builds do not validate native permissions or actual device saving.

## Backend and approval boundary

The default Toss API is `https://juka526-capomatic.hf.space`; override it with HTTPS-only `NEXT_PUBLIC_API_URL` at build time.

The user approved the CORS additions and uploading the existing `frontend/capomatic.ait` test bundle to `capomatic`. The HF Space now has these `CORS_ORIGINS`, preserving the existing web origin:

```text
https://capomatic.vercel.app
https://capomatic.apps.tossmini.com
https://capomatic.private-apps.tossmini.com
```

All three origins returned HTTP 200 with matching `Access-Control-Allow-Origin` headers for POST preflight to `/detect`; `/health` returned HTTP 200 and `status: ok` after the update.

## Current guide update (2026-10-12)

The Toss bundle embeds a static frontend and does not inherit Vercel deployments. The merged web guide fix from [PR #50](https://github.com/Juka526/capomatic/pull/50), commit `eec91d0`, is cherry-picked for Toss as `7e38bd6`. The guide now uses three text/icon cards: upload, capo selection, download, in Korean and English. Videos, posters, chapter data and their playback/recording code are removed. The guest-only Toss restrictions remain.

The user requested immediate replacement in the live Toss app. The new artifact was uploaded to the existing `capomatic` app with the saved default CLI profile. An independent read of the official CLI's deployment-status endpoint returned `SUCCESS` and `reviewStatus: CREATED`: **uploaded, not reviewed or released**. The saved deployment status must not be reported as live completion.

- Artifact: `frontend/capomatic.ait`, 295,715 bytes.
- SHA-256: `3659dc136befd6330592254b68a538dea16677196a183a1b8395c60e7d398450`.
- Console version: **`20261012-4`**; `isTested: false`, `deployed: false`.
- Deployment ID: `01a13079-8998-7e06-bf01-25bd13d3f883`.
- Test scheme:

```text
intoss-private://capomatic?_deploymentId=01a13079-8998-7e06-bf01-25bd13d3f883&host=appsInTossHost
```

Validation: `npm run check:toss` passed 39 tests, TypeScript, static export audit and `.ait` packaging with SDK/CLI 3.7.0. The generated archive contains 26 entries, zero `sources/guide/` files and zero MP4/WebM files. Compiled output contains `guide-icon` and all six Korean/English step titles, and no old `guide-media` or `guide-chapters` UI. No dependency manifest/lockfile changes were made.

The 2026-10-07 deployment `01a11516-9fa1-7cc7-acc6-828a88264cbb` now reports `APPROVED` and `deployed: true`, version **`20261007-3`**, last deployed 2026-10-08; it is the current older guide-video release. Do not choose that version when releasing the guide-card fix. The earlier `01a11510-ac6f-7182-a995-12670acbdfac` reports `CREATED`.

The [official update procedure](https://developers-apps-in-toss.toss.im/guide/operation/deploy.md) requires upload, review request, approval, then release. This session has CLI upload credentials, but no connected Toss Console MCP or usable browser surface, so console review submission/release and actual Toss-device interaction remain unfinished. User authorization for the guide update is already present; the remaining obstacle is console access and the platform's review process. No new console app is needed. Code changes continue through the existing Toss branch/PR, not direct main pushes.

Before review, verify home/deep links, native and Android back buttons, light mode, text-guide step navigation, image selection, OCR, transposition, file saving, support, and privacy/terms in the actual Toss app. No mTLS setup is needed for this guest-only client calling its own backend; it does not call Toss server APIs.

## Verification status

The 2026-10-07 editor-removal candidate passed `npm run check` and `npm run check:toss` (60 tests, TypeScript, builds, export audit, and packaging). The compiled web page still contains the chord editor; the compiled Toss page does not.

On 2026-10-06, the ordinary web and Toss `npm run check` flows passed 60 tests and TypeScript/build checks. The Toss check also passed the export audit and produced the upload candidate `frontend/capomatic.ait` using the confirmed app name. Fake Auth0 environment variables were also used in the earlier Toss check to confirm they do not enable external login. The existing npm security gate passed with its existing Tailwind/braces exception.

HTTP checks against the Toss development server returned 200 for `/` and `/privacy/`, and 404 for `/history/`. Browser interaction could not be tested because the browser automation connection failed. Native back behavior, photo selection, actual image saving, OCR from Toss origins, and customer support remain device/console checks. The historical HF CORS update is complete. The current guide-card upload and release status are recorded above; no console app was created and no review was submitted in this session.

## References

- [SDK 3.x configuration and packaging](https://developers-apps-in-toss.toss.im/documentation/integration/sdk-3.x)
- [Non-game release checklist](https://developers-apps-in-toss.toss.im/checklist/app-nongame)
- [Server API and current CORS origins](https://developers-apps-in-toss.toss.im/documentation/integration/server-api)
- [Navigation](https://developers-apps-in-toss.toss.im/documentation/common/navigationbar)
- [Back events](https://developers-apps-in-toss.toss.im/documentation/common/screen/event)

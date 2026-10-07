# Apps in Toss delivery

Understood as: prepare a guest-only Toss build on branch `v1/apps-in-toss` in worktree `/private/tmp/capomatic-ait`, preserving the ordinary web build; validate locally before any console creation, bundle upload, review submission, or HF Space changes.

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

The latest approved test bundle, which removes manual chord editing from Toss, was uploaded to the existing `capomatic` app on 2026-10-07. The CLI completed successfully, and a separate server status read returned `SUCCESS` with `reviewStatus: CREATED`. Review has not been submitted.

Current test scheme:

```text
intoss-private://capomatic?_deploymentId=01a11510-ac6f-7182-a995-12670acbdfac&host=appsInTossHost
```

The uploaded artifact is `frontend/capomatic.ait`, SHA-256 `133f744cce48daea67675e42de8ad8d7b8ecf01e0537cf57b310e4cd9c735f3b`, deployment ID `01a11510-ac6f-7182-a995-12670acbdfac`. Use this deployment's console test QR; the earlier deployment (`01a10e2f-8980-7996-a49b-4c07cd68d320`) still contains the editor. Its bundle is archived locally as `frontend/capomatic-01a10e2f-8980-7996-a49b-4c07cd68d320.ait`.

The next step is device testing. Review submission and creating another app are not authorized. Code changes go through the existing branch and PR; never push or merge directly to `main`.

Before review, verify home/deep links, native and Android back buttons, light mode, guide controls, image selection, OCR, transposition, file saving, support, and privacy/terms in the actual Toss app. No mTLS setup is needed for this guest-only client calling its own backend; it does not call Toss server APIs.

## Verification status

The 2026-10-07 editor-removal candidate passed `npm run check` and `npm run check:toss` (60 tests, TypeScript, builds, export audit, and packaging). The compiled web page still contains the chord editor; the compiled Toss page does not.

On 2026-10-06, the ordinary web and Toss `npm run check` flows passed 60 tests and TypeScript/build checks. The Toss check also passed the export audit and produced the upload candidate `frontend/capomatic.ait` using the confirmed app name. Fake Auth0 environment variables were also used in the earlier Toss check to confirm they do not enable external login. The existing npm security gate passed with its existing Tailwind/braces exception.

HTTP checks against the Toss development server returned 200 for `/` and `/privacy/`, and 404 for `/history/`. Browser interaction could not be tested because the browser automation connection failed. Native back behavior, photo selection, actual image saving, OCR from Toss origins, and customer support remain device/console checks. The approved HF CORS update and test bundle upload are complete. No console app was created and no review was submitted.

## References

- [SDK 3.x configuration and packaging](https://developers-apps-in-toss.toss.im/documentation/integration/sdk-3.x)
- [Non-game release checklist](https://developers-apps-in-toss.toss.im/checklist/app-nongame)
- [Server API and current CORS origins](https://developers-apps-in-toss.toss.im/documentation/integration/server-api)
- [Navigation](https://developers-apps-in-toss.toss.im/documentation/common/navigationbar)
- [Back events](https://developers-apps-in-toss.toss.im/documentation/common/screen/event)

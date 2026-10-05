import { defineConfig } from '@apps-in-toss/web-framework/config';

// Use the existing console app identifier, never silently create a second app.
const appName = process.env.AIT_APP_NAME;
if (!appName) throw new Error('Set AIT_APP_NAME to the existing Apps in Toss console app name.');

export default defineConfig({
  appName,
  brand: { primaryColor: '#a34200' },
  permissions: [],
  navigationBar: {
    withBackButton: true,
    withHomeButton: false,
    withTitle: true,
    theme: 'light',
    transparentBackground: false,
  },
  webView: {
    allowsInlineMediaPlayback: true,
    pullToRefreshEnabled: false,
    bounces: false,
    overScrollMode: 'never',
  },
  webBundleDir: 'out',
});

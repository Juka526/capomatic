import { defineConfig } from '@apps-in-toss/web-framework/config';

export default defineConfig({
  appName: 'capomatic',
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

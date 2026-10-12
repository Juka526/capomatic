const { withSentryConfig } = require('@sentry/nextjs/config');

const isToss = process.env.NEXT_PUBLIC_APP_TARGET === 'toss';
const tossApiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://juka526-capomatic.hf.space';
if (isToss && new URL(tossApiUrl).protocol !== 'https:') {
  throw new Error('The Toss build requires an HTTPS NEXT_PUBLIC_API_URL.');
}

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  agentRules: false,
  ...(isToss ? {
    output: 'export',
    trailingSlash: true,
    env: { NEXT_PUBLIC_API_URL: tossApiUrl },
  } : {}),
  webpack(config, { dev, isServer }) {
    if (isToss && dev && !isServer) {
      const { webpack } = require('@apps-in-toss/devtools/unplugin');
      config.plugins.unshift(webpack({ entryPattern: /\/pages\/_app\.tsx$/ }));
    }
    if (isToss) config.output.globalObject = 'globalThis';
    return config;
  },
};

// Static exports cannot carry Next server headers; keep these on the web host.
if (!isToss) {
  nextConfig.headers = async () => [{
    source: '/(.*)',
    headers: [
      { key: 'X-Content-Type-Options', value: 'nosniff' },
      { key: 'X-Frame-Options', value: 'DENY' },
      { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
      { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
    ],
  }];
}

module.exports = withSentryConfig(nextConfig, {
  silent: true,
  telemetry: false,
  sourcemaps: { disable: true },
});

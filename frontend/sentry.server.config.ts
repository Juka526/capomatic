import * as Sentry from '@sentry/nextjs';

import { sentryOptions } from './lib/sentry-options.mjs';

Sentry.init(sentryOptions({
  dsn: process.env.SENTRY_DSN || process.env.NEXT_PUBLIC_SENTRY_DSN,
  release: process.env.SENTRY_RELEASE || process.env.VERCEL_GIT_COMMIT_SHA,
  environment: process.env.SENTRY_ENVIRONMENT || process.env.VERCEL_ENV,
}));

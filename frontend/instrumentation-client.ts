import * as Sentry from '@sentry/nextjs';

import { sentryOptions } from './lib/sentry-options.mjs';

Sentry.init(sentryOptions({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  release: process.env.NEXT_PUBLIC_SENTRY_RELEASE || process.env.NEXT_PUBLIC_VERCEL_GIT_COMMIT_SHA,
  environment: process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT || process.env.NEXT_PUBLIC_VERCEL_ENV,
}));

export const onRouterTransitionStart = Sentry.captureRouterTransitionStart;

// Shared by the client, server, and edge Sentry configs so the privacy
// settings cannot drift between runtimes. Callers pass literal
// process.env values because Next.js only inlines static references.
export function sentryOptions({ dsn, release, environment }) {
  return {
    dsn,
    enabled: Boolean(dsn),
    release: release || undefined,
    environment: environment || 'development',
    tracesSampleRate: 0.05,
    sendDefaultPii: false,
    replaysSessionSampleRate: 0,
    replaysOnErrorSampleRate: 0,
  };
}

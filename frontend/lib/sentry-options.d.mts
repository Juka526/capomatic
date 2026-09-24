export function sentryOptions(env: {
  dsn?: string;
  release?: string;
  environment?: string;
}): {
  dsn?: string;
  enabled: boolean;
  release?: string;
  environment: string;
  tracesSampleRate: number;
  sendDefaultPii: false;
  replaysSessionSampleRate: 0;
  replaysOnErrorSampleRate: 0;
};

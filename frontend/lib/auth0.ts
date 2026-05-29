/**
 * Auth0 client configuration for Capomatic.
 * Handles authentication, token management, and user info.
 * When Auth0 env vars are absent (local dev), all auth functions are no-ops.
 */
import { Auth0Client } from '@auth0/auth0-spa-js';

const _domain = process.env.NEXT_PUBLIC_AUTH0_DOMAIN;
const _clientId = process.env.NEXT_PUBLIC_AUTH0_CLIENT_ID;

// Initialize Auth0 client only when env vars are present.
export const auth0Client: Auth0Client | null = (_domain && _clientId)
  ? new Auth0Client({
      domain: _domain,
      clientId: _clientId,
      authorizationParams: {
        redirect_uri: typeof window !== 'undefined' ? window.location.origin : '',
        audience: 'https://capomatic-api',
        scope: 'openid profile email',
      },
      cacheLocation: 'localstorage',
      useRefreshTokens: true,
    })
  : null;

/**
 * Get access token for API calls.
 * Returns null if user is not authenticated.
 */
export async function getAccessToken(): Promise<string | null> {
  if (!auth0Client) return null;
  try {
    return await auth0Client.getTokenSilently();
  } catch {
    return null;
  }
}

export async function isAuthenticated(): Promise<boolean> {
  if (!auth0Client) return false;
  try {
    return await auth0Client.isAuthenticated();
  } catch {
    return false;
  }
}

export async function getUser() {
  if (!auth0Client) return null;
  try {
    return await auth0Client.getUser();
  } catch {
    return null;
  }
}

export async function login() {
  if (!auth0Client) return;
  await auth0Client.loginWithRedirect({
    authorizationParams: { redirect_uri: window.location.origin },
  });
}

export async function logout() {
  if (!auth0Client) return;
  await auth0Client.logout({
    logoutParams: { returnTo: window.location.origin },
  });
}

export async function handleRedirectCallback() {
  if (!auth0Client) return;
  try {
    await auth0Client.handleRedirectCallback();
  } catch {
    // ignore stale callbacks
  }
}

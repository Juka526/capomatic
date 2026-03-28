/**
 * Auth0 client configuration for TransChord.
 * Handles authentication, token management, and user info.
 */
import { Auth0Client } from '@auth0/auth0-spa-js';

// Validate required environment variables
if (!process.env.NEXT_PUBLIC_AUTH0_DOMAIN) {
  throw new Error('NEXT_PUBLIC_AUTH0_DOMAIN environment variable is required');
}

if (!process.env.NEXT_PUBLIC_AUTH0_CLIENT_ID) {
  throw new Error('NEXT_PUBLIC_AUTH0_CLIENT_ID environment variable is required');
}

// Initialize Auth0 client
export const auth0Client = new Auth0Client({
  domain: process.env.NEXT_PUBLIC_AUTH0_DOMAIN,
  clientId: process.env.NEXT_PUBLIC_AUTH0_CLIENT_ID,
  authorizationParams: {
    redirect_uri: typeof window !== 'undefined' ? window.location.origin : '',
    audience: 'https://transchord-api',
    scope: 'openid profile email',
  },
  cacheLocation: 'localstorage',
  useRefreshTokens: true,
});

/**
 * Get access token for API calls.
 * Returns null if user is not authenticated.
 */
export async function getAccessToken(): Promise<string | null> {
  try {
    const token = await auth0Client.getTokenSilently();
    return token;
  } catch (error) {
    console.error('Failed to get access token:', error);
    return null;
  }
}

/**
 * Check if user is currently authenticated.
 */
export async function isAuthenticated(): Promise<boolean> {
  try {
    return await auth0Client.isAuthenticated();
  } catch (error) {
    console.error('Authentication check failed:', error);
    return false;
  }
}

/**
 * Get current user information.
 * Returns null if not authenticated.
 */
export async function getUser() {
  try {
    return await auth0Client.getUser();
  } catch (error) {
    console.error('Failed to get user info:', error);
    return null;
  }
}

/**
 * Initiate login flow with redirect to Auth0.
 */
export async function login() {
  await auth0Client.loginWithRedirect({
    authorizationParams: {
      redirect_uri: window.location.origin,
    },
  });
}

/**
 * Logout and redirect to home page.
 */
export async function logout() {
  await auth0Client.logout({
    logoutParams: {
      returnTo: window.location.origin,
    },
  });
}

/**
 * Handle redirect callback after login.
 * Should be called on page load to process Auth0 redirect.
 */
export async function handleRedirectCallback() {
  try {
    await auth0Client.handleRedirectCallback();
  } catch (error) {
    console.error('Redirect callback failed:', error);
  }
}

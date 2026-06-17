import crypto from "crypto";

function toBase64Url(input: Buffer): string {
  return input
    .toString("base64")
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/g, "");
}

export function createCodeVerifier(): string {
  return toBase64Url(crypto.randomBytes(48));
}

export function createCodeChallenge(verifier: string): string {
  const digest = crypto.createHash("sha256").update(verifier).digest();
  return toBase64Url(digest);
}

export function createStateToken(): string {
  return toBase64Url(crypto.randomBytes(24));
}

export function requiredEnv(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing environment variable: ${name}`);
  }
  return value;
}

export type AuthConfig = {
  authorizationEndpoint: string;
  tokenEndpoint: string;
  logoutEndpoint: string;
  logoutRedirectParam: string;
  clientId: string;
  redirectUri: string;
  logoutRedirectUri: string;
  scopes: string;
};

export function getAuthConfig(): AuthConfig {
  return {
    authorizationEndpoint: requiredEnv("AUTH_AUTHORIZATION_ENDPOINT"),
    tokenEndpoint: requiredEnv("AUTH_TOKEN_ENDPOINT"),
    logoutEndpoint: requiredEnv("AUTH_LOGOUT_ENDPOINT"),
    logoutRedirectParam: process.env.AUTH_LOGOUT_REDIRECT_PARAM ?? "post_logout_redirect_uri",
    clientId: requiredEnv("AUTH_CLIENT_ID"),
    redirectUri: requiredEnv("AUTH_REDIRECT_URI"),
    logoutRedirectUri: requiredEnv("AUTH_LOGOUT_REDIRECT_URI"),
    scopes: process.env.AUTH_SCOPES ?? "openid email profile",
  };
}

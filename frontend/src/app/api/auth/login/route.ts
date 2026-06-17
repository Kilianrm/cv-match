import { NextResponse } from "next/server";

import { createCodeChallenge, createCodeVerifier, createStateToken, getAuthConfig } from "@/lib/auth";

export async function GET(): Promise<NextResponse> {
  const auth = getAuthConfig();

  const verifier = createCodeVerifier();
  const challenge = createCodeChallenge(verifier);
  const state = createStateToken();

  const authUrl = new URL(auth.authorizationEndpoint);
  authUrl.searchParams.set("response_type", "code");
  authUrl.searchParams.set("client_id", auth.clientId);
  authUrl.searchParams.set("redirect_uri", auth.redirectUri);
  authUrl.searchParams.set("scope", auth.scopes);
  authUrl.searchParams.set("code_challenge_method", "S256");
  authUrl.searchParams.set("code_challenge", challenge);
  authUrl.searchParams.set("state", state);

  const response = NextResponse.redirect(authUrl);
  response.cookies.set("cv_pkce_verifier", verifier, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    maxAge: 10 * 60,
    path: "/",
  });
  response.cookies.set("cv_oauth_state", state, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    maxAge: 10 * 60,
    path: "/",
  });

  return response;
}

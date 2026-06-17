import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

import { getAuthConfig } from "@/lib/auth";

type TokenResponse = {
  access_token: string;
  id_token: string;
  refresh_token?: string;
  expires_in: number;
  token_type: string;
};

export async function GET(request: NextRequest): Promise<NextResponse> {
  const cookieStore = await cookies();
  const requestUrl = request.nextUrl;
  const code = requestUrl.searchParams.get("code");
  const returnedState = requestUrl.searchParams.get("state");
  const storedState = cookieStore.get("cv_oauth_state")?.value;
  const codeVerifier = cookieStore.get("cv_pkce_verifier")?.value;

  if (!code || !returnedState || !storedState || returnedState !== storedState || !codeVerifier) {
    return NextResponse.redirect(new URL("/?error=auth_state", request.url));
  }

  const auth = getAuthConfig();

  const body = new URLSearchParams();
  body.set("grant_type", "authorization_code");
  body.set("client_id", auth.clientId);
  body.set("code", code);
  body.set("redirect_uri", auth.redirectUri);
  body.set("code_verifier", codeVerifier);

  const tokenResponse = await fetch(auth.tokenEndpoint, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });

  if (!tokenResponse.ok) {
    return NextResponse.redirect(new URL("/?error=auth_token", request.url));
  }

  const tokenPayload = (await tokenResponse.json()) as TokenResponse;
  const response = NextResponse.redirect(new URL("/dashboard", request.url));

  response.cookies.set("cv_access_token", tokenPayload.access_token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    maxAge: tokenPayload.expires_in,
    path: "/",
  });

  response.cookies.set("cv_id_token", tokenPayload.id_token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    maxAge: tokenPayload.expires_in,
    path: "/",
  });

  response.cookies.delete("cv_pkce_verifier");
  response.cookies.delete("cv_oauth_state");

  return response;
}

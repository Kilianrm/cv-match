import { NextResponse } from "next/server";

import { getAuthConfig } from "@/lib/auth";

export async function GET(): Promise<NextResponse> {
  const auth = getAuthConfig();

  const logoutUrl = new URL(auth.logoutEndpoint);
  logoutUrl.searchParams.set("client_id", auth.clientId);
  logoutUrl.searchParams.set(auth.logoutRedirectParam, auth.logoutRedirectUri);

  const response = NextResponse.redirect(logoutUrl);
  response.cookies.delete("cv_access_token");
  response.cookies.delete("cv_id_token");
  response.cookies.delete("cv_pkce_verifier");
  response.cookies.delete("cv_oauth_state");

  return response;
}

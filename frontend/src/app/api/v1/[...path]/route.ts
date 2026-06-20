import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

const DEFAULT_GATEWAY_BASE_URL = "http://localhost:8000";

function gatewayBaseUrl(): string {
  return (
    process.env.API_GATEWAY_BASE_URL ||
    process.env.NEXT_PUBLIC_API_GATEWAY_BASE_URL ||
    DEFAULT_GATEWAY_BASE_URL
  );
}

async function proxyToGatewayV1(request: NextRequest, path: string[]): Promise<Response> {
  const cookieStore = await cookies();
  const accessToken = cookieStore.get("cv_access_token")?.value;

  if (!accessToken) {
    return NextResponse.json({ detail: "Missing session token" }, { status: 401 });
  }

  const targetUrl = new URL(`${gatewayBaseUrl()}/api/v1/${path.join("/")}`);
  targetUrl.search = request.nextUrl.search;

  const headers = new Headers();
  headers.set("Authorization", `Bearer ${accessToken}`);

  const incomingContentType = request.headers.get("content-type");
  let body: BodyInit | undefined;

  if (request.method !== "GET" && request.method !== "HEAD") {
    if (incomingContentType?.includes("multipart/form-data")) {
      body = await request.formData();
    } else {
      const rawBody = await request.text();
      if (rawBody.length > 0) {
        body = rawBody;
      }
      if (incomingContentType) {
        headers.set("Content-Type", incomingContentType);
      }
    }
  }

  const upstream = await fetch(targetUrl, {
    method: request.method,
    headers,
    body,
    cache: "no-store",
  });

  if (upstream.status === 204) {
    return new NextResponse(null, { status: 204 });
  }

  const contentType = upstream.headers.get("content-type") || "application/json";
  const payload = await upstream.arrayBuffer();

  return new NextResponse(payload, {
    status: upstream.status,
    headers: {
      "Content-Type": contentType,
    },
  });
}

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
): Promise<Response> {
  const { path } = await context.params;
  return proxyToGatewayV1(request, path);
}

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
): Promise<Response> {
  const { path } = await context.params;
  return proxyToGatewayV1(request, path);
}

export async function PUT(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
): Promise<Response> {
  const { path } = await context.params;
  return proxyToGatewayV1(request, path);
}

export async function DELETE(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
): Promise<Response> {
  const { path } = await context.params;
  return proxyToGatewayV1(request, path);
}

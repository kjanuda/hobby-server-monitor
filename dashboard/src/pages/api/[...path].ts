import type {
  APIContext,
  APIRoute,
} from "astro";

export const prerender = false;

const BACKEND_URL =
  process.env.HSM_BACKEND_URL ??
  "http://127.0.0.1:8000";


async function proxyRequest(
  context: APIContext,
): Promise<Response> {
  const path = context.params.path ?? "";

  const incomingUrl = new URL(
    context.request.url,
  );

  const targetUrl = new URL(
    `/api/${path}${incomingUrl.search}`,
    BACKEND_URL,
  );

  const headers = new Headers(
    context.request.headers,
  );

  headers.delete("host");
  headers.delete("content-length");

  const method = context.request.method;

  const body =
    method === "GET" || method === "HEAD"
      ? undefined
      : await context.request.arrayBuffer();

  const backendResponse = await fetch(
    targetUrl,
    {
      method,
      headers,
      body,
      redirect: "manual",
    },
  );

  const responseHeaders = new Headers();

  backendResponse.headers.forEach(
    (value, key) => {
      if (
        key.toLowerCase()
        !== "set-cookie"
      ) {
        responseHeaders.append(
          key,
          value,
        );
      }
    },
  );

  const headersWithCookies =
    backendResponse.headers as Headers & {
      getSetCookie?: () => string[];
    };

  const setCookies =
    headersWithCookies.getSetCookie?.()
    ?? [];

  for (const cookie of setCookies) {
    responseHeaders.append(
      "set-cookie",
      cookie,
    );
  }

  return new Response(
    backendResponse.body,
    {
      status: backendResponse.status,
      statusText:
        backendResponse.statusText,
      headers: responseHeaders,
    },
  );
}


export const GET: APIRoute =
  proxyRequest;

export const POST: APIRoute =
  proxyRequest;

export const PUT: APIRoute =
  proxyRequest;

export const PATCH: APIRoute =
  proxyRequest;

export const DELETE: APIRoute =
  proxyRequest;

export const OPTIONS: APIRoute =
  proxyRequest;

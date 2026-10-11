export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const targetUrl = new URL(url.pathname + url.search, "https://mindmaxing-creatives-9sz.pages.dev");

    const reqHeaders = new Headers(request.headers);
    reqHeaders.set("Host", "mindmaxing-creatives-9sz.pages.dev");
    reqHeaders.set("X-Forwarded-Host", url.host);
    reqHeaders.set("X-Forwarded-Proto", url.protocol.replace(":", ""));

    const proxyRequest = new Request(targetUrl.toString(), {
      method: request.method,
      headers: reqHeaders,
      body: request.body,
      redirect: "manual"
    });

    const response = await fetch(proxyRequest);

    const respHeaders = new Headers(response.headers);
    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: respHeaders
    });
  }
};

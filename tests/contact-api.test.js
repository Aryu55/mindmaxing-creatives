import test from "node:test";
import assert from "node:assert/strict";
import { onRequestPost } from "../functions/api/contact.js";

test("contact email escapes visitor-controlled HTML", async () => {
  const originalFetch = globalThis.fetch;
  let sentPayload;
  globalThis.fetch = async (_url, options) => {
    sentPayload = JSON.parse(options.body);
    return new Response(JSON.stringify({ id: "email_test" }), { status: 200 });
  };

  try {
    const request = new Request("https://mindmaxing.one/api/contact", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: "<script>alert(1)</script>",
        email: "person@example.com",
        details: "<img src=x onerror=alert(1)> & hello",
        project: "<b>Knittire</b>",
      }),
    });
    const response = await onRequestPost({ request, env: { RESEND_API_KEY: "test-key" } });
    assert.equal(response.status, 200);
    assert.match(sentPayload.html, /&lt;script&gt;alert\(1\)&lt;\/script&gt;/);
    assert.match(sentPayload.html, /&lt;img src=x onerror=alert\(1\)&gt; &amp; hello/);
    assert.doesNotMatch(sentPayload.html, /<script>alert\(1\)<\/script>/);
    assert.match(sentPayload.html, /&lt;b&gt;Knittire&lt;\/b&gt;/);
    assert.match(sentPayload.text, /Related project: <b>Knittire<\/b>/);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

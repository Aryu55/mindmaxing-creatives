const json = (body, status = 200) => new Response(JSON.stringify(body), {
  status,
  headers: { "Content-Type": "application/json; charset=utf-8" },
});

const cleanText = (value, maxLength) => typeof value === "string" ? value.trim().slice(0, maxLength) : "";
const escapeHtml = (value) => value.replace(/[&<>"']/g, (character) => ({
  "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  '"': "&quot;",
  "'": "&#39;",
}[character]));

export async function onRequestPost(context) {
  let data;
  try {
    data = await context.request.json();
  } catch {
    return json({ error: "Send the project details as valid JSON." }, 400);
  }

  if (!data || typeof data !== "object" || Array.isArray(data)) {
    return json({ error: "Send the project details as a JSON object." }, 400);
  }

  const name = cleanText(data.name, 120);
  const email = cleanText(data.email, 320);
  const phone = cleanText(data.phone, 80);
  const budget = cleanText(data.budget, 120);
  const details = cleanText(data.details, 10000);
  const project = cleanText(data.project, 120);

  if (!name || !email || !details) {
    return json({ error: "Name, email, and project details are required." }, 400);
  }
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return json({ error: "Enter a valid email address." }, 400);
  }

  const resendApiKey = context.env?.RESEND_API_KEY;
  if (!resendApiKey) return json({ error: "The inquiry service is not configured yet." }, 503);

  const safeName = escapeHtml(name);
  const safeEmail = escapeHtml(email);
  const safePhone = escapeHtml(phone || "Not provided");
  const safeBudget = escapeHtml(budget || "Not specified");
  const safeDetails = escapeHtml(details);
  const subjectName = name.replace(/[\r\n]+/g, " ").slice(0, 100);

  try {
    const response = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${resendApiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        from: "Mindmaxing Studio <onboarding@resend.dev>",
        to: ["mindmaxxxing@gmail.com"],
        reply_to: email,
        subject: `New project enquiry: ${subjectName}`,
        html: `
          <div style="font-family: Arial, sans-serif; background-color: #08090a; color: #f4f1ec; padding: 24px; border-radius: 8px;">
            <h2 style="color: #e5a950; margin-top: 0;">New project enquiry — Mindmaxing Studio</h2>
            <p style="font-size: 16px;"><strong>From:</strong> ${safeName} (&lt;${safeEmail}&gt;)</p>
            <p style="font-size: 16px;"><strong>Phone:</strong> ${safePhone}</p>
            <p style="font-size: 16px;"><strong>Budget:</strong> ${safeBudget}</p>
            ${project ? `<p style="font-size: 16px;"><strong>Related project:</strong> ${escapeHtml(project)}</p>` : ""}
            <hr style="border-color: rgba(244,241,236,0.15); margin: 20px 0;" />
            <h3 style="color: #f4f1ec;">Project details</h3>
            <div style="background-color: #12151b; padding: 16px; border-left: 2px solid #e5a950; border-radius: 4px; line-height: 1.6; white-space: pre-wrap;">${safeDetails}</div>
            <hr style="border-color: rgba(244,241,236,0.15); margin: 20px 0;" />
            <p style="font-size: 12px; color: #888;">Sent via mindmaxing.one</p>
          </div>
        `,
        text: `New project enquiry — Mindmaxing Studio\nFrom: ${name} <${email}>\nPhone: ${phone || "Not provided"}\nBudget: ${budget || "Not specified"}\nRelated project: ${project || "Not specified"}\n\nProject details:\n${details}`,
      }),
    });

    const result = await response.json().catch(() => ({}));
    if (!response.ok) {
      console.error("[Mindmaxing contact] Resend request failed:", response.status);
      return json({ error: "The note could not be delivered right now. Please try again." }, 502);
    }
    return json({ success: true, id: result.id });
  } catch (error) {
    console.error("[Mindmaxing contact] Request failed:", error);
    return json({ error: "The note could not be delivered right now. Please try again." }, 502);
  }
}

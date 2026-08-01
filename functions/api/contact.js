export async function onRequestPost(context) {
  try {
    const data = await context.request.json();
    const { name, email, phone, details, budget } = data;

    if (!name || !email || !details) {
      return new Response(JSON.stringify({ error: "Name, email, and project details are required." }), {
        status: 400,
        headers: { "Content-Type": "application/json" }
      });
    }

    const resendApiKey = context.env.RESEND_API_KEY;

    const res = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${resendApiKey}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        from: "Mindmaxing Studio <onboarding@resend.dev>",
        to: ["mindmaxxxing@gmail.com"],
        reply_to: email,
        subject: `🔥 New Project Enquiry: ${name}`,
        html: `
          <div style="font-family: Arial, sans-serif; background-color: #08090a; color: #f4f1ec; padding: 24px; border-radius: 8px;">
            <h2 style="color: #ff5a1f; margin-top: 0;">New Project Enquiry — Mindmaxing Creatives</h2>
            <p style="font-size: 16px;"><strong>From:</strong> ${name} (&lt;${email}&gt;)</p>
            <p style="font-size: 16px;"><strong>Phone:</strong> ${phone || "Not provided"}</p>
            <p style="font-size: 16px;"><strong>Timeline / Budget:</strong> ${budget || "Not specified"}</p>
            <hr style="border-color: rgba(244,241,236,0.15); margin: 20px 0;" />
            <h3 style="color: #f4f1ec;">Project Details & Problem Statement:</h3>
            <div style="background-color: #121316; padding: 16px; border-left: 4px solid #ff5a1f; border-radius: 4px; line-height: 1.6; white-space: pre-wrap;">${details}</div>
            <hr style="border-color: rgba(244,241,236,0.15); margin: 20px 0;" />
            <p style="font-size: 12px; color: #888;">Sent via Mindmaxing Creatives Portfolio (mindmaxing.one)</p>
          </div>
        `
      })
    });

    const resData = await res.json();

    if (!res.ok) {
      return new Response(JSON.stringify({ error: resData.message || "Failed to deliver email via Resend." }), {
        status: res.status,
        headers: { "Content-Type": "application/json" }
      });
    }

    return new Response(JSON.stringify({ success: true, id: resData.id }), {
      status: 200,
      headers: { "Content-Type": "application/json" }
    });
  } catch (err) {
    return new Response(JSON.stringify({ error: err.message || "Internal server error" }), {
      status: 500,
      headers: { "Content-Type": "application/json" }
    });
  }
}

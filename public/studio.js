const menuButton = document.querySelector(".nav-toggle");
const navLinks = document.querySelector(".nav-links");

if (menuButton && navLinks) {
  menuButton.addEventListener("click", () => {
    const open = menuButton.getAttribute("aria-expanded") !== "true";
    menuButton.setAttribute("aria-expanded", String(open));
    navLinks.classList.toggle("is-open", open);
  });

  navLinks.addEventListener("click", (event) => {
    if (!event.target.closest("a")) return;
    menuButton.setAttribute("aria-expanded", "false");
    navLinks.classList.remove("is-open");
  });

  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    menuButton.setAttribute("aria-expanded", "false");
    navLinks.classList.remove("is-open");
    menuButton.focus();
  });
}

const contactForm = document.querySelector("#contact-form");
if (contactForm) {
  const status = contactForm.querySelector(".form-status");
  const submit = contactForm.querySelector("[type=submit]");

  contactForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!contactForm.reportValidity()) return;

    const values = new FormData(contactForm);
    const payload = {
      name: String(values.get("name") || "").trim(),
      email: String(values.get("email") || "").trim(),
      phone: String(values.get("phone") || "").trim(),
      budget: String(values.get("budget") || "").trim(),
      details: String(values.get("details") || "").trim(),
    };

    status.textContent = "Sending your note…";
    status.dataset.state = "pending";
    submit.disabled = true;

    try {
      const response = await fetch("/api/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok || !result.success) throw new Error("The note could not be sent. Please try again in a moment.");

      status.textContent = "Your note is in. Thanks for giving us the real context.";
      status.dataset.state = "success";
      contactForm.reset();
    } catch (error) {
      status.textContent = error.message || "Something interrupted the send. Please try again.";
      status.dataset.state = "error";
    } finally {
      submit.disabled = false;
    }
  });
}

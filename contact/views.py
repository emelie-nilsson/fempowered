from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMessage
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views.generic.edit import FormView

from .forms import ContactForm

class ContactView(FormView):
    template_name = "contact/contact.html"
    form_class = ContactForm
    success_url = reverse_lazy("contact")

    def form_valid(self, form):
        name = form.cleaned_data["name"]
        email = form.cleaned_data["email"]
        subject = form.cleaned_data.get("subject") or "Contact form message"
        message = form.cleaned_data["message"]

        # Mall
        ctx = {
            "name": name,
            "email": email,
            "subject": subject,
            "message": message,
            "site_name": "Fempowered",
        }
        body_txt = render_to_string("contact/email/contact_email.txt", ctx)

        # Reply to 
        mail = EmailMessage(
            subject=f"[Fempowered] {subject}",
            body=body_txt,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=settings.CONTACT_RECIPIENTS,
            reply_to=[email],
        )
        mail.send(fail_silently=False)

        messages.success(self.request, "Thanks! Your message has been sent.")
        return redirect(self.get_success_url())

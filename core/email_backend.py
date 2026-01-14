from django.core.mail.backends.base import BaseEmailBackend
import resend
import os


class ResendEmailBackend(BaseEmailBackend):
    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        resend.api_key = os.getenv('RESEND_API_KEY')

    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        
        sent_count = 0
        for message in email_messages:
            try:
                params = {
                    "from": message.from_email,
                    "to": list(message.to),
                    "subject": message.subject,
                }
                
                # Se c'è contenuto HTML
                if hasattr(message, 'alternatives') and message.alternatives:
                    for content, mimetype in message.alternatives:
                        if mimetype == 'text/html':
                            params["html"] = content
                            break
                else:
                    params["html"] = message.body
                
                resend.Emails.send(params)
                sent_count += 1
                
            except Exception as e:
                if not self.fail_silently:
                    raise e
        
        return sent_count
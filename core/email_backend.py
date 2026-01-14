from django.core.mail.backends.base import BaseEmailBackend
import resend
import os
import logging

logger = logging.getLogger(__name__)


class ResendEmailBackend(BaseEmailBackend):
    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        resend.api_key = os.getenv('RESEND_API_KEY')
        
        if not resend.api_key:
            logger.error("RESEND_API_KEY non configurata!")

    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        
        sent_count = 0
        for message in email_messages:
            try:
                # Prepara i parametri base
                params: resend.Emails.SendParams = {
                    "from": message.from_email,
                    "to": list(message.to),
                    "subject": message.subject,
                }
                
                # Gestisci CC e BCC se presenti
                if message.cc:
                    params["cc"] = list(message.cc)
                if message.bcc:
                    params["bcc"] = list(message.bcc)
                if message.reply_to:
                    params["reply_to"] = list(message.reply_to)
                
                # Controlla se c'è contenuto HTML (per EmailMultiAlternatives)
                html_content = None
                if hasattr(message, 'alternatives') and message.alternatives:
                    for content, mimetype in message.alternatives:
                        if mimetype == 'text/html':
                            html_content = content
                            break
                
                # Imposta il contenuto
                if html_content:
                    params["html"] = html_content
                    params["text"] = message.body  # Fallback testo
                else:
                    # Solo testo semplice
                    params["html"] = message.body.replace('\n', '<br>')
                    params["text"] = message.body
                
                logger.info(f"Invio email a: {params['to']}")
                
                # Invia email
                response = resend.Emails.send(params)
                logger.info(f"Email inviata con successo: {response}")
                
                sent_count += 1
                
            except Exception as e:
                logger.error(f"Errore invio email: {str(e)}")
                if not self.fail_silently:
                    raise e
        
        return sent_count
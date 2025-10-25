from celery import shared_task
import django

from django.utils import timezone
from django.db import transaction, models
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth import get_user_model
import logging


logger = logging.getLogger(__name__)
User = get_user_model()

@shared_task(
    name='send_investment_created_email',
    max_retries=3,
    default_retry_delay=60,
    bind=True
)
def  send_verification_email_async(email, verification_url):
    """Send account verification email"""
    try:
        # Initialize Django for thread safety
        django.setup()

        subject = "Verify Your Email Address - Action Required"
            
        user_email = User.objects.get(email=email)
        user_email.first_name
        subject = "Welcome to Our Platform!"

            # Create both HTML and plain text versions
        html_message = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .button {{ display: inline-block; padding: 12px 24px; background: #007bff; 
                            color: white; text-decoration: none; border-radius: 4px; }}
                    .footer {{ margin-top: 20px; padding-top: 20px; border-top: 1px solid #eee; 
                            font-size: 12px; color: #666; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h2>Verify Your Email Address</h2>
                    <p>Thank you for registering with our e-commerce platform!</p>
                    <p>Please click the button below to verify your email address:</p>
                    <p>
                        <a href="{verification_url}" class="button">Verify Email Address</a>
                    </p>
                    <p>Or copy and paste this link in your browser:</p>
                    <p><a href="{verification_url}">{verification_url}</a></p>
                    <p>This link will expire in 24 hours.</p>
                    <div class="footer">
                        <p>If you didn't create an account, please ignore this email.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
        plain_message = f"""
            Verify Your Email Address
            
            Thank you for registering with our e-commerce platform!
            
            Please click the following link to verify your email address:
            {verification_url}
            
            This link will expire in 24 hours.
            
            If you didn't create an account, please ignore this email.
            """
            
        print(f"subjects:{subject},\nmessage:{plain_message},\nfrom:{settings.EMAIL_HOST_USER},\nrecipient:{email},\nhtml message:{html_message}")
            # Send the email
        send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                html_message=html_message,
                fail_silently=False,
            )
            
        logger.info(f" Verification email sent successfully to {email}")
        logger.info(f"SUCCESS: Verification email sent via MailerSend to {email}")
        print(f"✅ MailerSend email sent to {email}")
        return True
            
    except Exception as e:
        logger.error(f" Failed to send verification email to {email}: {str(e)}")
        return False
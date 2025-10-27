"""
Email utilities for sending emails.
IMPORTANT: For production on Render, use Celery instead of threading.
"""
import logging
import time
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)


def send_template_mail(subject, template_name, context, from_email, recipient_list, **kwargs):
    """
    Send a templated HTML email synchronously.
    
    Usage:
        send_template_mail(
            subject="Welcome!",
            template_name="emails/welcome.html",
            context={"user_name": "John"},
            from_email="noreply@example.com",
            recipient_list=["user@example.com"]
        )
    """
    try:
        # Render the HTML template
        html_message = render_to_string(template_name, context)
        
        # Create plain text version (strip HTML tags properly)
        from django.utils.html import strip_tags
        plain_message = strip_tags(html_message)
        
        # Send the email
        email = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=from_email,
            to=recipient_list,
            **kwargs
        )
        email.attach_alternative(html_message, "text/html")
        result = email.send(fail_silently=False)
        
        logger.info(f"Template email '{template_name}' sent successfully to {recipient_list}")
        return result
    except Exception as e:
        logger.error(f"Failed to send template email '{template_name}' to {recipient_list}: {e}")
        raise


def send_verification_email(email, verification_url):
    """
    Send account verification email SYNCHRONOUSLY.
    For production, this should be called via Celery task.
    """
    max_retries = 2
    retry_count = 0
    
    while retry_count <= max_retries:
        try:
            user = User.objects.get(email=email)

            subject = f"Welcome {user.first_name}! Verify Your Email Address"
            
            # Create HTML email content
            html_message = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .button {{ 
                        display: inline-block; 
                        padding: 12px 24px; 
                        background-color: #4CAF50; 
                        color: white; 
                        text-decoration: none; 
                        border-radius: 4px;
                        margin: 20px 0;
                    }}
                    .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #666; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h2>Welcome to E-Commerce Platform, {user.first_name}!</h2>
                    <p>Thank you for signing up. Please verify your email address to activate your account.</p>
                    <p>Click the button below to verify your email:</p>
                    <a href="{verification_url}" class="button">Verify Email Address</a>
                    <p>Or copy and paste this link into your browser:</p>
                    <p style="word-break: break-all; color: #0066cc;">{verification_url}</p>
                    <p>This link will expire in 24 hours.</p>
                    <div class="footer">
                        <p>If you didn't create an account, please ignore this email.</p>
                        <p>&copy; 2025 E-Commerce Platform. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Plain text version
            plain_message = f"""
            Welcome to E-Commerce Platform, {user.first_name}!
            
            Thank you for signing up. Please verify your email address to activate your account.
            
            Click this link to verify your email:
            {verification_url}
            
            This link will expire in 24 hours.
            
            If you didn't create an account, please ignore this email.
            """

            # Send email with both HTML and plain text versions
            email_obj = EmailMultiAlternatives(
                subject=subject,
                body=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[email]
            )
            email_obj.attach_alternative(html_message, "text/html")
            result = email_obj.send(fail_silently=False)

            if result == 1:
                logger.info(f"✅ Verification email sent successfully to {email}")
                return True
            else:
                logger.warning(f"Email send returned {result} for {email}")
                return False
                
        except User.DoesNotExist:
            logger.error(f"User with email {email} does not exist")
            return False
            
        except Exception as e:
            retry_count += 1
            logger.error(f"Attempt {retry_count}/{max_retries} failed to send verification email to {email}: {e}")

            if retry_count <= max_retries:
                time.sleep(1)  # Wait 1 second before retry
            else:
                logger.error(f"All retries exhausted for verification email to {email}")
                return False


def send_welcome_email(user_id, first_name, email, verification_token):
    """
    Send welcome email SYNCHRONOUSLY.
    For production, this should be called via Celery task.
    """
    try:
        user = User.objects.get(id=user_id)
        
        subject = "Welcome to E-Commerce! 🎉"
        
        html_message = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9; }}
                .content {{ background-color: white; padding: 30px; border-radius: 8px; }}
                h1 {{ color: #2c3e50; }}
                .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="content">
                    <h1>Welcome to E-Commerce! 🎉</h1>
                    <p>Hi {first_name}!</p>
                    <p>We're excited to have you on board!</p>
                    <p>Your account ({email}) has been successfully verified and activated.</p>
                    <p>You can now start shopping and exploring our platform.</p>
                    <p>Best regards,<br>The E-Commerce Team</p>
                </div>
                <div class="footer">
                    <p>&copy; 2025 E-Commerce Platform. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        plain_message = f"""
        Welcome to E-Commerce, {first_name}!
        
        We're excited to have you on board!
        
        Your account ({email}) has been successfully verified and activated.
        You can now start shopping and exploring our platform.
        
        Best regards,
        The E-Commerce Team
        """

        email_obj = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email]
        )
        email_obj.attach_alternative(html_message, "text/html")
        email_obj.send(fail_silently=False)
        
        logger.info(f"Welcome email sent successfully to user {user_id} ({email})")
        return True
    except Exception as e:
        logger.error(f"Failed to send welcome email to user {user_id}: {e}")
        import traceback
        logger.error(f"Welcome email traceback: {traceback.format_exc()}")
        return False
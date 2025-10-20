"""
Email utilities for sending emails in background threads.
Thales ika developer is using this simple email sending to avoid queue overhead.
"""
import threading
import logging
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth.models import User
from django.utils.html import strip_tags
import django
from django.template.loader import render_to_string
from threading import Thread
import logging

# from investments.models import (
#         HiVaultInvestment, HiWealthInvestment, EarlyStarterInvestment,
#         HalalInvestment, ReliefInvestment, SeniorsInvestment, VacayInvestment)
# from investments.models import FreestyleDeposit, FreestyleInvestmentAccount
# from investments.models import PaymentCard

logger = logging.getLogger(__name__)


# #function for sending mail using thread(*not used yet*)
# def send_mail_in_thread(*args, **kwargs):
#     """
#     Send a simple email in a background thread.
    
#     Usage:
#         send_mail_in_thread(subject, message, from_email, recipient_list)
#     """
#     def _send():
#         try:
#             send_mail(*args, **kwargs)
#             logger.info(f"Email sent successfully to {kwargs.get('recipient_list', args[3] if len(args) > 3 else 'unknown')}")
#         except Exception as e:
#             logger.error(f"Failed to send email: {e}")
    
#     threading.Thread(target=_send, daemon=True).start()


# #function for sending html email
# def send_html_mail_in_thread(subject, message, from_email, recipient_list, html_message=None, **kwargs):
#     """
#     Send an HTML email in a background thread.
    
#     Usage:
#         send_html_mail_in_thread(
#             subject="Test Subject",
#             message="Plain text message",
#             from_email="noreply@example.com",
#             recipient_list=["user@example.com"],
#             html_message="<h1>HTML message</h1>"
#         )
#     """
#     def _send():
#         try:
#             email = EmailMultiAlternatives(subject, message, from_email, recipient_list, **kwargs)
#             if html_message:
#                 email.attach_alternative(html_message, "text/html")
#             email.send()
#             logger.info(f"HTML email sent successfully to {recipient_list}")
#         except Exception as e:
#             logger.error(f"Failed to send HTML email to {recipient_list}: {e}")
    
#     threading.Thread(target=_send, daemon=True).start()


def send_template_mail_in_thread(subject, template_name, context, from_email, recipient_list, **kwargs):
    """
    Send a templated HTML email in a background thread.
    
    Usage:
        send_template_mail_in_thread(
            subject="Welcome!",
            template_name="emails/welcome.html",
            context={"user_name": "John"},
            from_email="noreply@example.com",
            recipient_list=["user@example.com"]
        )
    """
    def _send():
        try:
            # Render the HTML template
            html_message = render_to_string(template_name, context)
            
            # Create plain text version (simple strip of HTML tags)
            plain_message = html_message
            
            # Send the email
            email = EmailMultiAlternatives(subject, plain_message, from_email, recipient_list, **kwargs)
            email.attach_alternative(html_message, "text/html")
            email.send()
            
            logger.info(f"Template email '{template_name}' sent successfully to {recipient_list}")
        except Exception as e:
            logger.error(f"Failed to send template email '{template_name}' to {recipient_list}: {e}")
    
    threading.Thread(target=_send, daemon=True).start()


import logging
import threading
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import django

logger = logging.getLogger(__name__)

def send_verification_email(user_id, email, verification_url):
    """Send account verification email"""
    try:
        # Initialize Django for thread safety
        django.setup()
        
        subject = "Verify Your Email Address - Action Required"
        
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
        
        # Send the email
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"✅ Verification email sent successfully to {email}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to send verification email to {email}: {str(e)}")
        return False

def send_welcome_email_threaded(user_id, first_name, email):
    """Send welcome email in background thread"""
    def _send():
        try:
            django.setup()  # Ensure Django is properly initialized in thread
            
            subject = "Welcome to Our E-Commerce Store! 🎉"
            
            html_message = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1 style="color: #2c3e50;">Welcome to Our Store! 🎉</h1>
                    <p>Hi <strong>{first_name}</strong>!</p>
                    <p>We're excited to have you on board!</p>
                    <p>Your account <strong>({email})</strong> has been successfully verified.</p>
                    <p>You can now login and start shopping!</p>
                    <p>Best regards,<br>The E-Commerce Team</p>
                </div>
            </body>
            </html>
            """
            
            plain_message = f"""
            Welcome to Our E-Commerce Store, {first_name}!
            
            We're excited to have you on board!
            Your account ({email}) has been successfully verified.
            
            You can now login and start shopping!
            
            Best regards,
            The E-Commerce Team
            """
            
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                html_message=html_message,
                fail_silently=False,
            )
            
            logger.info(f"✅ Welcome email sent successfully to user {user_id} ({email})")
        except Exception as e:
            logger.error(f"❌ Failed to send welcome email to user {user_id}: {e}")
    
    # Start the thread
    thread = threading.Thread(target=_send, daemon=True)
    thread.start()
    
# #investment created email
# def send_investment_created_email_threaded(user_id, investment_id, investment_type, transaction_reference):
#     """Send investment created email in background thread"""
#     def _send():
#         try:
          
            
#             user = User.objects.get(id=user_id)
            
#             # Get the investment model based on type
#             model_map = {
#                 'hivault': HiVaultInvestment,
#                 'hiwealth': HiWealthInvestment,
#                 'earlystarter': EarlyStarterInvestment,
#                 'halal': HalalInvestment,
#                 'relief': ReliefInvestment,
#                 'seniors': SeniorsInvestment,
#                 'vacay': VacayInvestment,
#             }
            
#             model_class = model_map.get(investment_type.lower())
#             if not model_class:
#                 logger.error(f"Unknown investment type: {investment_type}")
#                 return f"This investment isn't available"

#             investment = model_class.objects.get(id=investment_id)
            
#             subject = f"Investment Created Successfully - {investment_type.title()}"
#             context = {
#                 "user_name": user.first_name,
#                 "investment_type": investment_type.title(),
#                 "investment_name": getattr(investment, 'name', f"{investment_type.title()} Investment"),
#                 "amount": getattr(investment, 'target_amount', getattr(investment, 'amount', 0)),
#                 "transaction_reference": transaction_reference,
#                 "company_name": "HiYield",
#             }
            
#             html_message = render_to_string("investments/emails/investment_created.html", context)
#             plain_message = f"Your {investment_type.title()} investment has been created successfully!"
            
#             email_obj = EmailMultiAlternatives(
#                 subject=subject,
#                 body=plain_message,
#                 from_email=settings.DEFAULT_FROM_EMAIL,
#                 to=[user.email]
#             )
#             email_obj.attach_alternative(html_message, "text/html")
#             email_obj.send()
            
#             logger.info(f"Investment created email sent successfully to user {user_id} for {investment_type} investment {investment_id}")
#         except Exception as e:
#             logger.error(f"Failed to send investment created email to user {user_id}: {e}")
    
#     threading.Thread(target=_send, daemon=True).start()


# #deposit successful mail
# def send_deposit_successful_email_threaded(user_id, deposit_id, previous_balance=None):
#     """Send deposit successful email in background thread"""
#     def _send():
#         try:
            
            
            
#             user = User.objects.get(id=user_id)
#             deposit = FreestyleDeposit.objects.get(id=deposit_id)
#             freestyle_account = FreestyleInvestmentAccount.objects.get(user=user)
            
#             subject = "Deposit Successful! 💰"
#             context = {
#                 "user_name": user.first_name,
#                 "deposit_amount": deposit.amount,
#                 "previous_balance": previous_balance,
#                 "new_balance": freestyle_account.current_amount,
#                 "deposit_reference": deposit.payment_reference,
#                 "company_name": "HiYield",
#             }
            
#             html_message = render_to_string("investments/emails/deposit_successful.html", context)
#             plain_message = f"Your deposit of ₦{deposit.amount} was successful!"
            
#             email_obj = EmailMultiAlternatives(
#                 subject=subject,
#                 body=plain_message,
#                 from_email=settings.DEFAULT_FROM_EMAIL,
#                 to=[user.email]
#             )
#             email_obj.attach_alternative(html_message, "text/html")
#             email_obj.send()
            
#             logger.info(f"Deposit successful email sent successfully to user {user_id} for deposit {deposit_id}")
#         except Exception as e:
#             logger.error(f"Failed to send deposit successful email to user {user_id}: {e}")
    
#     threading.Thread(target=_send, daemon=True).start()

# #card email
# def send_card_added_email_threaded(user_id, card_id):
#     """Send card added email in background thread"""
#     def _send():
#         try:
            
#             user = User.objects.get(id=user_id)
#             card = PaymentCard.objects.get(id=card_id)
            
#             subject = "Payment Card Added Successfully! 💳"
#             context = {
#                 "user_name": user.first_name,
#                 "card_last_4": card.card_last_4,
#                 "card_brand": card.card_brand,
#                 "card_name": card.card_name,
#                 "company_name": "HiYield",
#             }
            
#             html_message = render_to_string("investments/emails/card_added.html", context)
#             plain_message = f"Your {card.card_brand} card ending in {card.card_last_4} has been added successfully!"
            
#             email_obj = EmailMultiAlternatives(
#                 subject=subject,
#                 body=plain_message,
#                 from_email=settings.DEFAULT_FROM_EMAIL,
#                 to=[user.email]
#             )
#             email_obj.attach_alternative(html_message, "text/html")
#             email_obj.send()
            
#             logger.info(f"Card added email sent successfully to user {user_id} for card {card_id}")
#         except Exception as e:
#             logger.error(f"Failed to send card added email to user {user_id}: {e}")
    
#     threading.Thread(target=_send, daemon=True).start()

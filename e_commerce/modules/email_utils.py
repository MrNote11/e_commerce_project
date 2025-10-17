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


# Specific email functions for your app 
def send_welcome_email_threaded(user_id, first_name, email):
    """Send welcome email in background thread"""
    def _send():
        try:
           
            django.setup()  # Ensure Django is properly initialized in thread
            
            user = User.objects.get(id=user_id)
            
            subject = "Welcome to e_commerce_app! 🎉"
            context = {
                "user_name": first_name,
                "user_email": email,
            }
            
            # Try to render template, fallback to simple HTML if it fails
            try:
                html_message = render_to_string("templates/home/emails/welcome.html", context)
                logger.info(f"Welcome template rendered successfully for user {user_id}")
            except Exception as template_error:
                logger.error(f"Template rendering failed for user {user_id}: {template_error}")
                # Fallback to simple HTML
                html_message = f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h1 style="color: #2c3e50;">Welcome to HiYield! 🎉</h1>
                    <p>Hi {first_name}!</p>
                    <p>We're excited to have you on board!</p>
                    <p>Your account ({email}) has been successfully created.</p>
                    <p>Best regards,<br>The e_commerce_app! Team</p>
                </div>
                """
            
            plain_message = f"Welcome to e_commerce_app, {first_name}! We're excited to have you on board."
            
            email_obj = EmailMultiAlternatives(
                subject=subject,
                body=plain_message,
                from_email=settings.EMAIL_HOST_USER,
                to=[email]
            )
            email_obj.attach_alternative(html_message, "text/html")
            email_obj.send()
            
            logger.info(f"Welcome email sent successfully to user {user_id} ({email})")
        except Exception as e:
            logger.error(f"Failed to send welcome email to user {user_id}: {e}")
            import traceback
            logger.error(f"Welcome email traceback: {traceback.format_exc()}")
    
    threading.Thread(target=_send, daemon=True).start()


# email_utils.py
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from threading import Thread
import logging

logger = logging.getLogger(__name__)

def send_verification_email_threaded(user_id, first_name, email, verification_url):
    """Send verification email in background thread"""
    thread = Thread(target=send_verification_email, args=(user_id, first_name, email, verification_url))
    thread.daemon = True
    thread.start()

def send_verification_email(user_id, first_name, email, verification_url):
    """Send account verification email"""
    try:
        subject = "Verify Your Account - Welcome to Our Platform!"
        
        # HTML email content
        html_message = render_to_string('templates/home/emails/verification_email.html', {
            'first_name': first_name,
            'verification_url': verification_url,
            'support_email': 'support@yourapp.com'
        })
        
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Verification email sent to {email} for user {user_id}")
        
    except Exception as e:
        logger.error(f"Failed to send verification email to {email}: {str(e)}")
        raise

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

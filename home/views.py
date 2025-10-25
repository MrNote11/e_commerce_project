# # Imports utility for logging user/admin activities
# from admin_panel.utils import log_activity

# Imports request validation, standardized API response formatting
from django.shortcuts import redirect
from e_commerce.modules.utils import incoming_request_checks, api_response

from e_commerce.modules.utils import log_request
# Imports custom exception handler for serializer errors
from e_commerce.modules.exceptions import raise_serializer_error_msg

# Imports base class for creating API endpoints
from rest_framework.views import APIView

# Imports class for sending HTTP responses in DRF
from rest_framework.response import Response

# Imports HTTP status codes for response status
from rest_framework import status

# Imports JWT access token generator for authentication
from rest_framework_simplejwt.tokens import AccessToken

# Imports all serializers for request/response validation
from .serializers import *

# Imports decorator for auto-generating Swagger API docs
from drf_yasg.utils import swagger_auto_schema

# Imports permission class to restrict access to authenticated users
from rest_framework.permissions import IsAuthenticated

# Imports class for sending basic HTTP responses
from django.http import HttpResponse

# Imports OpenAPI schema objects for API documentation
from drf_yasg import openapi

# # Imports specific serializer for account tier output
# from .serializers import AccountTierSerializerOut

# # Imports models for account tier and BVN verification attempts
# from .models import AccountTier, BVNVerificationAttempt

# Imports generic list view for listing objects
from rest_framework.generics import ListAPIView

# # Imports custom permission to restrict access to resource owners
# from investments.permissions import IsOwner

from e_commerce.modules.email_utils import send_verification_email

# Imports utilities for encrypting/decrypting sensitive data
from e_commerce.modules.utils import encrypt_text, decrypt_text

# Imports timezone utilities for date/time operations
from django.utils import timezone

# Imports timedelta for time calculations
from datetime import timedelta

# # Imports serializer for BVN verification attempt output
# from .serializers import BVNVerificationAttemptSerializer

# Imports custom throttling classes for rate limiting
from e_commerce.modules.throttling import AuthRateThrottle, SignupThrottle
from django.conf import settings
# Imports Python logging for error/activity logging
import logging

# Imports admin activity logger
# from admin_panel.utils import log_admin_activity


# Imports Decimal for precise financial calculations
from decimal import Decimal 
from e_commerce.modules.email_utils import send_welcome_email_threaded
from .models import UserProfile
from django.contrib.auth.models import User



logger = logging.getLogger(__name__)

def welcome_message(request):
    return HttpResponse("Welcome to the API, Built by Sulaiman😛")


class LoginAPIView(APIView):
    permission_classes = []
    throttle_classes = [AuthRateThrottle]

    @swagger_auto_schema(
        request_body=LoginSerializerIn,
        responses={200: openapi.Response(description="Login successful")},
        consumes=['application/json'],
        produces=['application/json']
    )
    def post(self, request):
        status_, data = incoming_request_checks(request)
        if not status_:
            return Response(
                api_response(message=data, status=False),
                status=status.HTTP_400_BAD_REQUEST,
            )
        email = data.get('email')
        
        # Check if user exists and is locked
        try:
            user = User.objects.get(username=email)
            
            # Check if account is locked
            userprofile = getattr(user, 'userprofile', None)
            if not userprofile:
                return Response(
                    api_response(
                        message="User profile not found. Please contact support.",
                        status=False,
                        data=None
                    ),
                    status=status.HTTP_400_BAD_REQUEST
                )
            if userprofile.is_locked():
                remaining_seconds = userprofile.get_lockout_remaining()
                return Response(
                    api_response(
                        message="Account is temporarily locked due to "
                        "multiple failed login attempts "
                        f"Minutes remaining {remaining_seconds // 60}.",
                        status=False,
                        data={
                            'locked_until': userprofile.locked_until,
                            'remaining_seconds': remaining_seconds,
                            'minutes_remaining': remaining_seconds // 60
                        }
                    ),
                    status=status.HTTP_423_LOCKED
                )
                
        except User.DoesNotExist:
            # User doesn't exist, continue with normal flow
            pass

        serializer = LoginSerializerIn(data=data, context={"request": request})
        serializer.is_valid() or raise_serializer_error_msg(errors=serializer.errors)
        user = serializer.save()
        
    # log_activity(
        #     user=data.get('email'),
        #     activity_type='LOGIN',
        #     description=(
        #         f"User {email} login"
        #     ),
        #     ip_address=request.META.get('REMOTE_ADDR')
        # )
        
        
    
        return Response(
            api_response(
                message="Login successful",
                status=True,
                data={
                    "userData": UserSerializerOut(
                        user, context={"request": request}
                    ).data,
                    "accessToken": AccessToken.for_user(user),
                },
            )
        )


class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [AuthRateThrottle]

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'refresh_token': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Refresh token to blacklist (optional)'
                )
            }
        ),
        responses={
            200: openapi.Response(
                description="Logout successful",
                examples={
                    "application/json": {
                        "requestTime": "2024-01-15T10:30:00.123456Z",
                        "requestType": "outbound", 
                        "referenceId": "a1b2c3d4e5f6...",
                        "status": True,
                        "message": "Logout successful",
                        "data": None
                    }
                }
            )
        },
        consumes=['application/json'],
        produces=['application/json']
    )
    def post(self, request):
        status_, data = incoming_request_checks(request)
        if not status_:
            return Response(
                api_response(message=data, status=False),
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        refresh_token = data.get('refresh_token')
        
        try:
            # If using token blacklist, blacklist the refresh token
            if refresh_token:
                try:
                    from rest_framework_simplejwt.tokens import RefreshToken
                    token = RefreshToken(refresh_token)
                    token.blacklist()
                except ImportError:
                    # Blacklist not installed, just continue
                    pass
                except Exception as e:
                    # Log but don't fail the logout
                    logger.warning(f"Token blacklisting failed: {e}")
            
            # Log the logout activity
            # log_activity(
            #     user=request.user.email,
            #     activity_type='LOGOUT',
            #     description=f"User {request.user.email} logged out successfully",
            #     ip_address=request.META.get('REMOTE_ADDR')
            # )
            
            return Response(
                api_response(
                    message="Logout successful",
                    status=True
                )
            )
            
        except Exception as e:
            logger.error(f"Logout error for user {request.user.email}: {e}")
            return Response(
                api_response(
                    message="Error during logout process",
                    status=False
                ),
                status=status.HTTP_400_BAD_REQUEST
            )

class SignupAPIView(APIView):
    permission_classes = []
    throttle_classes = [SignupThrottle]
    
    @swagger_auto_schema(
        request_body=SignupSerializerIn,
        responses={200: openapi.Response(description="Signup successful")},
        consumes=['application/json'],
        produces=['application/json']
    )
    def post(self, request):
        status_, data = incoming_request_checks(request)
        if not status_:
            return Response(
                api_response(message=data, status=False),
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = SignupSerializerIn(data=data, context={"request": request})
        serializer.is_valid() or raise_serializer_error_msg(errors=serializer.errors)
        response = serializer.save()
        user = request.user
        print(f"user:{user}")
        return Response(api_response(message=response, status=True))


# views.py
class VerifyEmailAPIView(APIView):
    permission_classes = []
    
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'token',
                openapi.IN_QUERY,
                description="Email verification token",
                type=openapi.TYPE_STRING,
                required=True
            )
        ],
        responses={
            200: openapi.Response(description="Email verified successfully"),
            400: openapi.Response(description="Invalid or expired token")
        }
    )
    def get(self, request):
        """Verify email via token (for email links)"""
        token = request.GET.get('token')
        
        if not token:
            return Response(
                api_response(message="Verification token is required", status=False),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Find user profile with this token
            user_profile = UserProfile.objects.get(verification_token=token)
            
            # Check if token is expired
            if user_profile.is_verification_token_expired():
                return Response(
                    api_response(message="Verification link has expired. Please request a new one.", status=False),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            
            # Activate the user
            user = user_profile.user
            user.is_active = True
            user.save()
            data = request.user
            print(f"user:{data}")
            user_profile.is_verified = True
            user_profile.verification_token = None  # Clear the used token
            user_profile.save()
            
             # Send welcome email
            try:
                send_welcome_email_threaded(
                    user_id=user.id,
                    first_name=user.first_name,
                    email=user.email
                )
            except Exception as email_error:
                log_request(f"Warning: Failed to send welcome email: {email_error}")
            
            redirect_url = f"{settings.VERCEL_APP_URL}/?verified=true&email={user.email}"
            return redirect(redirect_url)
            
        except UserProfile.DoesNotExist:
            return Response(
                api_response(message="Invalid verification token", status=False),
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            log_request(f"Email verification error: {e}")
            return Response(
                api_response(message="Error verifying email", status=False),
                status=status.HTTP_400_BAD_REQUEST
            )

class ResendVerificationAPIView(APIView):
    permission_classes = []
    
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'email': openapi.Schema(type=openapi.TYPE_STRING)
            }
        ),
        responses={200: openapi.Response(description="Verification email sent")}
    )
    def post(self, request):
        """Resend verification email"""
        status_, data = incoming_request_checks(request)
        if not status_:
            return Response(
                api_response(message=data, status=False),
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        email = data.get('email')
        
        try:
            user = User.objects.get(email=email)
            user_profile = user.userprofile
            
            # Check if already verified
            if user.is_active and user_profile.is_verified:
                return Response(
                    api_response(message="Account is already verified", status=False),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Generate new verification token
            verification_token = user_profile.generate_verification_token()
            
            # Build verification URL
            verification_url = f"https://yourapp.com/verify-email/{verification_token}/"
            
            try:
                send_welcome_email_threaded(
                    user_id=user.id,
                    first_name=user.first_name,
                    email=email,
                    verification_url=verification_url
                )
                log_request(f"Welcome email queued in background thread for user {user.id} ({email})")

        
            except Exception as email_error:
                # Log the error but don't fail the registration
                log_request(f"Warning: Failed to send welcome email: {email_error}")
                log_request(f"Warning: Failed to queue welcome email for user {user.id}: {email_error}")
            
            
            return Response(
                api_response(
                    message="Verification email sent successfully. Please check your inbox.",
                    status=True
                )
            )
            
        except User.DoesNotExist:
            return Response(
                api_response(message="User with this email not found", status=False),
                status=status.HTTP_400_BAD_REQUEST
            )


# views.py
class TestEmailView(APIView):
    permission_classes = []
    
    def post(self, request):
        try:
            email = request.data.get('email', 'test@example.com')
            
            # Test SMTP
            send_mail(
                subject='Test Email',
                message='This is a test email.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            
            return Response({
                'status': True,
                'message': f'Test email sent to {email}',
                'smtp_config': {
                    'host': settings.EMAIL_HOST,
                    'port': settings.EMAIL_PORT,
                    'user': settings.EMAIL_HOST_USER,
                }
            })
        except Exception as e:
            return Response({
                'status': False,
                'message': f'Failed: {str(e)}'
            }, status=500)

class RequestEmailOTPView(APIView):
    permission_classes = []
    @swagger_auto_schema(
        request_body=RequestEmailOTPSerializerIn,
        responses={200: openapi.Response(description="OTP sent to your email")},
    )
    def post(self, request):
        status_, data = incoming_request_checks(request)
        if not status_:
            return Response(
                api_response(message=data, status=False),
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = RequestEmailOTPSerializerIn(data=data, context={"request": request})
        serializer.is_valid() or raise_serializer_error_msg(errors=serializer.errors)
        response = serializer.save()
        return Response(
            api_response(
                message="OTP sent to your email", data=response, status=True
            )
        )


class ConfirmOTPView(APIView):
    permission_classes = []
    
    @swagger_auto_schema(
        request_body=ConfirmOTPSerializerIn,
        responses={200: openapi.Response(description="OTP verified successfully")},
    )
    def post(self, request):
        status_, data = incoming_request_checks(request)
        if not status_:
            return Response(
                api_response(message=data, status=False),
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ConfirmOTPSerializerIn(data=data, context={"request": request})
        serializer.is_valid() or raise_serializer_error_msg(errors=serializer.errors)
        response = serializer.save()
        return Response(
            api_response(
                message="OTP verified successfully", data=response, status=True
            )
        )


class ChangePasswordAPIView(APIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        request_body=ChangePasswordSerializerIn,
        responses={200: openapi.Response(description="Password changed successfully")},
    )

    def post(self, request):
        status_, data = incoming_request_checks(request)
        if not status_:
            return Response(
                api_response(message=data, status=False),
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = ChangePasswordSerializerIn(data=data, context={"request": request})
        serializer.is_valid() or raise_serializer_error_msg(errors=serializer.errors)
        response = serializer.save()
        return Response(api_response(message=response, status=True))



class ResetPasswordAPIView(APIView):
    permission_classes = []

    @swagger_auto_schema(
        request_body=ForgetPasswordSerializerIn,
        responses={200: openapi.Response(description="Password reset successfully")},
    )
    def post(self, request):
        status_, data = incoming_request_checks(request)
        if not status_:
            return Response(
                api_response(message=data, status=False),
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = ForgetPasswordSerializerIn(data=data, context={"request": request})
        serializer.is_valid() or raise_serializer_error_msg(errors=serializer.errors)
        response = serializer.save()
        return Response(api_response(message=response, status=True))


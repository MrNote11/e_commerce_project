from django.shortcuts import redirect
from e_commerce.modules.utils import incoming_request_checks, api_response, log_request
from e_commerce.modules.exceptions import raise_serializer_error_msg
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import AccessToken
from .serializers import *
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
from drf_yasg import openapi
from rest_framework.generics import ListAPIView
from e_commerce.modules.email_utils import send_verification_email, send_welcome_email
from e_commerce.modules.utils import encrypt_text, decrypt_text
from django.utils import timezone
from datetime import timedelta
from e_commerce.modules.throttling import AuthRateThrottle, SignupThrottle
from django.conf import settings
import logging
from decimal import Decimal 
from .models import UserProfile, UserOTP
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
                        "multiple failed login attempts. "
                        f"Minutes remaining: {remaining_seconds // 60}.",
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
            pass

        serializer = LoginSerializerIn(data=data, context={"request": request})
        serializer.is_valid() or raise_serializer_error_msg(errors=serializer.errors)
        user = serializer.save()
    
        return Response(
            api_response(
                message="Login successful",
                status=True,
                data={
                    "userData": UserSerializerOut(
                        user, context={"request": request}
                    ).data,
                    "accessToken": str(AccessToken.for_user(user)),
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
            if refresh_token:
                try:
                    from rest_framework_simplejwt.tokens import RefreshToken
                    token = RefreshToken(refresh_token)
                    token.blacklist()
                except ImportError:
                    pass
                except Exception as e:
                    logger.warning(f"Token blacklisting failed: {e}")
            
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
        
        return Response(api_response(message=response, status=True))


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
            user_profile = UserProfile.objects.get(verification_token=token)
            
            if user_profile.is_verification_token_expired():
                return Response(
                    api_response(message="Verification link has expired. Please request a new one.", status=False),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Activate the user
            user = user_profile.user
            user.is_active = True
            user.save()
            
            user_profile.is_verified = True
            user_profile.verification_token = None
            user_profile.save()
            
            # Get or create UserOTP and generate token
            user_otp, created = UserOTP.objects.get_or_create(
                userprofile=user_profile,
                defaults={
                    'email': user_profile.email,
                    'phoneNumber': user_profile.phoneNumber
                }
            )
            otp_token = user_otp.generate_otp_token()
            
            # Send welcome email SYNCHRONOUSLY (no threading)
            try:
                email_sent = send_welcome_email(
                    user_id=user.id,
                    first_name=user.first_name,
                    email=user.email,
                    verification_token=otp_token
                )
                if email_sent:
                    log_request(f"✅ Welcome email sent to {user.email}")
                else:
                    log_request(f"⚠️ Welcome email may have failed for {user.email}")
            except Exception as email_error:
                log_request(f"Warning: Failed to send welcome email: {email_error}")
            
            # Redirect to frontend with success parameter
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


class RequestEmailOTPView(APIView):
    permission_classes = []
    
    @swagger_auto_schema(
        request_body=RequestEmailOTPSerializerIn,
        responses={200: openapi.Response(description="OTP sent successfully")},
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
            api_response(message="OTP sent successfully", data=response, status=True)
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


# Add these placeholder views if they're referenced in urls.py
class ChangePasswordAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        return Response(
            api_response(message="Change password endpoint - to be implemented", status=False),
            status=status.HTTP_501_NOT_IMPLEMENTED
        )


class ResetPasswordAPIView(APIView):
    permission_classes = []
    
    def post(self, request):
        return Response(
            api_response(message="Reset password endpoint - to be implemented", status=False),
            status=status.HTTP_501_NOT_IMPLEMENTED
        )
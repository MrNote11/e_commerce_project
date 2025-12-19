from django.shortcuts import redirect
from e_commerce.modules.utils import incoming_request_checks, api_response, log_request
from e_commerce.modules.exceptions import raise_serializer_error_msg
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import AccessToken
from .serializers import *
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated, AllowAny
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
from home.models import User, UserProfile, UserOTP
from vendors.models import VendorProfile
from e_commerce.modules.redis_cart import RedisCartService
logger = logging.getLogger(__name__)


def welcome_message(request):
    return HttpResponse("Welcome to the API, Built by Sulaiman😛")

class LoginAPIView(APIView):
    permission_classes = [AllowAny]
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
        data = user
        message = None
        if data.role == User.Role.VENDOR:
            message = {"vendor profile":"update your vendor profile to have full access"}
        return Response(
            api_response(
                message="Login successful",
                status=True,
                data={
                    "userData": UserSerializerOut(
                        user, context={"request": request}
                    ).data,
                    "profile message": message,
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
        user_email = request.user.email
            
            # Clear cart before logout
        cart_service = RedisCartService(request=request)
        success, message = cart_service.handle_user_logout()
            
        if not success:
            logger.warning(f"Cart cleanup failed during logout for user: {user_email}")
            
        refresh_token = data.get('refresh_token')
        
        try:
            if refresh_token:
                try:
                    from rest_framework_simplejwt.tokens import RefreshToken
                    token = RefreshToken(refresh_token)
                    request.session.flush()
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
    permission_classes = [AllowAny]
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
            user_profile = UserProfile.objects.filter(verification_token=token).select_related('user').first()
            vendor_profile = VendorProfile.objects.filter(verification_token=token).select_related('user').first()
           
                
            if vendor_profile:
                if vendor_profile.is_verification_token_expired():
                    return Response(
                        api_response(message="Verification link has expired. Please request a new one.", status=False),
                        status=status.HTTP_400_BAD_REQUEST
                    )
                vendor = vendor_profile.user
                vendor.is_active = True
                vendor.save()
                
                vendor_profile.is_approved  = True
                vendor_profile.verification_token = None
                User.objects.filter(id=vendor_profile.user_id).update(role="vendor")

                vendor_profile.save()
                
                user_profile_ = UserProfile.objects.get(user=vendor)
                user_profile_.is_verified = True
                user_profile_.save()
                
                try:
                    email_sent = send_welcome_email(
                        user_id=vendor.id,
                        first_name=vendor.first_name,
                        email=vendor.email
                    )
                    if email_sent:
                        log_request(f" Welcome email sent to {vendor.email}")
                    else:
                        log_request(f"⚠️ Welcome email may have failed for {vendor.email}")
                except Exception as email_error:
                        log_request(f"Warning: Failed to send welcome email: {email_error}")
            
                return Response(
                api_response(message="Success", status=True),
                status=status.HTTP_400_BAD_REQUEST
                )
            
            elif user_profile:
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
                
                try:
                    email_sent = send_welcome_email(
                        user_id=user.id,
                        first_name=user.first_name,
                        email=user.email,
                    )
                    
                    if email_sent:
                        log_request(f" Welcome email sent to {user.email}")
                    else:
                        log_request(f"⚠️ Welcome email may have failed for {user.email}")
                except Exception as email_error:
                    log_request(f"Warning: Failed to send welcome email: {email_error}")
            
                # Redirect to frontend with success parameter
                redirect_url = f"{settings.VERCEL_APP_URL}/?verified=true&email={user.email}"
                redirect_url = f"{settings.VERCEL_APP_URL_2}/?verified=true&email={user.email}"
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


class UserProfileDetails(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializerOut

    @swagger_auto_schema(
        responses={200: openapi.Response(description="User profile details")},
    )
    def get(self,request):
        serializer = self.serializer_class(request.user.userprofile)
        return Response(api_response(message="User profile details", status=True, data=serializer.data))

# views.py
class UpdateProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [AuthRateThrottle]  # Optional: Add rate limiting
    
    @swagger_auto_schema(
        request_body=UpdateProfileSerializer,
        responses={
            200: openapi.Response(
                description="Profile updated successfully",
                examples={
                    "application/json": {
                        "requestTime": "2024-01-15T10:30:00.123456Z",
                        "requestType": "outbound", 
                        "referenceId": "update_profile_ref_123456",
                        "status": True,
                        "message": "Profile updated successfully",
                        "data": {
                            "username": "john_doe",
                            "email": "john@example.com",
                            "profilePicture": "https://yourapp.com/media/profile_pics/image.jpg",
                            "profileDetail": {
                                "gender": "Male",
                                "phoneNumber": "8012345678",
                                "nin": "12319080",
                                "address": "7, hhigsj",
                                "full_name": "John Doe"
                            }
                        }
                    }
                }
            ),
            400: openapi.Response(
                description="Validation error",
                examples={
                    "application/json": {
                        "requestTime": "2024-01-15T10:30:00.123456Z",
                        "requestType": "outbound",
                        "referenceId": "update_profile_ref_123456", 
                        "status": False,
                        "message": "Validation failed",
                        "data": {
                            "errors": {
                                "email": ["Enter a valid email address."],
                                "user": {
                                    "email": ["This email is already registered."]
                                }
                            }
                        }
                    }
                }
            )
        },
        consumes=['application/json'],
        produces=['application/json'],
        operation_description="Update user profile information including user account details and profile image"
    )
    def patch(self, request):
        """
        Update user profile information
        
        Supports partial updates (PATCH method) for:
        - User fields (username, email, etc.)
        - UserProfile fields (profile image)
        
        Uses atomic transaction to ensure both User and UserProfile updates succeed or fail together
        """
        # Validate incoming request format
        status_, data = incoming_request_checks(request)
        if not status_:
            return Response(
                api_response(message=data, status=False),
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        try:
            # Get the current user's profile
            profile = UserProfile.objects.get(user=request.user)
            
        except UserProfile.DoesNotExist:
            return Response(
                api_response(
                    message="User profile not found. Please contact support.",
                    status=False
                ),
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Initialize serializer for partial update
        serializer = UpdateProfileSerializer(
            profile, 
            data=data, 
            partial=True,  # Allow partial updates for PATCH
            context={'request': request}
        )
        
        # Validate and save
        if serializer.is_valid():
            try:
                # This will trigger your custom update() method
                updated_profile = serializer.save()
                
                # Log the activity (uncomment when ready)
                # log_activity(
                #     user=request.user.email,
                #     activity_type='PROFILE_UPDATE',
                #     description=f"User {request.user.email} updated their profile",
                #     ip_address=request.META.get('REMOTE_ADDR')
                # )
                
                log_request(f"Profile updated successfully for user: {request.user.email}")
                
                return Response(
                    api_response(
                        message="Profile updated successfully",
                        status=True,
                        data=serializer.data  # This uses your to_representation() method
                    )
                )
                
            except Exception as save_error:
                log_request(f"Error saving profile update for {request.user.email}: {save_error}")
                return Response(
                    api_response(
                        message="Error updating profile. Please try again.",
                        status=False
                    ),
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        else:
            # Return validation errors in your standard format
            log_request(f"Profile update validation failed for {request.user.email}: {serializer.errors}")
            return Response(
                api_response(
                    message="Validation failed",
                    status=False,
                    data={"errors": serializer.errors}
                ),
                status=status.HTTP_400_BAD_REQUEST
            )
    
    
class RequestEmailOTPView(APIView):
    permission_classes = [AllowAny]
    
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
    permission_classes = [AllowAny] 
    
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

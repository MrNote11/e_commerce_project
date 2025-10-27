import threading
from rest_framework import serializers
from .models import UserProfile,UserOTP #, SiteSetting, AccountTier, FinancialTransaction, UserFinancialSummary, BVNVerificationAttempt, BankAccount
from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone
from e_commerce.modules.utils import incoming_request_checks, api_response,log_request,format_phone_number,get_site_details,encrypt_text,decrypt_text,generate_random_otp,get_next_minute
from e_commerce.modules.tmsaas import TMSaaSAPI
from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404 
from e_commerce.modules.exceptions import InvalidRequestException ,raise_serializer_error_msg
from django.contrib.auth.password_validation import validate_password 
from .task import send_verification_email_async
from django.contrib.auth.models import User
import time
from e_commerce.modules.email_utils import send_verification_email
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings



class UserProfileSerializerOut(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    phone_number = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    gender = serializers.SerializerMethodField()

    def get_username(self, obj):
        return obj.user.username
       
    def get_full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"

    def get_phone_number(self, obj):
        if obj.phoneNumber:
            return obj.phoneNumber[3:]
        return None

    def get_email(self, obj):
        return f"{obj.user.email}"
    
    def get_gender(self, obj):
        return obj.gender or None

    class Meta:
        model = UserProfile
        exclude = ["user", "image"]
        depth = 1


class UserSerializerOut(serializers.ModelSerializer):
    
    profilePicture = serializers.SerializerMethodField()
    profileDetail = serializers.SerializerMethodField()
   
    def get_profilePicture(self, obj):
        try:
            if obj.userprofile and obj.userprofile.image:
                request = self.context.get("request")
                return request.build_absolute_uri(obj.userprofile.image.url)
        except:
            pass
        return None

    def get_profileDetail(self, obj):
        try:
            if obj.userprofile:
                return UserProfileSerializerOut(obj.userprofile).data
        except:
            pass
        return None

    class Meta:
        model = User
        exclude = ["is_staff", "is_active", "is_superuser", "password"]
        
        

class LoginSerializerIn(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    def create(self, validated_data):
        email = validated_data.get("email")
        password = validated_data.get("password")

        # Get user by email first
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise InvalidRequestException(
                api_response(message="Invalid email or password", status=False)
            )

        # Authenticate with username and password
        user = authenticate(username=user.username, password=password)
        if not user:
            raise InvalidRequestException(
                api_response(message="Invalid email or password", status=False)
            )
        
        return user


class SignupSerializerIn(serializers.Serializer):
    password = serializers.CharField()
    phoneNo = serializers.CharField(required=False)
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.EmailField()
    gender = serializers.CharField(required=False)

    def create(self, validated_data):
        pword = validated_data.get("password") 
        phone_no = validated_data.get("phoneNo")
        first_name = validated_data.get("first_name")
        last_name = validated_data.get("last_name")
        email = validated_data.get("email")
        gender = validated_data.get("gender")

        # Check if user with this email already exists
        if User.objects.filter(username=email).exists():
            raise InvalidRequestException(
                api_response(message="User with this email already exists", status=False)
            )

        if UserProfile.objects.filter(email=email).exists():
            raise InvalidRequestException(
                api_response(message="Customer with this email already registered", status=False)
            )
        
        # Check if user with this phone number already exists
        if phone_no and UserProfile.objects.filter(phoneNumber=phone_no).exists():
            raise InvalidRequestException(
                api_response(
                    message="Customer with this phone number already registered", status=False
                )
            )

        try:
            validate_password(password=pword)
        except Exception as err:
            log_request(f"Password Validation Error:\nError: {err}")
            raise InvalidRequestException(api_response(message=str(err), status=False))
               
        phone = format_phone_number(phone_no) if phone_no else None

        # Create User but mark as inactive until email verification
        user = User.objects.create_user(
            username=email,
            email=email,
            first_name=first_name,
            last_name=last_name,
            is_active=False  # CRITICAL: User cannot login until verified
        )
        user.set_password(raw_password=pword)
        user.save()

        # Wait for signal to create UserProfile
        max_retries = 5
        user_profile = None
        for i in range(max_retries):
            try:
                user_profile = UserProfile.objects.get(user=user)
                break
            except UserProfile.DoesNotExist:
                if i == max_retries - 1:
                    # Last retry failed, create manually
                    user_profile = UserProfile.objects.create(
                        user=user,
                        email=email
                    )
                    # logger.warning(f"Had to manually create UserProfile for user {user.id}")
                else:
                    time.sleep(0.1)  # Wait 100ms before retry

        # Update profile with additional info
        if user_profile:
            user_profile.gender = gender
            user_profile.phoneNumber = phone
            user_profile.save()

        try:
            request = self.context.get('request')
            
            # Generate verification token
            verification_token = user_profile.generate_verification_token()
            base_url = request.build_absolute_uri('/').rstrip('/')
            verification_url = f"{base_url}/verify-email/?token={verification_token}"
            
            log_request(f"Verification URL: {verification_url}")
            
            # Send verification email SYNCHRONOUSLY (no threading)
            # In production, use Celery instead
            try:
                email_sent = send_verification_email(email, verification_url)
                if email_sent:
                    log_request(f"✅ Verification email sent successfully to {email}")
                else:
                    log_request(f"⚠️ Verification email may have failed for {email}")
            except Exception as email_error:
                log_request(f"❌ Failed to send verification email: {email_error}")
                # Don't fail registration if email fails
                
        except Exception as e:
            log_request(f"Warning: Error in verification email process for user {user.id}: {e}")
        
        return {
            "message": "Registration successful! Please check your email to verify your account.",
            "user_id": user.id,
            "email": email,
            "verification_url": verification_url  # For testing only - remove in production
        }


class RequestEmailOTPSerializerIn(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def create(self, validated_data):
        email = validated_data.get("email")
        
        log_request(f"Creating OTP for email: {email}")
        expiry = get_next_minute(timezone.now(), 15)
        random_otp = generate_random_otp()
        log_request(f"Generated OTP: {random_otp}")
        encrypted_otp = encrypt_text(random_otp)

        user_otp, _ = UserOTP.objects.get_or_create(email=email)
        log_request(f"OTP creation status: {_}")
        user_otp.otp = encrypted_otp
        user_otp.expiry = expiry
        user_otp.save()

        return {
            "otp": random_otp,
            "hint": "data object containing OTP will be removed when email service is fully configured",
        }


class ConfirmOTPSerializerIn(serializers.Serializer):
    otp = serializers.CharField()
    phoneNumber = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)

    def validate(self, data):
        # Either phoneNumber or email must be provided
        if not data.get('phoneNumber') and not data.get('email'):
            raise serializers.ValidationError("Either phoneNumber or email is required")
        return data

    def create(self, validated_data):
        phone_number = validated_data.get("phoneNumber")
        email = validated_data.get("email")
        otp = validated_data.get("otp")

        if phone_number:
            phone = format_phone_number(phone_number)
            try:
                user_otp = UserOTP.objects.get(phoneNumber=phone)
            except UserOTP.DoesNotExist:
                response = api_response(
                    message="Request not valid, please request another OTP", status=False
                )
                raise InvalidRequestException(response)
        elif email:
            try:
                user_otp = UserOTP.objects.get(email=email)
            except UserOTP.DoesNotExist:
                response = api_response(
                    message="Request not valid, please request another OTP", status=False
                )
                raise InvalidRequestException(response)
        else:
            response = api_response(
                message="Either phoneNumber or email is required", status=False
            )
            raise InvalidRequestException(response)

        if otp != decrypt_text(user_otp.otp):
            response = api_response(message="Invalid OTP", status=False)
            raise InvalidRequestException(response)

        # If OTP has expired
        if timezone.now() > user_otp.expiry:
            response = api_response(
                message="OTP has expired, kindly request for another one", status=False
            )
            raise InvalidRequestException(response)

        return {}
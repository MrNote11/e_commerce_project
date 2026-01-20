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
from home.models import User, UserProfile, UserOTP
import time
from e_commerce.modules.email_utils import send_vendor_verification_email, send_verification_email, send_request_email
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
import logging
from django.db import IntegrityError
from django.db import transaction
from vendors.models import VendorProfile

logger = logging.getLogger(__name__)

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
        exclude = ["user", "profile_image", "verification_token", "verification_sent_at", "failed_login_attempts", "locked_until", "last_failed_login"]
        extra_kwargs ={
            'user':{'read_only': True},
            'is_verified': {'read_only': True},
        }
        depth = 1


class UserSerializerOut(serializers.ModelSerializer):
    
    profilePicture = serializers.SerializerMethodField()
    profileDetail = serializers.SerializerMethodField()
   
    def get_profilePicture(self, obj):
        try:
            if obj.userprofile and obj.userprofile.profile_image:
                request = self.context.get("request")
                return request.build_absolute_uri(obj.userprofile.profile_image.url)
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
        request = self.context["request"]
        # Authenticate with username and password
        user = authenticate(username=user.username, password=password)
        if not user:
            raise InvalidRequestException(
                api_response(message="Invalid email or password", status=False)
            )
        return user
        
        
        

logger = logging.getLogger(__name__)

class SignupSerializerIn(serializers.Serializer):
    password = serializers.CharField(write_only=True)
    phoneNo = serializers.CharField(required=False, allow_blank=True)
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.EmailField()
    gender = serializers.CharField(required=False, allow_blank=True)
    role = serializers.ChoiceField(choices=User.Role.choices, required=True)

    def validate_email(self, value):
        """Validate email uniqueness"""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("User with this email already exists")
        if UserProfile.objects.filter(email=value).exists():
            raise serializers.ValidationError("Customer with this email already registered")
        return value

    def validate(self, attrs):
        phone_no = attrs.get('phoneNo')
        
        # Check phone number uniqueness if provided
        if phone_no and UserProfile.objects.filter(phoneNumber=phone_no).exists():
            raise serializers.ValidationError({
                "phoneNo": "Customer with this phone number already registered"
            })
        
        # Validate password
        password = attrs.get('password')
        try:
            validate_password(password=password)
        except Exception as err:
            raise serializers.ValidationError({"password": str(err)})
        
        return attrs

    def create(self, validated_data):
        pword = validated_data.pop("password")
        phone_no = validated_data.pop("phoneNo", None)
        first_name = validated_data.pop("first_name")
        last_name = validated_data.pop("last_name")
        email = validated_data.pop("email")
        gender = validated_data.pop("gender", None)
        role = validated_data.pop("role")

        phone = format_phone_number(phone_no) if phone_no else None

        with transaction.atomic():
            try:
                # Create User
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    is_active=False,
                    role=role,
                    password=pword  # Set password here to avoid extra save
                )
                
                # Wait briefly for signal to create profiles (if using signals)
                # Better approach: create profiles directly
                try:
                    user_profile = UserProfile.objects.get(user=user)
                except UserProfile.DoesNotExist:
                        return{"profile doesnt exists"}
                
                vendor_profile = None
                if user.role == User.Role.VENDOR:
                    try:
                        vendor_profile = VendorProfile.objects.get(user=user)
                    except VendorProfile.DoesNotExist:
                        # If signal didn't create it, create it manually
                        return {"vendorprofile doesnt exists"}
                
                # Update profile with additional info
                user_profile.gender = gender
                user_profile.phoneNumber = phone
                user_profile.save()
                
                if vendor_profile:
                    vendor_profile.contact_phone = phone
                    vendor_profile.contact_email = email
                    vendor_profile.save()

            except IntegrityError as e:
                logger.error(f"Integrity error during user creation: {e}")
                raise serializers.ValidationError("User creation failed due to database constraint")
            except Exception as e:
                logger.error(f"Error during user creation: {e}")
                raise serializers.ValidationError(f"User creation failed: {str(e)}")

        # Send verification emails
        try:
            request = self.context.get('request')
            
            # Generate verification tokens
            verification_token = user_profile.generate_verification_token()
            verification_token_vendor = vendor_profile.generate_vendor_verification_token() if vendor_profile else None
            
            base_url = request.build_absolute_uri('/').rstrip('/')
            verification_url = f"{base_url}/verify-email/?token={verification_token}" 
            verification_url_vendor = f"{base_url}/verify-email/?token={verification_token_vendor}" if verification_token_vendor else None

            logger.info(f"Verification URL: {verification_url}")
            
            # Send appropriate email based on role
            if user.role == User.Role.VENDOR:
                send_vendor_verification_email(email, verification_url_vendor)
                logger.info(f"Vendor verification email sent successfully to {email}")
                return {
                    "approval": "Email approval shall be sent within a day",
                    "email": email,
                    "role": user.role,
                }
                
            else:    
                send_verification_email(email, verification_url)
                logger.info(f"Verification email sent successfully to {email}")
                
        except Exception as e:
            logger.error(f"Error in verification email process for user {user.id}: {e}")
            # Registration succeeded but email failed
        return {
                "message": "verification Email send...",
                "user_id": user.id,
                "email": email,
                "role": user.role,
                "verification_token": verification_url,
        }
   

class RequestEmailOTPSerializerIn(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def create(self, validated_data):
        email = validated_data.get("email")
        
        user =User.objects.get(email=email)  # Ensure user exists; will raise if not
        
        if not user:
            raise InvalidRequestException(
                api_response(message="User with this email does not exist", status=False)
            )
        log_request(f"Creating OTP for email: {email}")
        expiry = get_next_minute(timezone.now(), 15)
        random_otp = generate_random_otp()
        log_request(f"Generated OTP: {random_otp}")
        encrypted_otp = encrypt_text(random_otp)

        user_otp, _ = UserOTP.objects.get_or_create(email=email)
        log_request(f"OTP creation status: {_}")
        user_otp.otp = encrypted_otp
        user_otp.expiry = expiry
        user_otp.is_verified = True
        user_otp.save()
        send_request_email(email, random_otp)

        return {
            "otp": random_otp,
            "hint": "data object containing OTP will be removed when email service is fully configured",
        }


# serializers.py
class UpdateProfileSerializer(serializers.ModelSerializer):
    # User model fields - for updating User table
    email = serializers.EmailField(source='user.email', required=False)
    first_name = serializers.CharField(source='user.first_name', required=False)
    last_name = serializers.CharField(source='user.last_name', required=False)
    username = serializers.CharField(source='user.username', required=False)
    
    # UserProfile fields - for updating UserProfile table
    profile_image = serializers.ImageField(required=False)

    class Meta:
        model = UserProfile
        fields = [
            # User fields
            'email', 'first_name', 'last_name', 'username',
            # UserProfile fields  
            'profile_image', 'otherName', 'gender', 'dob',
            'phoneNumber', 'address', 'city', 'state', 'country'
        ]
        extra_kwargs = {
            'user':{'read_only': True},
            'is_verified': {'read_only': True},
        }

    def update(self, instance, validated_data):
        """
        Update both User and UserProfile models
        """
        print(f"Starting profile update for: {instance.user.username}")
        
        # Extract user data from validated_data
        user_data = validated_data.pop('user', {})
        print(f"User data to update: {user_data}")
        print(f"Profile data to update: {validated_data}")
        
        with transaction.atomic():
            # Update User model first
            if user_data:
                user = instance.user
                for attr, value in user_data.items():
                    setattr(user, attr, value)
                    print(f"Setting user.{attr} = {value}")
                user.save()
                print(f"User updated: {user.username} ({user.email})")
            
            # Update UserProfile model
            instance = super().update(instance, validated_data)
            print(f"Profile updated successfully")
        
        return instance

    def to_representation(self, instance):
        """
        Return formatted output using your existing serializer
        """
        data = UserProfileSerializerOut(instance, context=self.context).data    
        return {
            "details":data,
            "profilePicture": instance.profile_image.url
        }

class ConfirmOTPSerializerIn(serializers.Serializer):
    otp = serializers.CharField()
    email = serializers.EmailField()

    def validate(self, data):
        # Both are required to check OTP
        if not data.get("otp"):
            raise serializers.ValidationError("OTP is required.")
        if not data.get("email"):
            raise serializers.ValidationError("Email is required.")
        return data

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this email does not exist.")
        return value

    def create(self, validated_data):
        email = validated_data["email"]
        otp = validated_data["otp"]

        user = User.objects.filter(email=email).first()

        user_otp = UserOTP.objects.filter(email=email).first()
        if not user_otp:
            raise InvalidRequestException(
                api_response("Request not valid, please request another OTP", False)
            )

        if otp != decrypt_text(user_otp.otp):
            raise InvalidRequestException(
                api_response("Invalid OTP", False)
            )

        if timezone.now() > user_otp.expiry:
            raise InvalidRequestException(
                api_response("OTP expired, request a new one", False)
            )

        return {}

class ChangePasswordSerializerIn(serializers.Serializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    currentPassword = serializers.CharField()
    newPassword = serializers.CharField()

    def create(self, validated_data):
        request = self.context.get('request')
        user = validated_data["user"] = request.user
        old_password = validated_data.get("currentPassword")
        new_password = validated_data.get("newPassword")

        if not check_password(password=old_password, encoded=user.password):
            raise InvalidRequestException(
                api_response(message="Incorrect old password", status=False)
            )

        try:
            validate_password(password=new_password)
        except Exception as err:
            log_request(f"Password Validation Error:\nError: {err}")
            raise InvalidRequestException(api_response(message=err, status=False))

        if old_password == new_password:
            raise InvalidRequestException(
                api_response(message="Passwords cannot be same", status=False)
            )

        user.password = make_password(password=new_password)
        user.save()

        return "Password Change Successful"


class ForgetPasswordSerializerIn(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField()
    password = serializers.CharField()

    def create(self, validated_data):
        email = validated_data.get("email")
        otp = validated_data.get("otp")
        new_password = validated_data.get("password")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise InvalidRequestException(
                api_response(message="User not found", status=False)
            )

        try:
            validate_password(password=new_password)
        except Exception as err:
            log_request(f"Password Validation Error:\nError: {err}")
            raise InvalidRequestException(api_response(message=err, status=False))

        try:
            user_otp = UserOTP.objects.get(email=user.email)
        except UserOTP.DoesNotExist:
            raise InvalidRequestException(
                api_response(message="OTP request is required", status=False)
            )

        if timezone.now() > user_otp.expiry:
            raise InvalidRequestException(
                api_response(message="OTP is expired", status=False)
            )

        decrypted_otp = decrypt_text(user_otp.otp)
        if str(decrypted_otp) != str(otp):
            raise InvalidRequestException(
                api_response(message="You have submitted an invalid OTP", status=False)
            )

        user.password = make_password(password=new_password)
        user.save()
        user_otp.delete()
        
        return "Password Reset Successful"

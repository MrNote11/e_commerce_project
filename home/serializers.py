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
# from withdrawals.payment_gateway import PaymentGateway, PaymentGatewayError
from e_commerce.modules.email_utils import send_welcome_email_threaded, send_verification_email
   # Import the email function
from e_commerce.modules.email_utils import send_verification_email
from django.contrib.auth.models import User

class UserProfileSerializerOut(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    phone_number = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    gender = serializers.SerializerMethodField()
    # current_tier = serializers.SerializerMethodField()
    # all_tier_details = serializers.SerializerMethodField()

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
    
    # def get_current_tier(self,obj):
    #     return {
    #         "tier": obj.tier.tier,
    #         "depositLimit": obj.tier.depositLimit,
    #         "withdrawalLimit": obj.tier.withdrawalLimit
    #     }
    
    # def get_all_tier_details(self,obj):
    #     tier_details = []
    #     tiers = obj.tier.objects.all()
    #     for tier in tiers:
    #         tier_name = tier.tier
    #         tier_withdrawal = tier.withdrawalLimit
    #         tier_deposit = tier.depositLimit
    #         tier_details.append({
    #             "tier": tier_name,
    #             "withdrawalLimit": tier_withdrawal,
    #             "depositLimit": tier_deposit
    #         })
    #     return tier_details

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


# serializers.py
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
            raise InvalidRequestException(api_response(message=err, status=False))
               
        phone = format_phone_number(phone_no) if phone_no else None

        # Create User but mark as inactive
        user = User.objects.create_user(
            username=email,
            email=email,
            first_name=first_name,
            last_name=last_name,
            is_active=False  # User cannot login until verified
        )
        user.set_password(raw_password=pword)
        user.save()

        # Create UserProfile
        user_profile = UserProfile.objects.create(
            user=user,      
            gender=gender,
            phoneNumber=phone,
            email=email 
        )
        try:
            request = self.context.get('request')
            # Generate verification token and send email
            verification_token = user_profile.generate_verification_token()
            verification_url = f"{request.build_absolute_uri('/')}verify-email/?token={verification_token}"
            send_verification_email(user.id, user.email, verification_url)
            print(f"verification url: {verification_url}")
            log_request(f"Verification email queued for user {user.id} ({email})")
        except Exception as email_error:
            log_request(f"Warning: Failed to queue verification email for user {user.id}: {email_error}")
        return {
            "message": "Registration successful! Please check your email to verify your account.",
            "user_id": user.id,
            "email": email
        }

       
            
# class RequestOTPSerializerIn(serializers.Serializer):
#     phone_number = serializers.CharField(required=True)

#     def create(self, validated_data):
#         phone_number = validated_data.get("phone_number")
      
        
#         phone_no = format_phone_number(phone_number)
#         log_request(f"Creating OTP for phone number: {phone_no}")
#         expiry = get_next_minute(timezone.now(), 15)
#         random_otp = generate_random_otp()
#         log_request(random_otp)
#         encrypted_otp = encrypt_text(random_otp)

#         user_otp, _ = UserOTP.objects.get_or_create(phoneNumber=phone_no)
#         log_request(f"OTP creation status: {_}")
#         user_otp.otp = encrypted_otp
#         user_otp.expiry = expiry
#         user_otp.save()

#         # Send OTP to user
#         # Thread(target=send_token_to_email, args=[user_detail]).start()
#         # Send via TMSaaS

#         bank = get_site_details()

#         # new_content = f"Dear {first_name},Your password reset token is {random_otp}. It expires in 10 minutes."
#         # log_request(new_content)

#         # TMSaaSAPI.send_tmsaas_sms(bank,new_content,phone_no,log_sms_response_to_server)

#         # Thread(target=send_tmsaas_sms, args=[bank, new_content, phone_number, log_sms_response_to_server]).start()

#         return {
#             "otp": random_otp,
#             "hint": "data object containing OTP will be removed when sms service start working",
#         }




class RequestEmailOTPSerializerIn(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def create(self, validated_data):
        email = validated_data.get("email")
        
        log_request(f"Creating OTP for email: {email}")
        expiry = get_next_minute(timezone.now(), 15)
        random_otp = generate_random_otp()
        log_request(random_otp)
        encrypted_otp = encrypt_text(random_otp)

        user_otp, _ = UserOTP.objects.get_or_create(email=email)
        log_request(f"OTP creation status: {_}")
        user_otp.otp = encrypted_otp
        user_otp.expiry = expiry
        user_otp.save()

        # Send OTP to user's email
        # This will be implemented later
        # For now, we just return the OTP in the response

        return {
            "otp": random_otp,
            "hint": "data object containing OTP will be removed when email service starts working",
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


class ChangePasswordSerializerIn(serializers.Serializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    currentPassword = serializers.CharField()
    newPassword = serializers.CharField()

    def create(self, validated_data):
        user = validated_data.get("user")
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
            user_otp = UserOTP.objects.get(phoneNumber=user.userprofile.phoneNumber)
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
        
        return "Password Reset Successful"


class NewUserProfileSerializer(serializers.ModelSerializer):
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    class Meta:
        model = UserProfile
        fields = ["otherName", "gender", "dob", "phoneNumber","nin", "address","first_name", "last_name","full_name"]

    def get_first_name(self,obj):
        return obj.user.first_name
    
    def get_last_name(self,obj):
        return obj.user.last_name
    
    def get_full_name(self,obj):
        return f"{obj.user.first_name} {obj.user.last_name}"

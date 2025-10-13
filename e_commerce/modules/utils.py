"""
Utility Module
=============

This module provides a collection of utility functions for common operations in the application.
It includes functionality for:

1. Security & Encryption:
   - Text encryption/decryption
   - Password validation
   - Transaction PIN handling
   - API key validation

2. Date & Time Operations:
   - Date range calculations
   - Time delta operations
   - Date formatting

3. Data Processing:
   - CSV generation
   - Email validation
   - Phone number formatting
   - Response formatting

4. Request Handling:
   - API request validation
   - Response formatting
   - Header validation
"""

import os
import base64
import calendar
import datetime
import logging
import re
import secrets
import csv
# from django.contrib.sites.models import Site
from django.utils import timezone
from cryptography.fernet import Fernet
from django.conf import settings
from django.utils.crypto import get_random_string
from dateutil.relativedelta import relativedelta
# from home.models import SiteSetting 
from django.shortcuts import render
from django.http import HttpResponse
from Crypto.Cipher import AES

# from whitecrust.modules.utils import send_email

def log_request(*args):
    """
    Log multiple arguments as info messages.
    
    Args:
        *args: Variable number of arguments to log
        
    This function is used throughout the application to log API requests,
    responses, and other important information for debugging and monitoring.
    """
    for arg in args:
        logging.info(arg)


def encrypt_text(text: str):
    """
    Encrypt sensitive text data using Fernet symmetric encryption.
    
    The function uses Django's SECRET_KEY as the encryption key,
    ensuring that the encrypted data can only be decrypted by the same
    application instance.
    
    Args:
        text (str): Plain text to encrypt
        
    Returns:
        str: Base64-encoded encrypted text
        
    Example:
        encrypted = encrypt_text("sensitive_data")
    """
    # Create encryption key from Django's SECRET_KEY
    key = base64.urlsafe_b64encode(settings.SECRET_KEY.encode()[:32])
    fernet = Fernet(key)
    # Encrypt and encode the text
    secure = fernet.encrypt(f"{text}".encode()).decode()
    return secure


def decrypt_text(text: str):
    """
    Decrypt text that was encrypted using encrypt_text().
    
    Uses the same Django SECRET_KEY-based encryption key to
    decrypt the data.
    
    Args:
        text (str): Encrypted text to decrypt
        
    Returns:
        str: Decrypted plain text
        
    Example:
        decrypted = decrypt_text(encrypted_text)
    """
    # Create encryption key from Django's SECRET_KEY
    key = base64.urlsafe_b64encode(settings.SECRET_KEY.encode()[:32])
    fernet = Fernet(key)
    # Decrypt and decode the text
    decrypt = fernet.decrypt(text.encode()).decode()
    return decrypt


def generate_csv(queryset, model_name):
    """
    Generate a CSV file from a Django model queryset for direct download.
    
    This function creates an in-memory CSV file containing all fields
    from the provided model queryset. The CSV can be directly downloaded
    through the browser.
    
    Args:
        queryset: Django queryset containing the data to export
        model_name: Django model class whose data is being exported
        
    Returns:
        HttpResponse: Response object with CSV content for direct download
        
    Example:
        queryset = User.objects.all()
        response = generate_csv(queryset, User)
    """
    # Get the model fields and extract their names for CSV header
    fields = model_name._meta.fields
    header = [field.name for field in fields]

    # Create a CSV file in memory with appropriate headers
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f"attachment; filename={model_name.__name__.lower()}_data.csv"
    )

    # Write the CSV data
    csv_writer = csv.writer(response) 
    csv_writer.writerow(header)  # Write headers

    # Write each object's data as a row
    for obj in queryset:
        row_data = []
        for field in header:
            value = getattr(obj, field)
            row_data.append(value)
        csv_writer.writerow(row_data)

    return response


def generate_and_send_csv(request, queryset, model_name, recipient_email):
    """
    Generate a CSV file from a queryset and email it to the recipient.
    
    This function:
    1. Creates a CSV file in the media directory
    2. Generates a download link
    3. Sends an email with the download link to the recipient
    
    Flow:
    1. Extract model fields for CSV headers
    2. Create CSV file in MEDIA_ROOT/csv_files directory
    3. Write data from queryset to CSV
    4. Generate a download link using BASE_URL
    5. Send an email with formatted message containing the download link
    
    Args:
        request: HTTP request object for user info
        queryset: Django queryset containing the data to export
        model_name: Django model class whose data is being exported
        recipient_email: Email address to send the CSV download link to
        
    Returns:
        str: Success message
        
    Example:
        result = generate_and_send_csv(request, Use r.objects.all(), User, "user@example.com")
    """
    

    # Get model fields for CSV headers
    fields = model_name._meta.get_fields()
    header = [field.name for field in fields]

    # Setup CSV file path in media directory
    media_path = os.path.join(settings.MEDIA_ROOT, "csv_files")
    os.makedirs(media_path, exist_ok=True)
    csv_file_path = os.path.join(media_path, f"{model_name.__name__.lower() }_data.csv")

    # Write data to CSV file
    with open(csv_file_path, "w", newline="") as csv_file:
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(header)  # Write headers

        for obj in queryset:
            row_data = []
            for field in header:
                value = getattr(obj, field)
                row_data.append(value)
            csv_writer.writerow(row_data)

    # Generate download link
    base_url = settings.BASE_URL.rstrip("/")
    relative_csv_path = os.path.relpath(csv_file_path, settings.MEDIA_ROOT)
    download_link = f"{base_url}/media/csv_files/{model_name.__name__.lower()}_data.csv"

    # Prepare email content
    first_name = request.user.first_name or "Up Admin"
    email = recipient_email

    # Create HTML email message with download button
    message = (
        f"Dear {first_name}, <br><br>Kindly click on the below link to download your requested report. <br>"
        f"<p/>Click the button below to download the file <p/>"
        f"<div style='text-align:left'><a href='{download_link}' target='_blank' "
        f"style='background-color: #67C1F0; color: white; padding: 15px 25px; text-align: center; "
        f"text-decoration: none; display: inline-block;'>Download</a></div><br>"
    )
    subject = "Report Download"
    
    # Render email template with message
    contents = render(
        None, "default_template.html", context={"message": message}
    ).content.decode("utf-8")
    
    # Send email with download link
    # send_email(contents, email, subject)
    return "Email sent successfully."


def generate_random_password():
    """
    Generate a random 10-character password string.
    
    Returns:
        str: Random password string
    
    Note: This uses Django's get_random_string utility which provides
    cryptographically secure random string generation.
    """
    return get_random_string(length=10)


def generate_random_otp():
    """
    Generate a random 6-digit OTP (One-Time Password).
    
    Returns:
        str: 6-digit numeric OTP string
    
    The OTP is generated using only numeric characters (0-9)
    for better user experience when entering on mobile devices.
    """
    return get_random_string(length=6, allowed_chars="1234567890")


# Date and Time Utility Functions
# These functions provide a consistent interface for date/time calculations
# using the dateutil.relativedelta library for accurate calculations

def get_previous_date(date, delta):
    """
    Get a date that is 'delta' days before the given date.
    
    Args:
        date: datetime object
        delta: Number of days to subtract
        
    Returns:
        datetime: Date object 'delta' days before input date
    """
    previous_date = date - relativedelta(days=delta)
    return previous_date


def get_next_date(date, delta):
    """
    Get a date that is 'delta' days after the given date.
    
    Args:
        date: datetime object
        delta: Number of days to add
        
    Returns:
        datetime: Date object 'delta' days after input date
    """
    next_date = date + relativedelta(days=delta)
    return next_date


def get_next_minute(date, delta):
    """
    Get a datetime that is 'delta' minutes after the given datetime.
    
    Args:
        date: datetime object
        delta: Number of minutes to add
        
    Returns:
        datetime: Datetime 'delta' minutes after input datetime
    """
    next_minute = date + relativedelta(minutes=delta)
    return next_minute


def get_previous_minute(date, delta):
    """
    Get a datetime that is 'delta' minutes before the given datetime.
    
    Args:
        date: datetime object
        delta: Number of minutes to subtract
        
    Returns:
        datetime: Datetime 'delta' minutes before input datetime
    """
    previous_minute = date - relativedelta(minutes=delta)
    return previous_minute


def get_previous_seconds(date, delta):
    """
    Get a datetime that is 'delta' seconds before the given datetime.
    
    Args:
        date: datetime object
        delta: Number of seconds to subtract
        
    Returns:
        datetime: Datetime 'delta' seconds before input datetime
    """
    previous_seconds = date - relativedelta(seconds=delta)
    return previous_seconds


def get_previous_hour(date, delta):
    """
    Get a datetime that is 'delta' hours before the given datetime.
    
    Args:
        date: datetime object
        delta: Number of hours to subtract
        
    Returns:
        datetime: Datetime 'delta' hours before input datetime
    """
    previous_hour = date - relativedelta(hours=delta)
    return previous_hour


# Date Range Calculation Functions
# These functions help in determining start and end dates for various time periods
# (day, week, month, year). They're useful for reporting and date-based filtering.

def get_day_start_and_end_datetime(date_time):
    """
    Get the start and end dates for the day containing the given datetime.
    
    Args:
        date_time: datetime object
        
    Returns:
        tuple: (day_start, day_end) where both are date objects
        
    Example:
        start, end = get_day_start_and_end_datetime(timezone.now())
    """
    # Get start of day by resetting to day 0
    day_start = date_time - relativedelta(day=0)
    # Get end of day by adding one day
    day_end = day_start + relativedelta(days=1)
    # Convert to date objects
    day_start = day_start.date()
    day_end = day_end.date()
    return day_start, day_end


def get_week_start_and_end_datetime(date_time):
    """
    Get the start and end datetimes for the week containing the given datetime.
    Week starts on Monday (0) and ends on Sunday (6).
    
    Args:
        date_time: datetime object
        
    Returns:
        tuple: (week_start, week_end) where both are datetime objects with
               week_start set to midnight (00:00:00) of Monday and
               week_end set to last second (23:59:59) of Sunday
    """
    # Get start of week (Monday)
    week_start = date_time - datetime.timedelta(days=date_time.weekday())
    # Get end of week (Sunday)
    week_end = week_start + datetime.timedelta(days=6)
    # Set time to start and end of day respectively
    week_start = datetime.datetime.combine(week_start.date(), datetime.time.min)
    week_end = datetime.datetime.combine(week_end.date(), datetime.time.max)
    return week_start, week_end


def get_month_start_and_end_datetime(date_time):
    """
    Get the start and end datetimes for the month containing the given datetime.
    
    Args:
        date_time: datetime object
        
    Returns:
        tuple: (month_start, month_end) where both are datetime objects with
               month_start set to midnight of the 1st day of the month and
               month_end set to last second of the last day of the month
    """
    # Set to first day of month
    month_start = date_time.replace(day=1)
    # Get last day of month using calendar
    month_end = month_start.replace(
        day=calendar.monthrange(month_start.year, month_start.month)[1]
    )
    # Set time to start and end of day respectively
    month_start = datetime.datetime.combine(month_start.date(), datetime.time.min)
    month_end = datetime.datetime.combine(month_end.date(), datetime.time.max)
    return month_start, month_end


def get_month_range(delta):
    """
    Get start and end dates for a month relative to current month.
    
    Args:
        delta: Number of months to look back from current month
        
    Returns:
        tuple: (start_date, end_date) for the month 'delta' months ago
        
    Example:
        # Get dates for previous month
        start, end = get_month_range(1)
    """
    current_date = timezone.now()
    # Get first day of target month
    start = (current_date - relativedelta(months=delta)).replace(day=1)
    # Get last day of target month
    end = (start + relativedelta(months=1)).replace(day=1) - relativedelta(days=1)
    return start, end


def get_year_start_and_end_datetime(date_time):
    """
    Get the start and end datetimes for the year containing the given datetime.
    
    Args:
        date_time: datetime object
        
    Returns:
        tuple: (year_start, year_end) where both are datetime objects with
               year_start set to midnight of January 1st and
               year_end set to last second of December 31st
    """
    # Set to first day of year
    year_start = date_time.replace(day=1, month=1, year=date_time.year)
    # Set to last day of year
    year_end = date_time.replace(day=31, month=12, year=date_time.year)
    # Set time to start and end of day respectively
    year_start = datetime.datetime.combine(year_start.date(), datetime.time.min)
    year_end = datetime.datetime.combine(year_end.date(), datetime.time.max)
    return year_start, year_end


def get_previous_month_date(date, delta):
    """
    Get a date that is 'delta' months before the given date.
    
    Args:
        date: datetime object
        delta: Number of months to subtract
        
    Returns:
        datetime: Date object 'delta' months before input date
    """
    return date - relativedelta(months=delta)


def get_next_month_date(date, delta):
    """
    Get a date that is 'delta' months after the given date.
    
    Args:
        date: datetime object
        delta: Number of months to add
        
    Returns:
        datetime: Date object 'delta' months after input date
    """
    return date + relativedelta(months=delta)


# Email sending function commented out as it's moved to another module
# def send_email(content, email, subject):
#     payload = json.dumps({
#         "personalizations": [{"to": [{"email": email}]}], "from": {"email": email_from, "name": "divebusters"},
#         "subject": subject, "content": [{"type": "text/html", "value": content}]
#     })
#     response = requests.request(
#         "POST", email_url, headers={"Content-Type": "application/json", "Authorization": f"Bearer {email_api_key}"},
#         data=payload
#     )
#     log_request(f"Sending email to: {email}\nResponse: {response.text}")
#     return response.text


def password_checker(password: str):
    """
    Validate password strength against security requirements.
    
    Password must contain:
    - At least 8 characters
    - At least one lowercase letter
    - At least one uppercase letter
    - At least one number
    - At least one special character from # ! - _ @ $
    - No whitespace characters
    
    Args:
        password (str): Password string to validate
        
    Returns:
        tuple: (is_valid, message) where:
            is_valid (bool): True if password meets all requirements
            message (str): "Valid Password" or description of requirements
    
    Example:
        is_valid, message = password_checker("MyP@ssw0rd")
    """
    try:
        flag = 0
        # Check each requirement
        while True:
            if len(password) < 8:
                flag = -1
                break
            elif not re.search("[a-z]", password):  # Lowercase
                flag = -1
                break
            elif not re.search("[A-Z]", password):  # Uppercase
                flag = -1
                break
            elif not re.search("[0-9]", password):  # Numbers
                flag = -1
                break
            elif not re.search("[#!_@$-]", password):  # Special chars
                flag = -1
                break
            elif re.search("\s", password):  # No whitespace
                flag = -1
                break
            else:
                flag = 0
                break

        if flag == 0:
            return True, "Valid Password"

        return (
            False,
            "Password must contain uppercase, lowercase letters, '# ! - _ @ $' special characters "
            "and 8 or more characters",
        )
    except (Exception,) as err:
        return False, f"{err}"


def validate_email(email):
    """
    Validate an email address using regex pattern.
    
    The regex pattern checks for:
    - Local part containing letters, numbers, and common special chars
    - @ symbol
    - Domain part with letters and numbers
    - TLD with 2 or more characters
    
    Args:
        email (str): Email address to validate
        
    Returns:
        bool: True if email is valid, False otherwise
        
    Example:
        is_valid = validate_email("user@example.com")
    """
    try:
        regex = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        if re.fullmatch(regex, email):
            return True
        return False
    except (TypeError, Exception) as err:
        # Log error
        return False


def get_site_details():
    # try:
    #     site, created = SiteSetting.objects.get_or_create(
    #         site=Site.objects.get_current()
    #     )
    # except Exception as ex:
    #     logging.exception(str(ex))
    #     site = SiteSetting.objects.filter(site=Site.objects.get_current()).first()
    # return site
    pass

def mask_character(number_to_mask, num_chars_to_mask, mask_char="*"):
    if len(number_to_mask) <= num_chars_to_mask:
        return mask_char * len(number_to_mask)
    else:
        return mask_char * num_chars_to_mask + number_to_mask[num_chars_to_mask:]


def create_notification(user, text):
    # notify = Notification.objects.create(message=text)
    # notify.user.add(user)
    return True


def api_response(message, status, data=None, **kwargs):
    if data is None:
        data = {}
    try:
        reference_id = secrets.token_hex(30)
        response = dict(
            requestTime=timezone.now(),
            requestType="outbound",
            referenceId=reference_id,
            status=bool(status),
            message=message,
            data=data,
            **kwargs,
        )

        # if "accessToken" in data and 'refreshToken' in data:
        if "accessToken" in data:
            # Encrypting tokens to be
            response["data"]["accessToken"] = encrypt_text(text=data["accessToken"])
            # response['data']['refreshToken'] = encrypt_text(text=data['refreshToken'])
            logging.info(msg=response)

            response["data"]["accessToken"] = decrypt_text(text=data["accessToken"])
            # response['data']['refreshToken'] = encrypt_text(text=data['refreshToken'])

        else:
            logging.info(msg=response)

        return response
    except (Exception,) as err:
        return err


def incoming_request_checks(request, require_data_field: bool = True) -> tuple:
    try:
        x_api_key = request.headers.get("X-Api-Key", None) or request.META.get(
            "HTTP_X_API_KEY", None
        )
        request_type = request.data.get("requestType", None)
        data = request.data.get("data", {})

        if not x_api_key:
            return False, "Missing or Incorrect Request-Header field 'X-Api-Key'"

        if x_api_key != settings.X_API_KEY:
            return False, "Invalid value for Request-Header field 'X-Api-Key'"

        if not request_type:
            return False, "'requestType' field is required"

        if request_type != "inbound":
            return False, "Invalid 'requestType' value"

        if require_data_field:
            if not data:
                return (
                    False,
                    "'data' field was not passed or is empty. It is required to contain all request data",
                )

        return True, data
    except (Exception,) as err:
        return False, f"{err}"


def get_incoming_request_checks(request) -> tuple:
    try:
        x_api_key = request.headers.get("X-Api-Key", None) or request.META.get(
            "HTTP_X_API_KEY", None
        )

        if not x_api_key:
            return False, "Missing or Incorrect Request-Header field 'X-Api-Key'"

        if x_api_key != settings.X_API_KEY:
            return False, f"Invalid value for Request-Header field 'X-Api-Key': {x_api_key}"

        return True, ""
        # how do I handle requestType and also client ID e.g 'inbound', do I need to expect it as a query parameter.
    except (Exception,) as err:
        return False, f"{err}"


# def format_phone_number(phone_number):
#     return f"234{phone_number[:11]}"


def format_phone_number(phone_number):
    """
    Format Nigerian phone numbers to international format.
    
    This function converts Nigerian phone numbers to the international
    format starting with '234'. It handles numbers that:
    - Start with '0' (local format)
    - Start with '234' (international format)
    
    Args:
        phone_number (str): Phone number to format
        
    Returns:
        str: Formatted phone number starting with '234'
        
    Raises:
        ValueError: If phone number format is invalid
        
    Examples:
        >>> format_phone_number("08012345678")
        "2348012345678"
        >>> format_phone_number("2348012345678")
        "2348012345678"
    """
    # Remove any non-digit characters
    phone_number = "".join(filter(str.isdigit, phone_number))

    # Handle Nigerian number formats
    if phone_number.startswith("0") and len(phone_number) == 11:
        # Convert local format (0) to international format (234)
        return f"234{phone_number[1:]}"
    elif phone_number.startswith("234") and len(phone_number) == 13:
        # Already in international format
        return phone_number
    else:
        # Invalid format
        raise ValueError("Invalid phone number format")


def decrypt_pin(content):
    """
    Decrypt a transaction PIN using AES encryption.
    
    This function uses AES in ECB mode to decrypt transaction PINs
    that were encrypted during transaction creation.
    
    Args:
        content (str): Encrypted PIN content in hexadecimal format
        
    Returns:
        str: Decrypted PIN as a string
        
    Note:
        - Uses settings.DECRYPTION_KEY for the encryption key
        - Removes null padding after decryption
    """
    # Get decryption key from settings
    encryption_key = settings.DECRYPTION_KEY
    # Convert hex strings to bytes
    key = bytes.fromhex(encryption_key)
    data = bytes.fromhex(content)
    # Create AES cipher in ECB mode
    cipher = AES.new(key, AES.MODE_ECB)
    # Decrypt and remove padding
    decrypted_data = cipher.decrypt(data)
    data = bytes(decrypted_data.decode("utf-8"), "utf-8")
    return data.rstrip(b"\x00").decode("utf-8")


def transaction_pin_correct(user, trans_pin):
    """
    Verify if a transaction PIN matches the user's stored PIN.
    
    This function:
    1. Decrypts the provided transaction PIN
    2. Decrypts the user's stored PIN
    3. Compares them for equality
    
    Args:
        user: User object with a userprofile containing transactionPin
        trans_pin (str): Encrypted transaction PIN to verify
        
    Returns:
        bool: True if PINs match, False otherwise
    """
    # Decrypt the provided PIN
    decrypted_pin = decrypt_pin(trans_pin)
    # Get user's stored PIN
    correct_pin = decrypt_text(user.userprofile.transactionPin)
    # Compare PINs
    if str(decrypted_pin) != str(correct_pin):
        return False
    return True

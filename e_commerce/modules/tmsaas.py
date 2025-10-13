"""
TMSaaS (Transaction Management Software as a Service) API Client
This module provides a comprehensive interface to interact with various TMSaaS services including:
- Bill payments and utilities (airtime, data, electricity, etc.)
- Insurance services (vehicle, health, gadget)
- SMS services
- Customer verification
- Wallet management
"""

import json
import requests
from e_commerce.modules.utils import decrypt_text, log_request, get_site_details

# Initialize bank details from site configuration
bank = get_site_details()


class TMSaaSAPI:
    """
    A class that provides methods to interact with the TMSaaS API endpoints.
    All methods are class methods to allow for stateless API interactions.
    """

    @classmethod
    def get_header(cls):
        """
        Constructs the authorization header required for TMSaaS API requests.
        
        Returns:
            dict: A dictionary containing the client-id header required for authentication
        """
        header = {
            # "client-id": decrypt_text(bank.tmsaasKey)
            "client-id": bank.tmsaasKey
        }
        return header

    @classmethod
    def get_base_url(cls):
        """
        Retrieves the base URL for the TMSaaS API from bank configuration.
        
        Returns:
            str: The base URL for all TMSaaS API endpoints
        """
        url = str(bank.tmsaasBaseUrl)
        return url

    @classmethod
    def get_networks(cls):
        """
        Retrieves a list of available mobile network operators for bill payments.
        Uses the creditswitch provider for network information.
        
        Returns:
            dict: JSON response containing available mobile networks
        """
        url = cls.get_base_url() + "/data/creditswitch/networks"
        header = cls.get_header()
        log_request(f"GET Bill Payment Networks Request:\nurl: {url}\nheader: {header}")
        response = requests.request("GET", url=url, headers=header)
        log_request(f"GET Bill Payment Networks Response:\nresponse: {response.text}")
        return response.json()

    @classmethod
    def get_data_plan(cls, network_name):
        """
        Retrieves available data plans for a specific mobile network operator.
        
        Args:
            network_name (str): The name of the mobile network operator (e.g., MTN, Airtel, etc.)
            
        Returns:
            dict: JSON response containing available data plans for the specified network
        """
        url = cls.get_base_url() + f"/data/plans?provider=creditswitch&network={network_name}"
        header = cls.get_header()
        log_request(f"GET Data Plan(s) Request:\nurl: {url}\nheader: {header}")
        response = requests.request("GET", url=url, headers=header)
        log_request(f"GET Data Plan(s) Response:\nresponse: {response.text}")
        return response.json()

    @classmethod
    def purchase_airtime(cls, **kwargs):
        """
        Purchase airtime for a mobile number through the creditswitch provider.
        
        Args:
            **kwargs: Keyword arguments containing:
                phone_number (str): The recipient's phone number
                network (str): Mobile network operator name
                amount (float/str): Amount of airtime to purchase
                
        Returns:
            dict: JSON response containing the transaction result
        """
        url = cls.get_base_url() + "/airtime"
        header = cls.get_header()
        payload = dict()
        payload["provider"] = "creditswitch"
        payload["phoneNumber"] = kwargs.get("phone_number")
        payload["network"] = kwargs.get("network")
        payload["amount"] = kwargs.get("amount")
        log_request(f"Purchase Airtime Request:\nurl: {url}\nheader: {header}\npayload: {payload}")
        response = requests.request("POST", url=url, headers=header, data=payload)
        log_request(f"Purchase Airtime Response:\nresponse: {response.text}")
        return response.json()

    @classmethod
    def vend_betting(cls, **kwargs):
        """
        Process betting transactions through the creditswitch provider.
        
        Args:
            **kwargs: Keyword arguments containing:
                provider (str): The betting service provider
                customer_id (str): Customer's ID with the betting provider
                name (str): Customer's name
                service_id (str): Service identifier
                amount (float/str): Amount to fund the betting account
                
        Returns:
            dict: JSON response containing the transaction result
        """
        url = cls.get_base_url() + "/betting"
        header = cls.get_header()
        payload = dict()
        amount = float(kwargs.get("amount"))
        payload["provider"] = "creditswitch"
        payload["betProvider"] = kwargs.get("provider")
        payload["customerId"] = kwargs.get("customer_id")
        payload["name"] = kwargs.get("name")
        payload["serviceId"] = kwargs.get("service_id")
        payload["amount"] = amount
        log_request(f"Vend Betting Request:\nurl: {url}\nheader: {header}\npayload: {payload}")
        response = requests.request("POST", url=url, headers=header, data=payload)
        log_request(f"Vend Betting Response:\nresponse: {response.text}")
        return response.json()

    @classmethod
    def purchase_data(cls, **kwargs):
        """
        Purchase mobile data plan through the creditswitch provider.
        
        Args:
            **kwargs: Keyword arguments containing:
                plan_id (str): ID of the selected data plan
                phone_number (str): Recipient's phone number
                amount (float/str): Cost of the data plan
                network (str): Mobile network operator name
                
        Returns:
            dict: JSON response containing the transaction result
        """
        url = cls.get_base_url() + "/data"
        header = cls.get_header()
        payload = dict()
        payload["planId"] = kwargs.get("plan_id")
        payload["phoneNumber"] = kwargs.get("phone_number")
        payload["provider"] = "creditswitch"
        payload["amount"] = kwargs.get("amount")
        payload["network"] = kwargs.get("network")
        log_request(f"Vend Data Request:\nurl: {url}\nheader: {header}\npayload: {payload}")
        response = requests.request("POST", url=url, headers=header, data=payload)
        log_request(f"Vend Data Response:\nresponse: {response.text}")
        return response.json()

    @classmethod
    def get_services(cls, service_type):
        """
        Retrieve available service billers for a specific service type.
        
        Args:
            service_type (str): Type of service to query (e.g., electricity, cable, etc.)
            
        Returns:
            dict: JSON response containing available service billers
        """
        url = cls.get_base_url() + f"/serviceBiller/{service_type}"
        header = cls.get_header()
        log_request(f"GET TMSaaS Service Billers Request:\nurl: {url}\nheader: {header}")
        response = requests.request("GET", url=url, headers=header)
        log_request(f"TMSaaS Service Billers Response:\nresponse: {response.text}")
        return response.json()

    @classmethod
    def get_service_products(cls, service_name, product_code=None):
        """
        Retrieve available products or addons for a specific service.
        
        Args:
            service_name (str): Name of the service
            product_code (str, optional): Code of the product to get addons for
            
        Returns:
            dict: JSON response containing products or addons for the service
        """
        url = cls.get_base_url() + f"/{service_name}/products?provider=cdl"
        header = cls.get_header()
        if product_code:
            url = cls.get_base_url() + f"/{service_name}/addons?provider=cdl&productCode={product_code}"
        log_request(f"GET TMSaaS Products Request:\nurl: {url}\nheader: {header}")
        response = requests.request("GET", url=url, headers=header)
        log_request(f"TMSaaS Products Response:\nresponse: {response.text}")
        return response.json()

    @classmethod
    def validate_smart_card(cls, service_name, scn):
        """
        Validate a cable TV smart card number with the service provider.
        
        Args:
            service_name (str): Name of the cable TV service (e.g., dstv, gotv)
            scn (str): Smart card number to validate
            
        Returns:
            dict: JSON response containing validation result and customer details
        """
        url = cls.get_base_url() + f"/{service_name}/validate"
        header = cls.get_header()
        header["Content-Type"] = "application/x-www-form-urlencoded"
        payload = f"provider=cdl&smartCardNumber={scn}"
        log_request(f"Validate SmartCardNumber TMSaaS:\nurl: {url}\nheader: {header}\npayload: {payload}")
        response = requests.request("POST", url=url, headers=header, data=payload)
        log_request(f"Validate SmartCardNumber TMSaaS Response:\nresponse: {response.text}")
        return response.json()

    @classmethod
    def cable_tv_subscription(cls, service_name, **kwargs):
        """
        Process a cable TV subscription payment.
        
        Args:
            service_name (str): Name of the cable TV service (e.g., dstv, gotv)
            **kwargs: Keyword arguments containing:
                duration (int): Number of months to subscribe for
                customer_number (str): Customer's account number
                amount (float/str): Subscription amount
                customer_name (str): Customer's name
                product_codes (list): List of product/bouquet codes
                smart_card_no (str): Customer's smart card number
                
        Returns:
            dict: JSON response containing subscription result
        """
        url = cls.get_base_url() + f"/{service_name}"
        header = cls.get_header()
        header["Content-Type"] = "application/json"
        amount = float(kwargs.get("amount"))
        payload = json.dumps({
                    "provider": "cdl",
                    "monthsPaidFor": kwargs.get("duration"),
                    "customerNumber": kwargs.get("customer_number"),
                    "amount": amount,
                    "customerName": kwargs.get("customer_name"),
                    "productCodes": kwargs.get("product_codes"),
                    "invoicePeriod": kwargs.get("duration"),
                    "smartcardNumber": kwargs.get("smart_card_no")
                })
        log_request(f"Cable TV Subscription Request:\nurl: {url}\nheader: {header}\npayload: {payload}")
        response = requests.request("POST", url=url, headers=header, data=payload)
        log_request(f"Cable TV Subscription Response:\nresponse: {response.text}")
        return response.json()

    @classmethod
    def get_distribution_company(cls):
        """
        Retrieve list of available electricity distribution companies (DISCOs).
        
        Returns:
            dict: JSON response containing list of available DISCOs
        """
        url = cls.get_base_url() + f"/electricity/getDiscos"
        header = cls.get_header()
        log_request(f"GET Distribution Companies Request:\nurl: {url}\nheader: {header}")
        response = requests.request("GET", url=url, headers=header)
        log_request(f"GET Distribution Companies Response:\nresponse: {response.text}")
        return response.json()

    @classmethod
    def get_betting_providers(cls):
        """
        Retrieve list of available betting service providers through creditswitch.
        
        Returns:
            dict: JSON response containing list of betting providers
        """
        url = cls.get_base_url() + f"/betting/creditswitch/providers"
        header = cls.get_header()
        log_request(f"GET Betting Provider Request:\nurl: {url}\nheader: {header}")
        response = requests.request("GET", url=url, headers=header)
        log_request(f"GET Betting Provider Response:\nresponse: {response.text}")
        return response.json()

    @classmethod
    def validate_betting(cls, customer_id, provider):
        """
        Validate a customer's betting account with a specific provider.
        
        Args:
            customer_id (str): Customer's ID with the betting provider
            provider (str): Name of the betting provider
            
        Returns:
            dict: JSON response containing validation result
        """
        url = cls.get_base_url() + f"/betting/validate"
        header = cls.get_header()
        payload = dict()
        payload["provider"] = "creditswitch"
        payload["betProvider"] = provider
        payload["customerId"] = customer_id
        log_request(f"Validate Betting Request:\nurl: {url}\nheader: {header}\npayload: {payload}")
        response = requests.request("POST", url=url, headers=header, data=payload)
        log_request(f"Validate Betting Response:\nresponse: {response.text}")
        return response.json()

    @classmethod
    def validate_meter_no(cls, disco_type, meter_no):
        """
        Validate an electricity meter number with a distribution company.
        
        Args:
            disco_type (str): Type of DISCO (e.g., IKEDC_PREPAID, EKEDC_POSTPAID)
            meter_no (str): Meter number to validate
            
        Returns:
            dict: JSON response containing validation result and customer details
        """
        url = cls.get_base_url() + f"/electricity/validate"
        header = cls.get_header()
        payload = dict()
        payload["type"] = disco_type
        payload["customerReference"] = meter_no
        log_request(f"Validate MeterNo Request:\nurl: {url}\nheader: {header}\npayload: {payload}")
        response = requests.request("POST", url=url, headers=header, data=payload)
        log_request(f"Validate MeterNo Response:\nresponse: {response.text}")
        return response.json()

    @classmethod
    def vend_electricity(cls, disco_type, meter_no, amount, phone_number):
        """
        Process electricity token purchase/bill payment.
        
        This method handles both prepaid and postpaid electricity payments for different
        distribution companies (DISCOs). It first validates the meter number and then
        processes the payment based on the DISCO type.
        
        Args:
            disco_type (str): Type of DISCO (e.g., IKEDC_PREPAID, EKEDC_POSTPAID)
            meter_no (str): Customer's meter number
            amount (float/str): Amount to pay/vend
            phone_number (str): Customer's phone number for notifications
            
        Returns:
            dict: Response containing:
                success (bool): Transaction success status
                message (str): Transaction status message
                token (str, optional): Electricity token for prepaid meters
                status (str): Transaction status (success/failed/pending)
                transaction_id (str): Unique transaction identifier
        """
        validate_response = cls.validate_meter_no(disco_type, meter_no)
        vending_amount = float(amount)

        response_data = dict()
        response_data["success"] = False
        response_data["message"] = "An error occurred while trying to vend electricity"
        response_data["token"] = None
        response_data["status"] = "pending"
        response_data["transaction_id"] = None

        if "error" in validate_response:
            response_data["message"] = "Meter Validation Error"
            response_data["status"] = "failed"
            return response_data

        # Construct payload based on distribution company type
        if disco_type == "IKEDC_POSTPAID":
            # Ikeja Electric Postpaid
            payload = {
                "disco": "IKEDC_POSTPAID",
                "customerReference": meter_no,
                "customerAddress": validate_response["data"]["address"],
                "amount": vending_amount,
                "customerName": validate_response["data"]["name"],
                "phoneNumber": phone_number,
                "customerAccountType": validate_response["data"]["customerAccountType"],
                "accountNumber": validate_response["data"]["accountNumber"],
                "customerAccountId": meter_no,
                "customerDtNumber": validate_response["data"]["customerDtNumber"],
                "contactType": "LANDLORD"
            }

        elif disco_type == "IKEDC_PREPAID":
            # Ikeja Electric Prepaid
            payload = {
                "disco": "IKEDC_PREPAID",
                "customerReference": meter_no,
                "customerAccountId": meter_no,
                "canVend": True,
                "customerAddress": validate_response["data"]["address"],
                "meterNumber": meter_no,
                "customerName": validate_response["data"]["name"],
                "customerAccountType": validate_response["data"]["customerAccountType"],
                "accountNumber": validate_response["data"]["accountNumber"],
                "customerDtNumber": validate_response["data"]["customerDtNumber"],
                "amount": vending_amount,
                "phoneNumber": phone_number,
                "contactType": "LANDLORD"
            }

        elif disco_type == "EKEDC_POSTPAID":
            # Eko Electric Postpaid
            payload = {
                "disco": "EKEDC_POSTPAID",
                "accountNumber": meter_no,
                "amount": vending_amount
            }

        elif disco_type == "EKEDC_PREPAID":
            # Eko Electric Prepaid
            payload = {
                "disco": "EKEDC_PREPAID",
                "customerReference": meter_no,
                "canVend": True,
                "customerAddress": validate_response["data"]["customerAddress"],
                "meterNumber": meter_no,
                "customerName": validate_response["data"]["customerName"],
                "amount": vending_amount
            }

        elif disco_type == "IBEDC_POSTPAID":
            # Ibadan Electric Postpaid
            payload = {
                "disco": "IBEDC_POSTPAID",
                "customerReference": meter_no,
                "amount": vending_amount,
                "thirdPartyCode": "21",
                "customerName": str(validate_response["data"]["firstName"] + " " + validate_response["data"]["lastName"])
            }

        elif disco_type == "IBEDC_PREPAID":
            # Ibadan Electric Prepaid
            payload = {
                "disco": "IBEDC_PREPAID",
                "customerReference": meter_no,
                "amount": vending_amount,
                "thirdPartyCode": "21",
                "customerType": "PREPAID",
                "firstName": validate_response["data"]["firstName"],
                "lastName": validate_response["data"]["lastName"]
            }
        else:
            response_data["message"] = "Distribution company type is not valid"
            response_data["status"] = "failed"
            return response_data

        # Process the electricity vending request
        header = cls.get_header()
        url = cls.get_base_url() + f"/electricity/vend"
        log_request(f"Vending Electricity ({disco_type}) Request:\nurl: {url}\nheader: {header}\npayload: {payload}")
        req = requests.request("POST", url=url, headers=header, data=payload)
        log_request(f"Vending Electricity ({disco_type}) Response:\nresponse: {req.text}")

        response = req.json()

        # Handle error response
        if "error" in response:
            response_data["message"] = response["error"]
            response_data["status"] = "failed"
            return response_data

        # Process successful response
        provider_status = response["data"]["providerResponse"]["status"]

        response_data["success"] = True
        response_data["message"] = "An error occurred while trying to vend electricity"
        response_data["transaction_id"] = response["data"]["transactionId"]

        if provider_status == "ACCEPTED":
            response_data["status"] = "success"

        # Include token for prepaid meters
        if response["data"]["providerResponse"]["token"]:
            response_data["token"] = response["data"]["providerResponse"]["token"]

        return response_data

    @classmethod
    def retry_electricity_vending(cls, transaction_id):
        """
        Retry a failed electricity vending transaction or check its status.
        
        Args:
            transaction_id (str): ID of the original vending transaction
            
        Returns:
            dict: JSON response containing updated transaction status
        """
        url = cls.get_base_url() + f"/electricity/query?disco=EKEDC_PREPAID&transactionId={transaction_id}"
        header = cls.get_header()
        log_request(f"Retry Electricity Request:\nurl: {url}\nheader: {header}")
        response = requests.request("GET", url=url, headers=header)
        log_request(f"Retry Electricity Response:\nresponse: {response.text}")
        return response.json()

    @classmethod
    def check_saas_wallet_balance(cls):
        """
        Check the current balance in the TMSaaS wallet.
        
        Returns:
            dict: JSON response containing wallet balance and details
        """
        client_id = decrypt_text(bank.tmsaasKey)
        url = cls.get_base_url() + f"/client/wallet/{client_id}"
        header = cls.get_header()
        log_request(f"Check TMSaaS Balance Request:\nurl: {url}\nheader: {header}")
        response = requests.request("GET", url=url, headers=header)
        log_request(f"Check TMSaaS Balance Response:\nresponse: {response.text}")
        return response.json()

    @classmethod
    def perform_liveness_check(cls, bvn, image_url):
        """
        Perform a liveness check by comparing a BVN with a provided image.
        
        Args:
            bvn (str): Bank Verification Number
            image_url (str): URL of the image to verify against the BVN
            
        Returns:
            dict: JSON response containing verification result
        """
        url = cls.get_base_url() + f"/verification/v1/verification/verifybvnimage"
        header = cls.get_header()
        payload = dict()
        payload["bvn"] = bvn
        payload["image"] = image_url
        log_request(f"Perform Liveness Check Request:\nurl: {url}\nheader: {header}\npayload: {payload}")
        response = requests.request("POST", url=url, headers=header, data=payload)
        log_request(f"Perform Liveness Check Response:\nresponse: {response.text}")
        return response.json()

    @classmethod
    def send_sms(cls, content, receiver):
        """
        Send SMS message using TMSaaS SMS service.
        
        Args:
            content (str): SMS message content
            receiver (str): Recipient's phone number
            
        Returns:
            dict: JSON response containing SMS delivery status
        """
        url = cls.get_base_url() + f"/sms"
        header = cls.get_header()
        header["Content-Type"] = "application/json"
        payload = json.dumps({"message": content, "senderId": bank.tm_sms_sender_id, "recipients": [receiver]})
        log_request(f"Sending TMSaaS SMS Request:\nurl: {url}\nheader: {header}\npayload: {payload}")
        response = requests.request("POST", url=url, headers=header, data=payload)
        log_request(f"Sending TMSaaS SMS Response:\nresponse: {response.text}")
        return response.json()



    # Insurance Services
    @classmethod
    def get_vehicle_insurance_detail(cls, query_type, service_provider=None, vm_id=None):
        """
        Retrieve various details related to vehicle insurance from the Uridium provider.
        
        This method can fetch different types of vehicle insurance information based on
        the query_type parameter:
        - Service providers list
        - Vehicle makes
        - Vehicle purposes
        - Vehicle colors
        - States (locations)
        - Insurance policies
        - Insurance types
        - Vehicle models (requires vehicle make ID)
        
        Args:
            query_type (str): Type of information to retrieve
                            (make/purpose/color/state/policy/insurance_type/model)
            service_provider (str, optional): Insurance service provider name
            vm_id (str, optional): Vehicle make ID, required when query_type is 'model'
            
        Returns:
            dict: JSON response containing requested insurance details
        """
        url = cls.get_base_url() + f"/insurance/serviceproviders?type=vehicle&provider=uridium"
        if query_type == "make":
            url = cls.get_base_url() + f"/insurance/vehiclemake?type=vehicle&provider=uridium&serviceProvider={service_provider}"
        if query_type == "purpose":
            url = cls.get_base_url() + f"/insurance/vehiclepurpose?type=vehicle&provider=uridium&serviceProvider={service_provider}"
        if query_type == "color":
            url = cls.get_base_url() + f"/insurance/vehiclecolor?type=vehicle&provider=uridium&serviceProvider={service_provider}"
        if query_type == "state":
            url = cls.get_base_url() + f"/insurance/state?type=vehicle&provider=uridium&serviceProvider={service_provider}"
        if query_type == "policy":
            url = cls.get_base_url() + f"/insurance/policy?type=vehicle&provider=uridium&serviceProvider={service_provider}"
        if query_type == "insurance_type":
            url = cls.get_base_url() + f"/insurance/type?type=vehicle&provider=uridium&serviceProvider={service_provider}"
        if query_type == "model":
            url = cls.get_base_url() + f"/insurance/vehiclemodel?type=vehicle&provider=uridium&serviceProvider={service_provider}&vehicleMakeId={vm_id}"

        header = cls.get_header()
        log_request(f"Vehicle Insurance Detail Request:\nurl: {url}\nheader: {header}")
        response = requests.request("GET", url=url, headers=header)
        log_request(f"Vehicle Insurance Detail Response:\nresponse: {response.text}")
        return response.json()

    @classmethod
    def get_vehicle_insurance_quote(cls, **kwargs):
        """
        Get a quote for vehicle insurance or proceed with insurance purchase.
        
        This method can either generate a quote or process an insurance purchase
        based on the vend_now parameter.
        
        Args:
            **kwargs: Keyword arguments containing:
                vend_now (str): If "true", processes insurance purchase
                amount (float/str): Insurance premium amount
                quote_id (str, optional): Required if vend_now is "true"
                policy_id (str): Insurance policy ID
                insurance_type_id (str): Type of insurance
                email (str): Customer's email
                state_code (str): State/location code
                model (str): Vehicle model ID
                make (str): Vehicle make ID
                color (str): Vehicle color ID
                insured_name (str): Name of the insured
                address (str): Customer's address
                engine_no (str): Vehicle engine number
                chassis_no (str): Vehicle chassis number
                engine_capacity (str): Engine capacity
                year (str): Vehicle manufacturing year
                category (str): Vehicle category ID
                sum_cover (str/float): Insurance coverage amount
                phone_number (str): Customer's phone number
                provider (str): Insurance provider
                plate_number (str): Vehicle plate number
                purpose (str): Vehicle purpose ID
                
        Returns:
            dict: JSON response containing quote or insurance purchase details
        """
        url = cls.get_base_url() + f"/insurance/quotes"
        vend_now = kwargs.get("vend_now")
        amount = float(kwargs.get("amount"))
        payload = dict()
        if vend_now == "true":
            url = cls.get_base_url() + f"/insurance/vend"
            payload["amount"] = amount
            payload["quoteId"] = kwargs.get("quote_id")
        payload["insurance_policy_id"] = kwargs.get("policy_id")
        payload["insurance_type_id"] = kwargs.get("insurance_type_id")
        payload["email"] = kwargs.get("email")
        payload["state_code"] = kwargs.get("state_code")
        payload["vehicle_model_id"] = kwargs.get("model")
        payload["vehicle_make_id"] = kwargs.get("make")
        payload["vehicle_color_id"] = kwargs.get("color")
        payload["insured_name"] = kwargs.get("insured_name")
        payload["address"] = kwargs.get("address")
        payload["engine_no"] = kwargs.get("engine_no")
        payload["chassis_no"] = kwargs.get("chassis_no")
        payload["engine_capacity"] = kwargs.get("engine_capacity")
        payload["year_of_make"] = kwargs.get("year")
        payload["vehicle_category_id"] = kwargs.get("category")
        payload["sum_cover"] = kwargs.get("sum_cover")
        payload["phonenumber"] = kwargs.get("phone_number")
        payload["type"] = "vehicle"
        payload["provider"] = "uridium"
        payload["serviceProvider"] = kwargs.get("provider")
        payload["number_plate"] = kwargs.get("plate_number")
        payload["vehicle_purpose_id"] = kwargs.get("purpose")

        header = cls.get_header()
        header["Content-Type"] = "application/x-www-form-urlencoded"
        log_request(f"Vehicle Insurance Quote Request:\nurl: {url}\nheader: {header}\npayload: {payload}")
        response = requests.request("POST", url=url, headers=header, data=payload)
        log_request(f"Vehicle Insurance Quote Response:\nresponse: {response.text}")
        return response.json()

    @classmethod
    def get_my_cover_insurance_plans(cls, insurance_type):
        """
        Retrieve available insurance plans from MyCover provider.
        
        Supports different types of insurance plans:
        - Health insurance
        - Gadget insurance
        - Content insurance (shop/office/home)
        
        Args:
            insurance_type (str): Type of insurance ("health", "gadget", or "content")
            
        Returns:
            dict: JSON response containing available insurance plans for the specified type
        """
        url = cls.get_base_url() + f"/insurance/plans?provider=mycover&type=health"
        if insurance_type == "gadget":
            url = cls.get_base_url() + f"/insurance/plans?provider=mycover&type=gadget"
        if insurance_type == "content":
            url = cls.get_base_url() + f"/insurance/plans?provider=mycover&type=content"
        header = cls.get_header()
        log_request(f"GET myCover Insurance Plan Request:\nurl: {url}\nheader: {header}")
        response = requests.request("GET", url=url, headers=header)
        log_request(f"GET myCover Insurance Plan Response:\nresponse: {response.text}")
        return response.json()

    @classmethod
    def perform_insurance(cls, insurance_type, **kwargs):
        """
        Process insurance purchase requests for various types of insurance.
        
        This method handles multiple types of insurance:
        1. Health Insurance (MyCoverGenius provider)
        2. Content Insurance (Aiico provider):
           - Shop content
           - Office content
           - Home content
        3. Gadget Insurance:
           - MyCoverGenius provider
           - Sovereign Trust provider
        
        Args:
            insurance_type (str): Type of insurance to process
                                (health/shop_content/office_content/home_content/
                                 mycover_gadget/sovereign_gadget)
            **kwargs: Keyword arguments containing:
                Common fields:
                    first_name (str): Customer's first name
                    last_name (str): Customer's last name
                    dob (str): Date of birth
                    gender (str): Customer's gender
                    email (str): Customer's email
                    phone_number (str): Customer's phone number
                    product_id (str): Insurance product ID
                    product_name (str): Insurance product name
                    image (str): Customer's image URL
                    amount (float/str): Insurance premium amount
                    address (str): Customer's address
                    title (str): Customer's title
                
                Health Insurance specific:
                    duration (str): Payment plan duration
                
                Content Insurance specific:
                    local_govt (str): Local government area
                    indentification_document (str): ID document type
                    indentification_document_url (str): ID document image URL
                    insurance_date (str): Insurance start date
                    tenancy (str): Tenancy details (for office/home)
                    description (str): Property description (for office/home)
                    items (list): List of items to insure (for office/home)
                    business_type (str): Nature of business (for shop)
                    stock_type (str): Nature of stock (for shop)
                    stock_interval (str): Stock-taking interval (for shop)
                    stock_amount (float): Stock value (for shop)
                
                Gadget Insurance specific:
                    make (str): Device make
                    model (str): Device model
                    color (str): Device color
                    imei (str): Device IMEI number
                    serial_no (str): Device serial number
                    purchase_date (str): Device purchase date
                    device_type (str): Type of device
                    device_value (float): Device value
                    
        Returns:
            dict: JSON response containing insurance purchase result
        """
        url = cls.get_base_url() + f"/insurance/vend"
        amount = float(kwargs.get("amount"))
        
        # Common payload fields for all insurance types
        payload = {
            "firstName": kwargs.get("first_name"),
            "lastName": kwargs.get("last_name"),
            "dob": kwargs.get("dob"),
            "gender": kwargs.get("gender"),
            "email": kwargs.get("email"),
            "phoneNumber": kwargs.get("phone_number"),
            "productId": kwargs.get("product_id"),
            "productName": kwargs.get("product_name"),
            "image": kwargs.get("image"),
            "amount": amount,
            "address": kwargs.get("address"),
            "title": kwargs.get("title"),
        }

        # Health insurance specific fields
        if insurance_type == "health":
            payload.update({
                "provider": "mycover",
                "type": "health",
                "serviceProvider": "MyCoverGenius",
                "paymentPlan": str(kwargs.get("duration")).capitalize()
            })

        # Content insurance (shop/office/home) specific fields
        if insurance_type in ["shop_content", "office_content", "home_content"]:
            payload.update({
                    "provider": "mycover",
                    "type": "content",
                    "lga": kwargs.get("local_govt"),
                    "isFullYear": True,
                    "identificationName": kwargs.get("indentification_document"),
                    "identificationUrl": kwargs.get("indentification_document_url"),
                    "insuranceStartDate": kwargs.get("insurance_date"),
                    "serviceProvider": "Aiico"
                })
            # Additional fields for office and home content
            if insurance_type == "office_content" or "home_content":
                payload.update({
                    "tenancy": kwargs.get("tenancy"),
                    "description": kwargs.get("description"),
                    "preOwnership": ""
                })
            # Office-specific items
            if insurance_type == "office_content":
                payload.update({"officeItems": kwargs.get("items")})
            # Home-specific items
            if insurance_type == "home_content":
                payload.update({"homeItems": kwargs.get("items")})
            # Shop-specific details
            if insurance_type == "shop_content":
                payload.update({
                    "shopType": "Box",
                    "natureOfBusiness": kwargs.get("business_type"),
                    "natureOfStock": kwargs.get("stock_type"),
                    "stockKeeping": True,
                    "stockTakingInterval": kwargs.get("stock_interval"),
                    "stockAmount": kwargs.get("stock_amount")
                })

        # Gadget insurance specific fields
        if insurance_type in ["mycover_gadget", "sovereign_gadget"]:
            payload.update({
                "provider": "mycover",
                "type": "gadget",
                "deviceMake": kwargs.get("make"),
                "deviceModel": kwargs.get("model"),
                "deviceColor": kwargs.get("color"),
                "imeiNumber": kwargs.get("imei"),
                "deviceSerialNumber": kwargs.get("serial_no"),
                "dateOfPurchase": kwargs.get("purchase_date"),
                "deviceType": kwargs.get("device_type"),
                "deviceValue": kwargs.get("device_value"),
            })
            # Set appropriate service provider
            if insurance_type == "mycover_gadget":
                payload.update({"serviceProvider": "MyCoverGenius"})
            if insurance_type == "sovereign_gadget":
                payload.update({"serviceProvider": "Sovereign Trust"})

        # Process the insurance request
        header = cls.get_header()
        log_request(f"Vend Insurance Request:\nurl: {url}\nheader: {header}\npayload: {payload}")
        response = requests.request("POST", url=url, headers=header, data=payload)
        log_request(f"Vend Insurance Response:\nresponse: {response.text}")
        return response.json()

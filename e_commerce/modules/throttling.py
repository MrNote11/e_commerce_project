from rest_framework.throttling import (ScopedRateThrottle, UserRateThrottle, 
                                       AnonRateThrottle)


class AuthRateThrottle(AnonRateThrottle):
    """
    Throttle for unauthenticated users attempting to authenticate.
    """
    rate = '5/minute' 
    scope = 'auth'


class SignupThrottle(ScopedRateThrottle):
    """Throttle for signup attempts"""
    scope = 'signup'


class WithdrawalThrottle(ScopedRateThrottle):
    """Throttle for withdrawal operations"""
    scope = 'withdrawal'


class InvestmentThrottle(ScopedRateThrottle):
    """Throttle for investment operations"""
    scope = 'investment'


class AdminThrottle(ScopedRateThrottle):
    """Throttle for admin operations"""
    scope = 'admin'


class BurstRateThrottle(UserRateThrottle):
    """Throttle for burst rate limiting"""
    scope = 'burst'


class SustainedRateThrottle(UserRateThrottle):
    """Throttle for sustained rate limiting"""
    scope = 'sustained' 

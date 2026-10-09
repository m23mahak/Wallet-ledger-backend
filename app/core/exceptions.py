"""Custom exceptions for WalletLedger."""


class AppException(Exception):
    status_code: int = 500
    code: str = "INTERNAL_ERROR"
    message: str = "Internal server error"

    def __init__(self, message: str | None = None):
        self.message = message or self.message
        super().__init__(self.message)


class ServiceUnavailable(AppException):
    status_code = 503
    code = "SERVICE_UNAVAILABLE"
    message = "Service unavailable"


class Unauthorized(AppException):
    status_code = 401
    code = "UNAUTHORIZED"
    message = "Authentication required"


class InvalidCredentials(AppException):
    status_code = 401
    code = "INVALID_CREDENTIALS"
    message = "Invalid email or password"


class Forbidden(AppException):
    status_code = 403
    code = "FORBIDDEN"
    message = "You do not have permission to perform this action"


class UserBlocked(AppException):
    status_code = 403
    code = "USER_BLOCKED"
    message = "This account is blocked"


class EmailAlreadyRegistered(AppException):
    status_code = 409
    code = "EMAIL_ALREADY_REGISTERED"
    message = "Email is already registered"


class WalletNotFound(AppException):
    status_code = 404
    code = "WALLET_NOT_FOUND"
    message = "Wallet not found"


class WalletFrozen(AppException):
    status_code = 403
    code = "WALLET_FROZEN"
    message = "Wallet is frozen and cannot perform operations"


class InsufficientBalance(AppException):
    status_code = 400
    code = "INSUFFICIENT_BALANCE"
    message = "Insufficient available balance"


class SelfTransferNotAllowed(AppException):
    status_code = 400
    code = "SELF_TRANSFER_NOT_ALLOWED"
    message = "Cannot transfer funds to the same wallet"


class InvalidRecipient(AppException):
    status_code = 404
    code = "RECIPIENT_NOT_FOUND"
    message = "Recipient wallet or user not found"


class RiskLimitExceeded(AppException):
    status_code = 400
    code = "RISK_LIMIT_EXCEEDED"
    message = "Transfer exceeds maximum permitted limit"


class HoldNotFound(AppException):
    status_code = 404
    code = "HOLD_NOT_FOUND"
    message = "Hold not found"


class InvalidHoldState(AppException):
    status_code = 400
    code = "INVALID_HOLD_STATE"
    message = "Hold is not in ACTIVE state"


class TransactionNotFound(AppException):
    status_code = 404
    code = "TRANSACTION_NOT_FOUND"
    message = "Transaction not found"


class IdempotencyConflict(AppException):
    status_code = 409
    code = "IDEMPOTENCY_CONFLICT"
    message = "Concurrent request with the same idempotency key"

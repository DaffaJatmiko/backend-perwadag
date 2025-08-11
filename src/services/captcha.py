"""Google reCAPTCHA verification service."""

import httpx
import logging
from typing import Optional, Dict, Any
from src.core.config import settings

logger = logging.getLogger(__name__)


class CaptchaVerificationResult:
    """Result of CAPTCHA verification."""

    def __init__(
        self,
        success: bool,
        score: Optional[float] = None,
        action: Optional[str] = None,
        error_codes: Optional[list] = None,
        hostname: Optional[str] = None,
    ):
        self.success = success
        self.score = score
        self.action = action
        self.error_codes = error_codes or []
        self.hostname = hostname

    @property
    def is_human(self) -> bool:
        """Check if the score indicates human-like behavior."""
        if self.score is None:
            return self.success
        return self.success and self.score >= settings.RECAPTCHA_THRESHOLD

    def get_error_message(self) -> str:
        """Get human-readable error message."""
        if not self.error_codes:
            return "CAPTCHA verification failed"

        error_messages = {
            "missing-input-secret": "Secret key is missing",
            "invalid-input-secret": "Secret key is invalid",
            "missing-input-response": "CAPTCHA token is missing",
            "invalid-input-response": "CAPTCHA token is invalid or expired",
            "bad-request": "Invalid request format",
            "timeout-or-duplicate": "CAPTCHA token has expired or already been used",
        }

        messages = []
        for code in self.error_codes:
            messages.append(error_messages.get(code, f"Unknown error: {code}"))

        return "; ".join(messages)


class CaptchaService:
    """Service for Google reCAPTCHA verification."""

    def __init__(self):
        self.verify_url = settings.RECAPTCHA_VERIFY_URL
        self.secret_key = settings.RECAPTCHA_SECRET_KEY
        self.timeout = settings.RECAPTCHA_TIMEOUT_SECONDS

    async def verify_token(
        self,
        token: str,
        remote_ip: Optional[str] = None,
        expected_action: Optional[str] = "login",
    ) -> CaptchaVerificationResult:
        """
        Verify reCAPTCHA token with Google's API.

        Args:
            token: reCAPTCHA token from frontend
            remote_ip: Client IP address (optional)
            expected_action: Expected action name for v3 (optional)

        Returns:
            CaptchaVerificationResult with verification details
        """
        if not settings.RECAPTCHA_ENABLED:
            logger.info("reCAPTCHA verification is disabled")
            return CaptchaVerificationResult(success=True, score=1.0)

        if not self.secret_key:
            logger.error("reCAPTCHA secret key is not configured")
            return CaptchaVerificationResult(
                success=False, error_codes=["missing-input-secret"]
            )

        if not token:
            logger.warning("Empty reCAPTCHA token provided")
            return CaptchaVerificationResult(
                success=False, error_codes=["missing-input-response"]
            )

        # Prepare verification data
        data = {"secret": self.secret_key, "response": token}

        if remote_ip:
            data["remoteip"] = remote_ip

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:

                response = await client.post(
                    self.verify_url,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                response.raise_for_status()
                result_data = response.json()
        
        except httpx.TimeoutException:
            logger.error("reCAPTCHA verification timed out")
            return CaptchaVerificationResult(success=False, error_codes=["timeout"])
        except httpx.HTTPError as e:
            logger.error(f"reCAPTCHA verification HTTP error: {e}")
            return CaptchaVerificationResult(success=False, error_codes=["http-error"])
        except Exception as e:
            logger.error(f"reCAPTCHA verification unexpected error: {e}")
            return CaptchaVerificationResult(
                success=False, error_codes=["unexpected-error"]
            )

        # Parse Google's response
        success = result_data.get("success", False)
        score = result_data.get("score")  # Available in v3
        action = result_data.get("action")  # Available in v3
        error_codes = result_data.get("error-codes", [])
        hostname = result_data.get("hostname")

        # Log detailed response for debugging
        logger.info(
            f"Google reCAPTCHA response - Success: {success}, Score: {score}, Hostname: {hostname}, Errors: {error_codes}"
        )

        result = CaptchaVerificationResult(
            success=success,
            score=score,
            action=action,
            error_codes=error_codes,
            hostname=hostname,
        )

        # Log verification result
        if result.success:
            if score is not None:
                logger.info(f"reCAPTCHA verified successfully (score: {score:.2f})")
            else:
                logger.info("reCAPTCHA verified successfully")
        else:
            logger.warning(
                f"reCAPTCHA verification failed: {result.get_error_message()}"
            )

        # Validate action if provided (v3 specific)
        if expected_action and action and action != expected_action:
            logger.warning(
                f"reCAPTCHA action mismatch: expected {expected_action}, got {action}"
            )
            return CaptchaVerificationResult(
                success=False,
                score=score,
                action=action,
                error_codes=["action-mismatch"],
            )

        return result

    def is_configured(self) -> bool:
        """Check if reCAPTCHA is properly configured."""
        return bool(
            settings.RECAPTCHA_ENABLED
            and self.secret_key
            and settings.RECAPTCHA_SITE_KEY
        )

    def get_site_key(self) -> Optional[str]:
        """Get the site key for frontend usage."""
        return settings.RECAPTCHA_SITE_KEY if self.is_configured() else None


# Global service instance
captcha_service = CaptchaService()

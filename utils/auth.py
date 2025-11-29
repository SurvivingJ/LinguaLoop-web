from functools import wraps
from flask import request, jsonify, g
import jwt, requests, json
import logging

logger = logging.getLogger(__name__)

SUPABASE_JWKS_URL = "https://kpfqrjtfxmujzolwsvdq.supabase.co/auth/v1/.well-known/jwks.json"

def supabase_jwt_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        logger.info(f"🔐 Auth header present: {bool(auth)}, starts with Bearer: {auth.startswith('Bearer ')}")

        if not auth.startswith("Bearer "):
            logger.error("❌ Missing or malformed bearer token")
            return jsonify({"error": "Missing bearer token"}), 401

        token = auth[len("Bearer "):]
        logger.info(f"🔑 Token length: {len(token)} chars")

        try:
            # JWKS fetch/caching could be optimized
            jwks = requests.get(SUPABASE_JWKS_URL).json()["keys"]
            header = jwt.get_unverified_header(token)
            logger.info(f"📝 JWT header kid: {header.get('kid')}")

            key = next((k for k in jwks if k["kid"] == header["kid"]), None)
            if not key:
                logger.error(f"❌ No matching JWK key for kid: {header.get('kid')}")
                raise Exception("No matching JWK key")

            public_key = jwt.algorithms.ECAlgorithm.from_jwk(json.dumps(key))
            claims = jwt.decode(token, public_key, algorithms=["ES256"], audience="authenticated")
            logger.info(f"✅ JWT validated for user: {claims.get('sub')}")

            # Store claims on Flask global context for use in the route handler
            g.supabase_claims = claims
        except Exception as e:
            logger.error(f"❌ JWT validation failed: {str(e)}", exc_info=True)
            return jsonify({"error": f"Invalid Supabase JWT: {str(e)}"}), 401
        return fn(*args, **kwargs)
    return wrapper

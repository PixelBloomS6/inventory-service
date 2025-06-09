from fastapi import Depends, HTTPException, Header
from jose import jwt, jwk, JWTError
import requests

JWKS_URL = "https://pixelbloomflower.b2clogin.com/pixelbloomflower.onmicrosoft.com/b2c_1_signupsignin/discovery/v2.0/keys"
AUDIENCE = "dfe5acb7-236a-40b0-8d8e-165fcbe2623e"
ISSUER = "https://pixelbloomflower.b2clogin.com/f61d643d-6382-41b1-a520-4541fd18d04e/v2.0/"

# Fetch signing keys (in production, cache this!)
jwks = requests.get(JWKS_URL).json()

def get_kid(token: str):
    unverified_header = jwt.get_unverified_header(token)
    return unverified_header["kid"]

def get_signing_key(kid):
    for key in jwks["keys"]:
        if key["kid"] == kid:
            return key
    raise Exception("Signing key not found")

def verify_jwt_token(token: str = Header(..., alias="Authorization")):
    if token.startswith("Bearer "):
        token = token[len("Bearer "):]

    try:
        kid = get_kid(token)
        key_data = get_signing_key(kid)
        key = jwk.construct(key_data, algorithm="RS256")

        payload = jwt.decode(
            token,
            key=key,
            audience=AUDIENCE,
            issuer=ISSUER,
            algorithms=["RS256"]
        )
        return payload
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token verification failed: {str(e)}")

def require_role(role: str):
    def checker(payload: dict = Depends(verify_jwt_token)):
        # Temporarily allow all authenticated users for ShopOwner
        if role == "ShopOwner":
            return payload
        
        roles = payload.get("roles", [])
        if role not in roles:
            raise HTTPException(status_code=403, detail="Forbidden: Insufficient role")
        return payload
    return checker

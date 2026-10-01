from passlib.context import CryptContext

# bcrypt cost 10 is OWASP's minimum recommended work factor. The default (12)
# is 4x slower per sign-in: ~1 s on a laptop and several seconds on a
# fractional-CPU host, which users felt as a slow login. The cost is stored
# inside each hash, so existing cost-12 hashes keep verifying unchanged.
pwd_context = CryptContext(
    schemes=["bcrypt"],
    bcrypt__rounds=10,
    deprecated="auto"
)


def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)

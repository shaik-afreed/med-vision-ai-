from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str):
    print("Entered Password :", plain_password)
    print("Stored Hash      :", hashed_password)

    result = pwd_context.verify(plain_password, hashed_password)

    print("Password Match   :", result)

    return result

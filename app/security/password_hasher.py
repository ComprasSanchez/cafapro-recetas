import bcrypt


def hash_password(plain: str, rounds: int = 12) -> str:
    salt = bcrypt.gensalt(rounds=rounds)
    return bcrypt.hashpw(plain.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain: str, stored_hash: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), stored_hash.encode("utf-8"))

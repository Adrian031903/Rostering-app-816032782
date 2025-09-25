# Ensure tests can call generate_password_hash(..., method="sha256")
# Werkzeug 3.x expects "pbkdf2:sha256". Patch it before tests import.
import werkzeug.security as _sec

_orig_generate = _sec.generate_password_hash

def _generate_password_hash_compat(password, method="pbkdf2:sha256", salt_length=8):
    if method == "sha256":
        method = "pbkdf2:sha256"
    return _orig_generate(password, method=method, salt_length=salt_length)

_sec.generate_password_hash = _generate_password_hash_compat  # type: ignore
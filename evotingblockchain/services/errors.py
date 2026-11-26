class EvoteError(Exception):
    """Dasar semua kesalahan aplikasi yang aman ditampilkan ke pengguna."""

class ValidationError(EvoteError):
    pass

class PermissionDenied(EvoteError):
    pass

class ChainError(EvoteError):
    pass

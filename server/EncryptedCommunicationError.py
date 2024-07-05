class EncryptedCommunicationError(Exception):
    """异常基类"""
    pass


class SignError(EncryptedCommunicationError):
    """签名异常：加签异常、验签不匹配等"""
    pass


class AESError(EncryptedCommunicationError):
    """AES异常：加密、解密时参数错误"""
    pass


class RSAError(EncryptedCommunicationError):
    """RSA异常：密钥错误、加密解密错误"""
    pass
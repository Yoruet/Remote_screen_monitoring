import base64
from binascii import b2a_hex, a2b_hex
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import pad, unpad
from EncryptedCommunicationError import *
basestring = (str, bytes)


def required_string(string, dst_type=None):
    """自动适应并返回所需的字符串类型。

    :param string: 任意字符串，py3+中为str或bytes

    :param dst_type: 需要的字符串类型，默认py3为bytes

    :returns: 转换后的字符串
    """
    if isinstance(string, basestring):
        if not dst_type or dst_type == "bytes":
            # py3 default string type: bytes
            if isinstance(string, bytes):
                return string
            else:
                return string.encode("utf-8")
        elif dst_type == "str":
            if isinstance(string, str):
                return string
            else:
                return string.decode("utf-8")
        else:
            raise ValueError("The param dst_type error, require str or bytes in py3")
    else:
        raise TypeError("The param string type error, require %s" % basestring)


def AESEncrypt(key, plaintext, output="base64", output_type=None):
    """AES加密函数

    :param key: 密钥，ASCII编码的16、24或32字节

    :param plaintext: 待加密文本

    :param output: 输出格式，base64（默认）或hex（十六进制）

    :param output_type: 输出字符串的类型，参考required_string函数中的dst_type参数

    :raises: AESError, ValueError

    :returns: 加密后的密文

    """

    if key and plaintext:
        key = required_string(key, "bytes")
        if len(key) not in AES.key_size:
            raise AESError("The key type error, resulting in length illegality")
        # 需要填充，使用bytes类型
        padding = pad(required_string(plaintext, "bytes"), AES.block_size)
        # 采用CBC模式加密，iv为密钥的前16个字节
        aes = AES.new(key, AES.MODE_CBC, key[:16])
        ciphertext = aes.encrypt(padding)
        crypted_str = b2a_hex(ciphertext) if output == "hex" else base64.b64encode(ciphertext)
        return required_string(crypted_str, output_type)
    else:
        raise AESError("The key or plaintext is not valid")


def AESDecrypt(key, ciphertext, input="base64", output_type=None):
    """AES解密函数

    :param key: 密钥，参考AESEncrypt函数中的key参数

    :param ciphertext: 密文

    :param input: 输入格式，base64（默认）或hex（十六进制）

    :param output_type: 输出字符串的类型，参考required_string函数中的dst_type参数

    :raises: AESError, binascii.Error, ValueError, TypeError

    :returns: 解密后的明文
    """
    if key and ciphertext:
        key = required_string(key, "bytes")
        if len(key) not in AES.key_size:
            raise AESError("The key type error, resulting in length illegality")
        #: Encrypted in CBC mode, iv is fixed to the first 16 characters of the key
        aes = AES.new(key, AES.MODE_CBC, key[:16])
        ciphertext = a2b_hex(ciphertext) if input == "hex" else base64.b64decode(ciphertext)
        #: Remove fill
        plaintext = unpad(aes.decrypt(ciphertext), AES.block_size)
        return required_string(plaintext, output_type)
    else:
        raise AESError("The key or plaintext is not valid")

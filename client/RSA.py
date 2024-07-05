import time
import base64
from binascii import b2a_hex, a2b_hex
from Cryptodome.PublicKey import RSA
from Cryptodome.Cipher import PKCS1_v1_5
def generate_rsa_keys(length=2048, passphrase=None):
    """生成RSA所需的公钥和私钥，公钥格式pkcs8，私钥格式pkcs1。

    :param length: int: 指定密钥长度，默认1024，需要更强加密可设置为2048

    :param passphrase: str: 私钥保护的密码短语

    :returns: tuple(public_key, private_key)
    """
    # 开始生成
    key = RSA.generate(length)
    public_key = key.publickey().exportKey(format="PEM", pkcs=8)
    private_key = key.exportKey(format="PEM", passphrase=passphrase, pkcs=1)
    # 生成完毕
    return (public_key, private_key)


def RSAEncrypt(pubkey, plaintext, output="base64"):
    """RSA公钥加密

    :param pubkey: str,bytes: pkcs1或pkcs8格式公钥

    :param plaintext: str,bytes: 准备加密的文本消息

    :param output: str: Output format: base64 (default), hex (hexadecimal)

    :returns: str,unicode: base64编码的字符串
    """
    if (isinstance(plaintext, str)):
        plaintext = plaintext.encode("utf-8")
    pubkey = RSA.importKey(pubkey)
    ciphertext = PKCS1_v1_5.new(pubkey).encrypt(plaintext)
    crypted_str = b2a_hex(ciphertext) if output == "hex" else base64.b64encode(ciphertext)
    return crypted_str


def RSADecrypt(privkey, ciphertext, passphrase=None, sentinel="ERROR", input="base64"):
    """RSA私钥解密

    :param privkey: str,bytes: pkcs1格式私钥

    :param ciphertext: str,bytes: 已加密的消息

    :param passphrase: str,bytes: 私钥保护的密码短语

    :param sentinel: any type: 检测到错误时返回的标记，默认返回ERROR字符串

    :param input: str: Input format: base64 (default) or hex (hexadecimal), refer to the output parameter of :func:`RSAEncrypt`

    :returns: str,unicode: 消息原文
    """
    privkey = RSA.importKey(privkey, passphrase=passphrase)
    ciphertext = a2b_hex(ciphertext) if input == "hex" else base64.b64decode(ciphertext)
    plaintext = PKCS1_v1_5.new(privkey).decrypt(ciphertext, sentinel)
    return plaintext
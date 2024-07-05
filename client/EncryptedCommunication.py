import re
import sys
import json
import copy
import hashlib
from urllib.parse import quote

from Cryptodome.Random import get_random_bytes

from RSA import *
from AES import *
from EncryptedCommunicationError import *

class EncryptedCommunicationMix(object):
    """加密传输通信基类。

    此类封装加密通信过程中所需函数，包括RSA、AES、MD5等，加密传输整个流程是::

        客户端上传数据加密 ==> 服务端获取数据解密 ==> 服务端返回数据加密 ==> 客户端获取数据解密

    NO.1 客户端上传数据加密流程::

        1. 客户端随机产生一个16位的字符串，用以之后AES加密的秘钥，AESKey。
        2. 使用RSA对AESKey进行公钥加密，RSAKey。
        3. 参数加签，规则是：对所有请求或提交的字典参数按key做升序排列并用"参数名=参数值&"形式连接。
        4. 将明文的要上传的数据包(字典/Map)转为Json字符串，使用AESKey加密，得到JsonAESEncryptedData。
        5. 封装为{key : RSAKey, value : JsonAESEncryptedData}的字典上传服务器，服务器只需要通过key和value，然后解析，获取数据即可。

    NO.2 服务端获取数据解密流程::

        1. 获取到RSAKey后用服务器私钥解密，获取到AESKey
        2. 获取到JsonAESEncriptedData，使用AESKey解密，得到明文的客户端上传上来的数据。
        3. 验签
        4. 返回明文数据

    NO.3 服务端返回数据加密流程::

        1. 将要返回给客户端的数据(字典/Map)进行加签并将签名附属到数据中
        2. 上一步得到的数据转成Json字符串，用AESKey加密处理，记为AESEncryptedResponseData
        3. 封装数据{data : AESEncryptedResponseData}的形式返回给客户端

    NO.4 客户端获取数据解密流程::

        1. 客户端获取到数据后通过key为data得到服务器返回的已经加密的数据AESEncryptedResponseData
        2. 对AESEncryptedResponseData使用AESKey进行解密，得到明文服务器返回的数据。
    """

    #: Set the length of the byte to generate the AESKey
    #:
    #: .. versionadded:: 0.5.0
    BS = AES.block_size

    def get_current_timestamp(self):
        """ UTC时间 """
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def md5(self, message):
        """MD5签名

        :params message: str,unicode,bytes:

        :returns: str: Signed message
        """
        if isinstance(message, str):
            message = message.encode("utf-8")
        return hashlib.md5(message).hexdigest()

    def sha1(self, message):
        """SHA1签名

        :params message: str,unicode,bytes:

        :returns: str: Signed message
        """
        if isinstance(message, str):
            message = message.encode("utf-8")
        return hashlib.sha1(message).hexdigest()

    def sha256(self, message):
        """SHA256签名

        :params message: str,unicode,bytes:

        :returns: str: Signed message
        """
        if isinstance(message, str):
            message = message.encode("utf-8")
        return hashlib.sha256(message).hexdigest()

    def abstract_algorithm_mapping(self, algorithm="md5"):
        """摘要算法映射表

        :param algorithm: str: 算法名称，默认md5，可选md5、sha1、sha256

        :returns: method of calculating summary
        """
        mapping = dict(md5=self.md5, sha1=self.sha1, sha256=self.sha256)
        return mapping.get(algorithm.lower(), self.md5)

    def genAesKey(self):
        """生成AES密钥，32字节

        :returns: str
        """
        return get_random_bytes(self.BS)

    def conversionComma(self, comma_str):
        """将字符串comma_str使用正则以逗号分隔

        :param comma_str: str: 要分隔的字符串，以英文逗号分隔

        :return: list
        """
        if comma_str and isinstance(comma_str, basestring):
            comma_pat = re.compile(r"\s*,\s*")
            comma_str = required_string(comma_str, "str")
            return [i for i in comma_pat.split(comma_str) if i]
        else:
            return []

    def sign(self, parameters, meta={}):
        """ 参数签名，目前版本请勿嵌套无序数据类型（如嵌套dict、嵌套list中嵌套dict），否则可能造成签名失败！

        :param parameters: dict: 请求参数或提交的数据

        :param meta: dict: 公共元数据，参与排序加签

        :raises: TypeError

        :returns: sign message(str) or None
        """
        if isinstance(parameters, dict) and isinstance(meta, dict):
            signIndex = meta.get("SignatureIndex", None)
            SignMethod = meta.get("SignatureMethod", "md5")
            # 重新定义要加签的dict
            if signIndex is False:
                return
            elif signIndex and isinstance(signIndex, basestring):
                signIndex = self.conversionComma(signIndex)
                data = dict()
                for k in signIndex:
                    data[k] = parameters[k]
            else:
                data = copy.deepcopy(parameters)
            # 追加公共参数
            for k, v in meta.items():
                data[k] = v
            # NO.1 参数排序
            _my_sorted = sorted(data.items(), key=lambda data: data[0])
            # NO.2 排序后拼接字符串
            canonicalizedQueryString = ''
            for (k, v) in _my_sorted:
                canonicalizedQueryString += '%s=%s&' % (self._percent_encode(k), self._percent_encode(v))
            # NO.3 加密返回签名: Signature
            return self.abstract_algorithm_mapping(SignMethod)(canonicalizedQueryString)
        else:
            raise TypeError("Invalid sign parameters or meta")

    def _percent_encode(self, encodeStr):
        try:
            encodeStr = json.dumps(encodeStr, sort_keys=True)
        except:
            raise
        if isinstance(encodeStr, bytes):
            encodeStr = encodeStr.decode(sys.stdin.encoding or 'utf-8')
        res = quote(encodeStr.encode('utf-8'), '')
        res = res.replace('+', '%20')
        res = res.replace('*', '%2A')
        res = res.replace('%7E', '~')
        return res


class EncryptedCommunicationClient(EncryptedCommunicationMix):
    """客户端：主要是公钥加密"""

    def __init__(self, PublicKey):
        """初始化客户端请求类

        :param PublicKey: str: RSA的pkcs1或pkcs8格式公钥
        """
        self.AESKey = self.genAesKey()
        self.PublicKey = PublicKey

    def clientEncrypt(self, post, **signargs):
        """客户端发起加密请求通信 for NO.1

        :param post: dict: 请求的数据

        :param signIndex: str: 参与排序加签的键名，False表示不签名，None时表示加签post中所有数据，非空时请用逗号分隔键名(字符串)

        :param signMethod: str: 签名算法，可选md5、sha1、sha256

        :returns: dict: {key=RSAKey, value=加密数据}
        """
        if not (post and isinstance(post, dict)):
            raise TypeError("Invalid post data")
        # 深拷贝post
        postData = copy.deepcopy(post)
        # 使用RSA公钥加密AES密钥获取RSA密文作为密钥
        RSAKey = RSAEncrypt(self.PublicKey, self.AESKey)
        # 定义元数据
        metaData = dict(Timestamp=self.get_current_timestamp(), SignatureVersion="v1", SignatureMethod=signargs.get("signMethod", "md5"), SignatureIndex=signargs.get("signIndex", None))
        # 对请求数据签名
        metaData.update(Signature=self.sign(postData, metaData))
        # 对请求数据填充元信息
        postData.update(__meta__=metaData)
        # 使用AES加密请求数据
        JsonAESEncryptedData = AESEncrypt(self.AESKey, json.dumps(postData, separators=(',', ':')), output_type="str")
        return dict(key=RSAKey, value=JsonAESEncryptedData)

    def clientDecrypt(self, encryptedRespData):
        """客户端获取服务端返回的加密数据并解密 for NO.4

        :param encryptedRespData: dict: 服务端返回的加密数据，其格式应该是 {data: AES加密数据}

        :raises: TypeError,SignError

        :returns: 解密验签成功后，返回服务端的消息原文
        """
        if encryptedRespData and isinstance(encryptedRespData, dict) and \
                "data" in encryptedRespData:
            JsonAESEncryptedData = encryptedRespData["data"]
            respData = json.loads(AESDecrypt(self.AESKey, JsonAESEncryptedData, output_type="str"))
            metaData = respData.pop("__meta__")
            Signature = metaData.pop("Signature")
            SignData = self.sign(respData, metaData)
            if Signature == SignData:
                return respData
            else:
                raise SignError("Signature verification failed")
        else:
            raise TypeError("Invalid encrypted resp data")


class EncryptedCommunicationServer(EncryptedCommunicationMix):
    """服务端：主要是私钥解密"""

    def __init__(self, PrivateKey):
        """初始化服务端响应类

        :param PrivateKey: str: pkcs1格式私钥
        """
        self.PrivateKey = PrivateKey
        # AESKey是服务端解密时解码的AESKey，即客户端加密时自主生成的AES密钥
        self.AESKey = None

    def serverDecrypt(self, encryptedPostData):
        """服务端获取请求数据并解密 for NO.2

        :param encryptedPostData: dict: 请求的加密数据

        :raises: TypeError,SignError

        :returns: 解密后的请求数据原文
        """
        if encryptedPostData and isinstance(encryptedPostData, dict) and \
            "key" in encryptedPostData and \
                "value" in encryptedPostData:
            RSAKey = encryptedPostData["key"]
            self.AESKey = RSADecrypt(self.PrivateKey, RSAKey)
            JsonAESEncryptedData = encryptedPostData["value"]
            postData = json.loads(AESDecrypt(self.AESKey, JsonAESEncryptedData, output_type="str"))
            metaData = postData.pop("__meta__")
            Signature = metaData.pop("Signature")
            SignData = self.sign(postData, metaData)
            if Signature == SignData:
                return postData
            else:
                raise SignError("Signature verification failed")
        else:
            raise TypeError("Invalid encrypted post data")

    def serverEncrypt(self, resp, **signargs):
        """服务端返回加密数据 for NO.3

        :param resp: dict: 服务端返回的数据，目前仅支持dict

        :param signIndex: tuple,list: 参与排序加签的键名，False表示不签名，None时表示加签resp中所有数据，非空时请用逗号分隔键名(字符串)

        :param signMethod: str: 签名算法，可选md5、sha1、sha256

        :raises: TypeError,ValueError

        :returns: dict: 返回dict，格式是 {data: AES加密数据}
        """
        if self.AESKey:
            if resp and isinstance(resp, dict):
                respData = copy.deepcopy(resp)
                metaData = dict(Timestamp=self.get_current_timestamp(), SignatureVersion="v1", SignatureMethod=signargs.get("signMethod", "md5"), SignatureIndex=signargs.get("signIndex", None))
                metaData.update(Signature=self.sign(respData, metaData))
                respData.update(__meta__=metaData)
                JsonAESEncryptedData = AESEncrypt(self.AESKey, json.dumps(respData, separators=(',', ':')), output_type="str")
                return dict(data=JsonAESEncryptedData)
            else:
                raise TypeError("Invalid resp data")
        else:
            raise ValueError("Invalid AESKey")
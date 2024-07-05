from PIL import Image
from math import ceil
import io

class Compress(object):

    def __init__(self, ignoreBy=102400, quality=60):
        self.img = None
        self.ignoreBy = ignoreBy
        self.quality = quality

    def setImg(self, img):
        self.img = img

    def computeScale(self):
        # 计算缩小的倍数
        srcWidth, srcHeight = self.img.size

        srcWidth = srcWidth + 1 if srcWidth % 2 == 1 else srcWidth
        srcHeight = srcHeight + 1 if srcHeight % 2 == 1 else srcHeight

        longSide = max(srcWidth, srcHeight)
        shortSide = min(srcWidth, srcHeight)

        scale = shortSide / longSide
        if 1 >= scale > 0.5625:
            if longSide < 1664:
                return 1
            elif longSide < 4990:
                return 2
            elif 4990 < longSide < 10240:
                return 4
            else:
                return max(1, longSide // 1280)

        elif 0.5625 >= scale > 0.5:
            return max(1, longSide // 1280)

        else:
            return ceil(longSide / (1280.0 / scale))

    def compress(self, img):
        # 先调整大小，再调整品质
        # 首先，将 bytes 对象转换为一个图像对象
        img = Image.open(io.BytesIO(img))
        self.setImg(img)

        img_byte_arr = io.BytesIO()
        self.img.save(img_byte_arr, format=self.img.format)
        img_size = img_byte_arr.tell()

        if img_size <= self.ignoreBy:
            return img_byte_arr.getvalue()  # 返回压缩后的图像数据

        else:

            scale = self.computeScale()
            srcWidth, srcHeight = self.img.size
            cache = self.img.resize((srcWidth // scale, srcHeight // scale),
                                    Image.LANCZOS)
            return cache
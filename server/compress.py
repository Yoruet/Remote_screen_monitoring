from PIL import Image
import os
from os.path import getsize
from shutil import copyfile
from math import ceil
import io

class Compress(object):

    def __init__(self, ignoreBy=102400, quality=60):
        self.img = None
        self.ignoreBy = ignoreBy
        self.quality = quality

    def setImg(self, img):
        self.img = img

    def load(self):
        if self.img.mode == "RGB":
            self.type = "JPEG"
        elif self.img.mode == "RGBA":
            self.type = "PNG"
        else:  # 其他的图片就转成JPEG
            self.img = self.img.convert("RGB")
            self.type = "JPEG"

    def computeScale(self):
        # 计算缩小的倍数
        srcWidth, srcHeight = self.img.size

        srcWidth = srcWidth + 1 if srcWidth % 2 == 1 else srcWidth
        srcHeight = srcHeight + 1 if srcHeight % 2 == 1 else srcHeight

        longSide = max(srcWidth, srcHeight)
        shortSide = min(srcWidth, srcHeight)

        scale = shortSide / longSide
        if (scale <= 1 and scale > 0.5625):
            if (longSide < 1664):
                return 1
            elif (longSide < 4990):
                return 2
            elif (longSide > 4990 and longSide < 10240):
                return 4
            else:
                return max(1, longSide // 1280)

        elif (scale <= 0.5625 and scale > 0.5):
            return max(1, longSide // 1280)

        else:
            return ceil(longSide / (1280.0 / scale))

    def compress(self, img):
        # self.setImg(img)
        # 先调整大小，再调整品质
        # 假设 img_data 是图像数据的 bytes 对象
        # 首先，将 bytes 对象转换为一个图像对象
        img = Image.open(io.BytesIO(img))
        self.setImg(img)  # 假设这个方法设置了 self.img 为图像对象

        # 然后，像之前一样处理图像
        img_byte_arr = io.BytesIO()
        self.img.save(img_byte_arr, format=self.img.format)
        img_size = img_byte_arr.tell()

        if img_size <= self.ignoreBy:
            return img_byte_arr.getvalue()  # 返回压缩后的图像数据
        # if getsize(self.img) <= self.ignoreBy:
        #     return self.img

        else:
            self.load()

            scale = self.computeScale()
            srcWidth, srcHeight = self.img.size
            cache = self.img.resize((srcWidth // scale, srcHeight // scale),
                                    Image.LANCZOS)
            return cache


if __name__ == '__main__':

    compressor = Luban()
    compressor.compress()
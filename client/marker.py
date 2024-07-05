#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import math
from PIL import Image, ImageFont, ImageDraw, ImageEnhance, ImageChops, ImageOps

# 固定参数
file_path = './1.png'  # 替换为你的图片路径
out = './output'  # 输出目录，不存在时会创建
mark_text = "监控中"
color = "#8B8B1B"
space = 75
angle = 30
font_family = './font/青鸟华光简琥珀.ttf'
font_height_crop = 1.2
size = 50
opacity = 0.15
quality = 80


def add_mark(image, mark):
    '''
    添加水印，然后保存图片
    '''
    im = ImageOps.exif_transpose(image)
    return mark(im)


def set_opacity(im, opacity):
    '''
    设置水印透明度
    '''
    assert 0 <= opacity <= 1, "Opacity must be between 0 and 1"

    alpha = im.split()[3]
    alpha = ImageEnhance.Brightness(alpha).enhance(opacity)
    im.putalpha(alpha)
    return im


def crop_image(im):
    '''裁剪图片边缘空白'''
    bg = Image.new('RGBA', im.size)
    diff = ImageChops.difference(im, bg)
    del bg
    bbox = diff.getbbox()
    if bbox:
        return im.crop(bbox)
    return im


def gen_mark():
    '''
    生成mark图片，返回添加水印的函数
    '''
    width = len(mark_text) * size
    height = round(size * float(font_height_crop))

    # 创建水印图片
    mark = Image.new('RGBA', (width, height))
    draw = ImageDraw.Draw(mark)
    draw.text((0, 0), mark_text, fill=color, font=ImageFont.truetype(font_family, size))
    del draw

    # 裁剪空白
    mark = crop_image(mark)

    # 透明度
    mark = set_opacity(mark, opacity)

    def mark_im(im):
        c = int(math.sqrt(im.size[0] ** 2 + im.size[1] ** 2))
        mark2 = Image.new('RGBA', (c, c))

        y, idx = 0, 0
        while y < c:
            x = -int((mark.size[0] + space) * 0.5 * idx)
            idx = (idx + 1) % 2
            while x < c:
                mark2.paste(mark, (x, y))
                x += mark.size[0] + space
            y += mark.size[1] + space

        mark2 = mark2.rotate(angle)
        if im.mode != 'RGBA':
            im = im.convert('RGBA')
        im.paste(mark2, (int((im.size[0] - c) / 2), int((im.size[1] - c) / 2)), mask=mark2.split()[3])
        del mark2
        return im

    return mark_im


def main():
    mark = gen_mark()
    image = Image.open(file_path)
    add_mark(image, mark).save("./2.png")


if __name__ == '__main__':
    main()

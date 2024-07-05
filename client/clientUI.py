import base64
import socket
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO

import requests
from PIL import ImageGrab
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtWidgets import QMainWindow, QWidget
from flask import Flask, jsonify, request, json

from EncryptedCommunication import EncryptedCommunicationClient
from compress import Compress
from frame import Ui_frame
from mainwindow import Ui_MainWindow
from signup_client import Ui_Signup_client
from marker import gen_mark, add_mark

"""获取主机ip地址"""
def get_public_ip():
    ip = socket.gethostbyname(socket.gethostname())
    return ip

"""获取主机的MAC地址"""
def get_mac_address():
    mac = ':'.join(['{:02x}'.format((uuid.getnode() >> i) & 0xff) for i in range(0, 8 * 6, 8)][::-1])
    return mac

"""从服务器获取公钥"""
def get_server_public_key():
    url = f"{server_url}/generate_keys"
    # 发送的信息
    request = {
        "username": username_input
    }
    response = requests.post(url, data=request).json()
    if response['status_code'] == 200:
        public_key_return = response['public_key']
        return public_key_return
    else:
        raise Exception("Failed to retrieve public key from server")

"""一些全局变量"""
public_key = None #初始无公钥
monitor_frequency = 5  # 初始监控频率为5秒
server_ip = '10.21.143.46'  # 服务器IP
server_port = 5000  # 服务器端口
server_url = f'http://{server_ip}:{server_port}'  #服务器url
username_input = None
password_input = None
ip_address = get_public_ip()     #得到ip地址
mac_address = get_mac_address()  #得到mac地址
running = False   #初始运行状态是不运行

"""用于监听更改频率的线程"""
app = Flask(__name__)
def run_flask_server():
    # 在子进程中启动 Flask 服务器
    try:
        app.run(debug=False, host='0.0.0.0', port=6666, threaded=True)
    except Exception as e:
        print('error::' + str(e))

"""接收更改的频率并应用"""
@app.route('/change_frequency', methods=['POST'])
def change_frequency():
    global monitor_frequency
    data = request.form
    monitor_frequency = int(data["monitor_frequency"])
    myMainWindow.show_frequency()
    return jsonify({"message": "修改成功", "status_code": 200})

"""登录注册主界面"""
class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setupUi(self)
        self.monitoring_thread = None
        self.lock = threading.Lock()

    """登录按钮发送请求"""
    def signin_pushbutton(self):
        global username_input, public_key, password_input, server_url, ip_address, mac_address, monitor_frequency, running
        # 获取用户名和密码
        username_input = self.Username.text()
        password_input = self.Password.text()
        if username_input and password_input:
            try:
                # 从服务器获取公钥
                public_key = get_server_public_key()
                # 创建客户端加密通信实例
                ec = EncryptedCommunicationClient(public_key)
                url = f"{server_url}/login"
                # 加密的信息
                request_temp = {
                    "password": password_input,
                    "ip_address": ip_address,
                    "mac_address": mac_address
                }
                encryptedPost = ec.clientEncrypt(request_temp)
                # 发送的信息
                request = {
                    "username": username_input,
                    "encryptedPost": str(encryptedPost)
                }
                response = requests.post(url, data=request).json()
                if response['status_code'] == 200:
                    QtWidgets.QMessageBox.information(self, '登录成功', '登录成功！')
                    # 界面跳转到登录后界面并启动截屏
                    self.close()
                    mySigninWindow.show()
                    self.Username.clear()
                    self.Password.clear()
                    running = True
                    self.start_monitoring()
                elif response['status_code'] == 401:
                    QtWidgets.QMessageBox.warning(self, '登录失败', '用户名或密码错误')
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, '错误', f'无法连接到服务器: {e}')
        else:
            QtWidgets.QMessageBox.warning(self, '输入错误', '请输入用户名和密码')

    """启动监控线程"""
    def start_monitoring(self):
        self.monitoring_thread = threading.Thread(target=self.monitor)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()

    """监控函数，定时截屏并发送"""
    def monitor(self):
        while running:
            self.capture_screen()
            time.sleep(monitor_frequency)

    """获得屏幕截图压缩编码并发送"""
    def capture_screen(self):
        try:
            screenshot = ImageGrab.grab()
            # 添加水印
            mark = gen_mark()
            screenshot = add_mark(screenshot, mark).convert('RGB')
            with self.lock:
                # 转化为JPEG格式
                with BytesIO() as output:
                    screenshot.save(output, format='JPEG')
                    img_data = output.getvalue()
                    compressor = Compress()
                    compressor.compress(img_data)
                # 使用base64编码
                compressed_data = base64.b64encode(img_data).decode('utf-8')
                self.send_screenshot(compressed_data)
        except Exception as e:
            print(f'截图发送错误: {e}')

    """发送屏幕截图并显示在客户端"""
    def send_screenshot(self, img_data):
        global username_input, public_key, password_input, server_url, monitor_frequency
        try:
            # 从服务器获取公钥
            public_key = get_server_public_key()
            # 创建客户端加密通信实例
            ec = EncryptedCommunicationClient(public_key)
            url = f"{server_url}/receive_image"
            # 加密的信息
            request_temp = {
                "image_data": img_data
            }
            encryptedPost = ec.clientEncrypt(request_temp)
            # 发送的信息
            request = {
                "username": username_input,
                "encryptedPost": str(encryptedPost)
            }
            response = requests.post(url, data=request).json()
            if response["status_code"] == 200:
                print('图像发送成功.')
                # 在用户界面显示一些信息
                self.show_screenshot(base64.b64decode(img_data))
                self.show_frequency()
            else:
                print('图像发送失败.')
        except Exception as e:
            print(f'图像发送错误: {e}')

    """显示发送频率"""
    def show_frequency(self):
        font = QFont()
        font.setPointSize(18)
        mySigninWindow.label_3.setFont(font)
        mySigninWindow.label_3.setText(f" {monitor_frequency} 秒")

    """显示发送的屏幕截图"""
    def show_screenshot(self, img_data, max_width=850, max_height=600):
        pixmap = QPixmap()
        pixmap.loadFromData(img_data)
        scaled_pixmap = pixmap.scaled(max_width, max_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        mySigninWindow.monitored.setPixmap(scaled_pixmap)
        mySigninWindow.monitored.setAlignment(Qt.AlignCenter)
        mySigninWindow.monitored.adjustSize()

    """注册按钮点击进入注册界面"""
    def signup_pushbutton(self):
        self.close()
        mySignupWindow.show()


"""注册界面"""
class SignupWindow(QWidget, Ui_Signup_client):
    def __init__(self):
        super(SignupWindow, self).__init__()
        self.server_username = None
        self.setupUi(self)
        self.lineEdit.setText(ip_address)
        self.lineEdit_2.setText(mac_address)

    """确认按钮发送注册请求"""
    def sure_pushbutton(self):
        global username_input, public_key, password_input, server_url, ip_address, mac_address
        # 获取输入的用户名和密码
        username_input = self.username.text()
        password_input = self.password.text()
        self.server_username = self.lineEdit_3.text()
        if username_input and password_input and password_input == self.surepassword.text():
            try:
                # 从服务器获取公钥
                public_key = self.get_server_public_key_register()
                # 创建客户端加密通信实例
                ec = EncryptedCommunicationClient(public_key)
                url = f"{server_url}/register"
                # 加密的信息
                request_temp = {
                    "password": password_input,
                    "ip_address": ip_address,
                    "mac_address": mac_address,
                }
                encryptedPost = ec.clientEncrypt(request_temp)
                # 发送的信息
                request = {
                    "username": username_input,
                    "server_username": self.server_username,
                    "encryptedPost": str(encryptedPost)
                }
                response = requests.post(url, data=request).json()
                if response['status_code'] == 200:
                    QtWidgets.QMessageBox.information(self, '注册成功', '注册成功！')
                    self.username.clear()
                    self.password.clear()
                    self.surepassword.clear()
                    self.show()
                elif response['status_code'] == 400:
                    QtWidgets.QMessageBox.warning(self, '注册失败', '注册失败，请重试')
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, '注册失败', f'已存在相同用户名')
        elif password_input == self.surepassword.text():
            QtWidgets.QMessageBox.warning(self, '输入错误', '请输入用户名或密码')
        else:
            QtWidgets.QMessageBox.warning(self, '输入错误', '两次密码不一致')


    """返回登录按钮点击返回登录注册主界面"""
    def back_pushbutton(self):
        self.close()
        myMainWindow.show()

    """注册时请求公钥"""
    def get_server_public_key_register(self):
        url = f"{server_url}/generate_keys"
        # 发送的信息
        request = {
            "server_username": self.server_username,
            "username": username_input
        }
        response = requests.post(url, data=request).json()
        if response['status_code'] == 200:
            public_key_return = response['public_key']
            return public_key_return
        else:
            raise Exception("Failed to retrieve public key from server")

"""登录后界面"""
class SigninWindow(QWidget, Ui_frame):
    def __init__(self):
        super(SigninWindow, self).__init__()
        self.tray_icon = None
        self.init_tray()
        self.setupUi(self)

    """登出按钮点击退出登录返回登陆注册主界面"""
    def exit_pushbutton(self):
        global username_input, public_key, password_input, server_url, mac_address, running
        try:
            url = f"{server_url}/logout"
            # 发送的信息
            request = {
                "username": username_input,
            }
            response = requests.post(url, data=request).json()
            if response["status_code"] == 200:
                running = False
                self.hide()
                if myMainWindow.monitoring_thread and myMainWindow.monitoring_thread.is_alive():
                    myMainWindow.monitoring_thread.join()
                self.tray_icon.hide()
                myMainWindow.show()
                QtWidgets.QMessageBox.information(self, '登出成功', '登出成功！')
            else:
                QtWidgets.QMessageBox.warning(self, '登出失败', '登出失败，请重试')
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, '错误', f'无法连接到服务器: {e}')

    """托盘图标设置"""
    def init_tray(self):
        self.tray_icon = QtWidgets.QSystemTrayIcon(self)
        self.tray_icon.setIcon(QtGui.QIcon('./assert/icon.ico'))
        tray_menu = QtWidgets.QMenu()
        quit_action = tray_menu.addAction("退出")
        quit_action.triggered.connect(self.quit)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    """退出程序逻辑"""
    def quit(self):
        self.exit_pushbutton()
        # QtWidgets.QApplication.quit()

    """重写关闭事件，最小化到托盘"""
    def closeEvent(self, event):
        if self.tray_icon.isVisible():
            self.hide()
            event.ignore()
            self.tray_icon.showMessage(
                "远程屏幕监控客户端",
                "客户端最小化到托盘。要退出程序，请使用托盘菜单。",
                QtWidgets.QSystemTrayIcon.Information,
                2000
            )

    """托盘图标点击事件"""
    def on_tray_icon_activated(self, reason):
        if reason == 3:
            if self.isMinimized():
                self.showNormal()
            self.show()

if __name__ == '__main__':
    thread_process = threading.Thread(name = "thread_process", target=run_flask_server)
    thread_process.start()
    print(1)
    app_qt = QtWidgets.QApplication(sys.argv)
    myMainWindow = MainWindow()
    mySignupWindow = SignupWindow()
    mySigninWindow = SigninWindow()
    myMainWindow.show()
    sys.exit(app_qt.exec_())
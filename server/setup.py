from datetime import datetime,timedelta
import glob
import json
import re
import socket
import threading
import time
import uuid
from PyQt5 import QtWidgets
from PyQt5.QtCore import QStringListModel, pyqtSignal, QTimer, QUrl
from PyQt5.QtWebSockets import QWebSocket
from PyQt5.QtWidgets import QMessageBox, QVBoxLayout, QListView, QLabel, QLineEdit, QPushButton, QTextEdit, QWidget, QComboBox
from PyQt5.QtCore import Qt, pyqtSlot,pyqtSignal,QObject
from PyQt5.QtGui import QPixmap
import os
import sys

import requests
from signup_server import Ui_signup_server
from signin_server import Ui_signin_server
from monitor import Ui_monitor
from freq import Ui_freq
from his import Ui_his
from db_handler import get_db,get_ip_from_username
from List import Ui_list

"""获取主机ip地址"""
def get_public_ip():
    ip = socket.gethostbyname(socket.gethostname())
    return ip

"""获取主机的MAC地址"""
def get_mac_address():
    mac = ':'.join(['{:02x}'.format((uuid.getnode() >> i) & 0xff) for i in range(0, 8 * 6, 8)][::-1])
    return mac
ip_address = get_public_ip()      #得到ip地址
mac_address = get_mac_address()  #得到mac地址

from http.server import BaseHTTPRequestHandler, HTTPServer

class RequestHandler(BaseHTTPRequestHandler):
    #接收回传的登录/登出信息
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"POST request received.")

        # 使用全局变量或某种机制来获取HttpServer的实例
        # global http_server_instance
        try:
            http_server_instance.request_received.emit(post_data.decode('utf-8'))
            #发出登录/登出信号
        except Exception as e:
            print(e)
        print(f"Received POST data: {post_data.decode('utf-8')}")
class HttpServer(QObject):
    request_received = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.server = HTTPServer(('localhost', 7842), RequestHandler)
        
        self.thread = threading.Thread(target=self.run)
        self.thread.start()

    def run(self):
        self.server.serve_forever()

# 服务器用户注册页面
class SignupServerImp(QtWidgets.QWidget, Ui_signup_server):
    def __init__(self, parent=None):
        super(SignupServerImp, self).__init__(parent)
        self.setupUi(self)
        self.lineEdit.setText(ip_address)
        self.lineEdit_2.setText(mac_address)
    def signup_sure_pushbutton(self):

        # print("signup_sure_pushbutton")
        # 在这里添加注册确认按钮的逻辑
        username = self.username.text()
        password = self.password.text()
        ip_address = socket.gethostbyname(socket.gethostname())
        mac_address = ':'.join(re.findall('..', '%012x' % uuid.getnode()))
        if username == "" or password == "":
            QMessageBox.information(self, "提示", "用户名或密码不能为空", QMessageBox.Yes)
            return
        try:
            request = {
                "username": username,
                "password": password,
                "ip_address": ip_address,
                "mac_address": mac_address
            }
            print(request)
            response = requests.post("http://127.0.0.1:5000/Sregister", data=request).json()
            print(response)
            if response["status_code"] == 200:
                QMessageBox.information(self, "提示", "注册成功", QMessageBox.Yes)
            else:
                QMessageBox.information(self, "提示", "注册失败", QMessageBox.Yes)
        except Exception as e:
            print(e)
            QMessageBox.information(self, "提示", "服务异常", QMessageBox.Yes)
            return
        self.hide()
        signin_server.show()

    def back_signin_pushbutton(self):
        # print("back_signin_pushbutton")
        # 在这里添加返回登录界面按钮的逻辑
        self.hide()
        signin_server.show()


# 服务器用户登录页面
class SigninServerImp(QtWidgets.QMainWindow, Ui_signin_server):
    signal_confirm = pyqtSignal(str)
    def __init__(self, parent=None):
        super(SigninServerImp, self).__init__(parent)
        self.setupUi(self)
        self.username_input = None

    def signin_pushbutton(self):
        username = self.username.text()
        self.username_input = username
        password = self.password.text()
        ip_address = socket.gethostbyname(socket.gethostname())
        mac_address = ':'.join(re.findall('..', '%012x' % uuid.getnode()))
        if username == "" or password == "":
            QMessageBox.information(self, "提示", "用户名或密码不能为空", QMessageBox.Yes)
            return

        try:
            request = {
                "username": username,
                "password": password,
                "ip_address": ip_address,
                "mac_address": mac_address
            }
            # print("here")
            response = requests.post("http://127.0.0.1:5000/Slogin", data=request).json()
            print(response)
            if response["status_code"] == 200:
                # 登录成功后跳转到监控界面

                self.hide()
                self.signal_confirm.emit(str(username))
                monitor.show()
            else:
                QMessageBox.information(self, "提示", "用户名或密码错误", QMessageBox.Yes)
                return
        except Exception as e:
            print(e)
            QMessageBox.information(self, "提示", "登录失败", QMessageBox.Yes)
            return

    def signup_pushbutton(self):
        # print("signup_pushbutton")
        # 在这里添加注册按钮的逻辑

        self.hide()
        signup_server.show()

# 监控界面（主界面）
class MonitorImp(QtWidgets.QWidget, Ui_monitor):
    update_usertree_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        super(MonitorImp, self).__init__(parent)
        self.setupUi(self)
        self.current_user = None
        self.serveruser = None
        self.timer = QTimer(self)
        signin_server.signal_confirm.connect(self.setServerUser)
        self.timer.timeout.connect(self.update_screenshot)
        self.timer.start(5000)
        self.counter = 0
        self.fomer_pic = None
        freq.frequency_sure_signal.connect(self.change_frequency) #修改频率信号
        # self.server = http_server_instance
        http_server_instance.request_received.connect(self.handle_request) #用户登录/登出信号
    #弹出登录/登出提示框
    def handle_request(self, data):
        # self.output.append(f"Received data: {data}")
        data = data.split('&')
        # 初始化字典来存储键值对
        data_dict = {}
        # 遍历键值对
        for pair in data:
            # 分割键和值
            key, value = pair.split('=')
            # 存储到字典中
            data_dict[key] = value
        print(data_dict["action"])
        print(f"Received data: {data}")
        if  data_dict["action"]=="login":
            QMessageBox.information(self, "提示", data_dict["username"]+"用户上线" )
        elif data_dict["action"]=="logout":
            QMessageBox.information(self,"提示",data_dict["username"]+"用户离线")    
    def update_screenshot(self):
        self.setCurrentUser(self.current_user)
        # pass
    def change_frequency(self,frequency):
        self.timer.stop()
        self.timer.start(frequency*1000)
    def client_tree_pushbutton(self):
        self.update_usertree_signal.emit(str(signin_server.username_input))
        listimp.user_set.connect(self.setCurrentUser)
        print("client_tree_pushbutton")
        # 在这里添加用户树的逻辑
    #设置当前监控的用户
    def setCurrentUser(self, qList1):
        if qList1 is not None:
            self.current_user = qList1
            print("setCurrentUser",qList1)
            
            # print(qList1)
            path = os.path.join(os.getcwd(), 'screenshots', self.serveruser,  qList1  )
            # # Get the list of image files in the directory
            image_files = glob.glob(os.path.join(path, "*.jpeg"))

            # # Sort the image files by their modification time in descending order
            sorted_image_files = sorted(image_files, key=os.path.getmtime, reverse=True)
            if len(sorted_image_files) == 0:
                print("No image files found")
                return
            # # Get the path of the latest image file
            latest_image_file = sorted_image_files[0]
            print(latest_image_file)
            pixmap = QPixmap(latest_image_file)
            resized_pixmap = pixmap.scaled(self.monitor_desk.width(), self.monitor_desk.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            # self.label.setPixmap(pixmap)
            self.monitor_desk.setPixmap(resized_pixmap)
            if self.fomer_pic is None:
                self.fomer_pic = latest_image_file
            if self.fomer_pic != latest_image_file:
                self.fomer_pic = latest_image_file
                self.counter = 0
            else:
                self.counter += 1
                if self.counter > 20:
                    self.counter = 0
                    self.timer.stop()
                    #接收到的图片没有更新，说明客户端已断开连接
                    QMessageBox.information(self, "提示", "客户端已断开连接", QMessageBox.Yes)
                    url = "http://127.0.0.1:5000/logout"
                    request = {
                        "username": self.current_user
                    }
                    response = requests.post(url, data=request).json()
                    print(response)
                    if response["status_code"] == 200:
                        print("logout success")
                    else:
                        print("logout failed")
            
    def setServerUser(self,serveruser):
        self.serveruser = serveruser
    def frequency_pushbutton(self):

        print("frequency_pushbutton")
        # 在这里添加调整频率的逻辑

    def history_pushbutton(self):
        print("history_pushbutton")
        # 在这里添加历史记录的逻辑

    def exit_pushbutton(self):
        # print("exit_pushbutton")
        # 在这里添加退出按钮的逻辑
        username = signin_server.username_input
        mac_address = ':'.join(re.findall('..', '%012x' % uuid.getnode()))
        try:
            request = {
                "username": username,
                "mac_address": mac_address
            }
            response = requests.post("http://127.0.0.1:5000/Slogout", data=request).json()
            if response["status_code"] == 200:
                # QMessageBox.information(self, "提示", "退出成功", QMessageBox.Yes)
                pass
            else:
                QMessageBox.information(self, "提示", "退出失败", QMessageBox.Yes)
        except Exception as e:
            print(e)
            QMessageBox.information(self, "提示", "服务异常", QMessageBox.Yes)
            return

        self.hide()
        signin_server.show()

#修改监控频率页面
class FreqImp(QtWidgets.QWidget, Ui_freq):
    frequency_sure_signal = pyqtSignal(int)
    def __init__(self, parent=None):
        super(FreqImp, self).__init__(parent)
        self.setupUi(self)

    def frequency_sure_pushbutton(self):
        try:
            username = listimp.currentuser
            print(username)
            db = next(get_db())
            ip = get_ip_from_username(db,username)
            url = "http://"+ip+":6666/change_frequency" #向客户端发送修改频率请求
            print(url)
            # print(self.spinBox.value())
            if self.spinBox.value() < 1:
                QMessageBox.information(self, "提示", "频率不能小于1", QMessageBox.Yes)
                return
            value = self.spinBox.value()
            request = {
                "monitor_frequency": value
            }
            response = requests.post(url, data=request).json()
            print(response)
            self.frequency_sure_signal.emit(value)
        except Exception as e:
            print(e)
        # if response["status_code"] == 200:
        #     QMessageBox.information(self, "提示", "修改成功", QMessageBox.Yes)
        #     pass
        # else:
        #     pass
            # QMessageBox.information(self, "提示", "修改失败", QMessageBox.Yes)
        

        # print("freq_sure_pushbutton:",self.spinBox.value())
        # 在这里添加频率确认按钮的逻辑

# 历史记录页面
class HisImp(QtWidgets.QWidget, Ui_his):
    def __init__(self, parent=None):
        super(HisImp, self).__init__(parent)
        self.setupUi(self)
        options = [] #下拉列表内容
        self.dropdown_menu.addItems(options)
        self.pageindex=0
        self.totalpages=0
        self.serverpath = os.path.join(os.getcwd(), 'screenshots')
        signin_server.signal_confirm.connect(self.setDropdownMenu)
        signin_server.signal_confirm.connect(self.setPath)
        signin_server.signal_confirm.connect(self.setdefaultimg)
        self.comboBox.addItems(["1分钟前","5分钟前","10分钟前","30分钟前","1小时前","1天前","1周前","1月前","1年前"])
        self.comboBoxContent = None
    def setPath(self,serveruser):
        self.serverpath = os.path.join(os.getcwd(), 'screenshots',serveruser)
    def setDropdownMenu(self,serveruser):
        print(serveruser)
        request = {"serveruser":serveruser}
        response = requests.post("http://127.0.0.1:5000/getUser",data=request).json()
        users  = eval(response['users'])
        self.dropdown_menu.addItems([user['username'] for user in users])
    def setdefaultimg(self,serveruser):
        imgfiles = self.search_img(self.selected_option)
        self.totalpages=len(imgfiles)//4
        self.show_screenshot(imgfiles)
    def delete_dropdown_menu_changed(self, index):
        # print("delete_dropdown_menu_changed")
        # print(self.comboBox.currentText())
        self.comboBoxContent = self.comboBox.currentText()
        # print("当前选中的选项是:", self.comboBoxContent)
    def delete_history_screenshots(self):
        username = self.selected_option
        self.comboBoxContent = self.comboBox.currentText()
        current_time = datetime.now()
        if self.comboBoxContent is None:
            return
        if self.comboBoxContent == "1分钟前":
            time_threshold = current_time - timedelta(minutes=1)
        elif self.comboBoxContent == "5分钟前":
            time_threshold = current_time - timedelta(minutes=5)
        elif self.comboBoxContent == "10分钟前":
            time_threshold = current_time - timedelta(minutes=10)
        elif self.comboBoxContent == "30分钟前":
            time_threshold = current_time - timedelta(minutes=30)
        elif self.comboBoxContent == "1小时前":
            time_threshold = current_time - timedelta(hours=1)
        elif self.comboBoxContent == "1天前":
            time_threshold = current_time - timedelta(days=1)
        elif self.comboBoxContent == "1周前":
            time_threshold = current_time - timedelta(weeks=1)
        elif self.comboBoxContent == "1月前":
            time_threshold = current_time - timedelta(weeks=4)
        elif self.comboBoxContent == "1年前":
            time_threshold = current_time - timedelta(weeks=52)
        time_threshold = time_threshold.timestamp()
        print(f"删除历史截图: {time_threshold}")
        print(self.serverpath,username)
        screenshot_dir = os.path.join(os.getcwd(), self.serverpath,username)
        print(f"删除历史截图: {screenshot_dir}")
        search_pattern = os.path.join(screenshot_dir, '*.jpeg')
        # 构建搜索模式，匹配该文件夹下的所有图像文件
        search_pattern = os.path.join(screenshot_dir, '*.jpeg')  # 假设图像文件以.png结尾
        # 使用glob.glob查找匹配的文件路径
        image_files = glob.glob(search_pattern)
        print(f"找到的图像文件: {image_files}")
        for image_file in image_files:
            timestamp = os.path.getmtime(image_file)
            
            image_time = (timestamp)
            
            if image_time < time_threshold:
                print(f"删除文件: {image_file}")
                os.remove(image_file)
        print("删除完成")
        imgfiles = self.search_img(self.selected_option)
        self.totalpages=len(imgfiles)//4
        self.show_screenshot(imgfiles)

    def search_img(self,user_name):
        # 定义screenshot目录的路径
        screenshot_dir = os.path.join(os.getcwd(), self.serverpath,user_name)
        # 构建搜索模式，匹配该文件夹下的所有图像文件
        search_pattern = os.path.join(screenshot_dir, '*.jpeg')  # 假设图像文件以.png结尾
        # 使用glob.glob查找匹配的文件路径
        image_files = glob.glob(search_pattern)
        
        return image_files  # 返回图像路径列表
        

    def on_dropdown_menu_changed(self, index):
        
        
        self.selected_option = self.dropdown_menu.currentText()
        # print("当前选中的选项是:", self.selected_option)
        imgfiles = self.search_img(self.selected_option)
        self.totalpages=len(imgfiles)//4
        self.show_screenshot(imgfiles)
            
    
    def pgup_pushbutton(self): 
        self.pageindex-=1
        if self.pageindex<0:
            self.pageindex=0
        imgfiles = self.search_img(self.selected_option)
        self.totalpages=len(imgfiles)//4
        self.show_screenshot(imgfiles)
        # print("pgup_pushbutton")
        # 在这里添加向上翻页的逻辑
    def pgdn_pushbutton(self):
        self.pageindex+=1
        print(self.pageindex)
        if self.pageindex>self.totalpages:
            self.pageindex=self.totalpages
        imgfiles = self.search_img(self.selected_option)
        self.totalpages=len(imgfiles)//4
        self.show_screenshot(imgfiles)
        # print("pgdn_pushbutton")
        # 在这里添加向下翻页的逻辑
    def show_screenshot(self, imgfiles,max_width=421, max_height=321):
    # def show_screenshot(self, pixmaps_img,imgfiles):       
        # 保留下面这行
        try:
            print(self.pageindex)
        except Exception as e:
            print("Exception here",e)
            return
        
        self.photo_1.clear()
        self.photo_2.clear()
        self.photo_3.clear()
        self.photo_4.clear()
        imgfiles = sorted(imgfiles, key=lambda x: x, reverse=True)

        if (self.pageindex)*4+1>len(imgfiles): 
            # if self.photo_1.pixmap() is not None:  # 检查是否已设置pixmap
            self.photo_1.image_path = None
            self.photo_2.image_path = None
            self.photo_3.image_path = None
            self.photo_4.image_path = None
            return
        # print("self.pageindex",self.pageindex)
        # print(len(pixmaps_img))
        scaled_pixmap = QPixmap(imgfiles[(self.pageindex)*4]).scaled(max_width, max_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        self.photo_1.setPixmap(scaled_pixmap)
        self.photo_1.setAlignment(Qt.AlignCenter)

        self.photo_1.adjustSize()
        try:
            self.photo_1.image_path = imgfiles[(self.pageindex)*4]
            # print(self.photo_1.image_path)
            # print(imgfiles[self.pageindex*4])
        except Exception as e:
            print(e)
        if self.pageindex*4+2>len(imgfiles):
            # if self.photo_2.pixmap() is not None:  # 检查是否已设置pixmap
            # self.photo_2.clear()
            # self.photo_3.clear()
            # self.photo_4.clear()
            self.photo_2.image_path = None
            self.photo_3.image_path = None
            self.photo_4.image_path = None
            return
        scaled_pixmap = QPixmap(imgfiles[(self.pageindex)*4]).scaled(max_width, max_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        # scaled_pixmap = pixmaps_img[self.pageindex*4+1]
        self.photo_2.setPixmap(scaled_pixmap)
        self.photo_2.setAlignment(Qt.AlignCenter)
        self.photo_2.adjustSize()
        self.photo_2.image_path = imgfiles[self.pageindex*4+1]
        if self.pageindex*4+3>len(imgfiles):
            # if self.photo_3.pixmap() is not None:
            # self.photo_3.clear()
            # self.photo_4.clear()
            self.photo_3.image_path = None
            self.photo_4.image_path = None
            return
        scaled_pixmap = QPixmap(imgfiles[(self.pageindex)*4]).scaled(max_width, max_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        # scaled_pixmap = pixmaps_img[self.pageindex*4+2]
        self.photo_3.setPixmap(scaled_pixmap)
        self.photo_3.setAlignment(Qt.AlignCenter)
        self.photo_3.adjustSize()
        self.photo_3.image_path = imgfiles[self.pageindex*4+2]
        if self.pageindex*4+4>len(imgfiles):
            # if self.photo_4.pixmap() is not None:
            # self.photo_4.clear()
            self.photo_4.image_path = None
            return
        scaled_pixmap = QPixmap(imgfiles[(self.pageindex)*4]).scaled(max_width, max_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        # scaled_pixmap = pixmaps_img[self.pageindex*4+3] 
        self.photo_4.setPixmap(scaled_pixmap)
        self.photo_4.setAlignment(Qt.AlignCenter)
        self.photo_4.adjustSize()
        self.photo_4.image_path = imgfiles[self.pageindex*4+3]
# 用户列表页面        
class ListImp(QtWidgets.QWidget, Ui_list):
    user_set = pyqtSignal(str)
    def __init__(self, parent=None):
        super(ListImp, self).__init__(parent)
        self.ui = Ui_list()
        self.ui.setupUi(self)
        signin_server.signal_confirm.connect(self.setUserTree)
        monitor.update_usertree_signal.connect(self.updateUserTree)
        self.currentuser = None
    def client_tree_set(self,item):
        QMessageBox.information(self, "QListView", "你选择了: " + self.qList[item.row()])
        print("点击的是：" + str(item.row()))
        self.user_set.emit(str(self.qList[item.row()]))
        self.currentuser = str(self.qList[item.row()])

    def setUserTree(self,serveruser):
        print("serveruser",serveruser)
        slm = QStringListModel()  # 创建mode
        request = {"serveruser":serveruser}
        response = requests.post("http://127.0.0.1:5000/getUser",data=request).json()
        users  = eval(response['users'])
        self.qList = []
        for user in users:
            self.qList.append(str(user['username']))
        slm.setStringList(self.qList)  # 将数据设置到model
        self.ui.listView.setModel(slm)  ##绑定 listView 和 model
    def updateUserTree(self,serveruser):
        slm = QStringListModel()  # 创建mode
        request = {"serveruser": serveruser}
        response = requests.post("http://127.0.0.1:5000/getUser", data=request).json()
        # print(response)
        users = eval(response['users'])
        self.qList = []
        self.res = []
        for user in users:
            online = ""
            if user['online'] is True:
                online = "online:"
            else:
                online = "offline:"
            self.qList.append(str(user['username']))
            self.res.append(online+str(user['username']))
        slm.setStringList(self.res)  # 将数据设置到model
        self.ui.listView.setModel(slm)  ##绑定 listView 和 model
if __name__ == "__main__":
    # import sys
    app = QtWidgets.QApplication(sys.argv)
    signup_server = SignupServerImp()
    http_server_instance = HttpServer()
    signin_server = SigninServerImp()
    signin_server.show()
    freq = FreqImp()
    monitor = MonitorImp()
    listimp = ListImp()
   
    
    his = HisImp()
    
    signup_server.pushButton.clicked.connect(
        lambda: {signup_server.hide(), signin_server.show()}
        # lambda:signin_server.show()
    )
    signup_server.pushButton_2.clicked.connect(
        lambda: {signup_server.hide(), signin_server.show()}
    )
    # login
    # signin_server.pushButton.clicked.connect(
    #     lambda:{signin_server.hide(), monitor.show()}
    # )
    # signin_server.pushButton_2.clicked.connect(
    #     lambda:{signin_server.hide(), signup_server.show()}
    # )
    monitor.pushButton.clicked.connect(
        lambda: {listimp.show()}
    )
    monitor.pushButton_2.clicked.connect(
        lambda: {freq.show()}
    )

    monitor.pushButton_4.clicked.connect(
        lambda: {his.show()}
    )
    freq.pushButton.clicked.connect(
        lambda: {freq.hide(), monitor.show()}
    )

    sys.exit(app.exec_())


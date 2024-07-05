import os
import base64
import queue
import time
from urllib import response
# from flask_socketio import SocketIO, emit,send

import zlib
import json
from flask import Flask, request, jsonify, make_response, g, session
import requests
from EncryptedCommunication import EncryptedCommunicationServer
from RSA import generate_rsa_keys
import threading
from db_handler import get_db, register_user, login_user, logout_user, register_serveruser, login_serveruser, logout_serveruser, from_user_get_serveruser,get_username_from_serveruser

app = Flask(__name__)

# 全局变量
public_key = None
private_key = None

server_username = 'TEST'
services = ["generate_keys", "receive_image"]

# 初始化密钥存储结构
keys_storage = {}

# 生成密钥的函数
def generate_keys_for_user(username, server_username):
    global keys_storage
    identifier = f"{username}@{server_username}"
    public_key, private_key = generate_rsa_keys()
    keys_storage[identifier] = {
        "public_key": public_key,
        "private_key": private_key
    }
    return public_key, private_key
# 检索密钥的函数
def get_keys_for_user(username, server_username):
    identifier = f"{username}@{server_username}"
    keys = keys_storage.get(identifier)
    if keys:
        return keys["public_key"], keys["private_key"]
    else:
        return None, None


# 使用 g 对象存储请求期间的数据库连接
@app.before_request
def before_request():
    g.db = next(get_db())

# 在请求结束时释放 g 对象中的数据库连接
@app.teardown_request
def teardown_request(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

#用户注册
@app.route('/register', methods=['POST'])
def register():
    db = g.db
    data = request.form
    username = data["username"]
    print("username:",username)
    server_username = data["server_username"]
    encrypted_data = eval(data["encryptedPost"])
    # print("encrypted_data:",encrypted_data)
    public_key, private_key = get_keys_for_user(username, server_username)
    if not server_username:
        return jsonify({'message': '用户未绑定', "status_code": 404})
    #获取加密通信实例
    sc = EncryptedCommunicationServer(private_key)
    try:
        data_extra = sc.serverDecrypt(encrypted_data)
    except Exception as e:
        app.logger.error("解密失败：%s" % str(e))
        return jsonify({"error": "Decryption failed", "status_code": 500})
    print("here")
    password = data_extra.get('password')
    ip_address = data_extra.get('ip_address')
    mac_address = data_extra.get('mac_address')
    print("here1")
    if not username or not password or not ip_address or not mac_address or not server_username:
        return jsonify({'message': '注册信息有误', "status_code": 400})

    user = register_user(db, username, password, mac_address, server_username)
    if user is not None:
        return jsonify({'message': '注册成功', "status_code": 200})
    else:
        return jsonify({'message': '注册失败', "status_code": 500})

#用户登录
@app.route('/login', methods=['POST'])
def login():
    db = g.db
    data = request.form
    username = data['username']
    server_username = from_user_get_serveruser(db, username)
    public_key, private_key = get_keys_for_user(username, server_username)
    sc = EncryptedCommunicationServer(private_key)
    print("data:",data)
    encrypted_data = eval(data["encryptedPost"])
    print("encrypted_data:",encrypted_data)
    try:
        data_extra = sc.serverDecrypt(encrypted_data)
    except Exception as e:
        app.logger.error("解密失败：%s" % str(e))
        return jsonify({"error": "Decryption failed", "status_code": 500})

    
    password = data_extra.get('password')
    # ip_address = data_extra.get('ip_address')
    ip_address = request.remote_addr
    mac_address = data_extra.get('mac_address')
    if not username or not password or not mac_address or not ip_address:
        return jsonify({'message': '登录信息有误', "status_code": 400})
    
    success = login_user(db, username, password, ip_address)
    if success is not None:

        url ="http://127.0.0.1:7842"
        #向前端发送登录信息，提示用户登录
        response = requests.post(url, data={"username":username,"action":"login"})
        print(response.text)
        print("login")
        return jsonify({'message': '登录成功', "status_code": 200})
    else:
        return jsonify({'message': '用户名或密码错误', "status_code": 401})

@app.route('/logout', methods=['POST'])
def logout():
    db = g.db
    data = request.form
    username = data["username"]
    if not username :
        return jsonify({'message': '登出信息有误', "status_code": 400})

    success = logout_user(db, username)
    if success is not None:
        #向前端发送登出信息，提示用户登出
        url ="http://127.0.0.1:7842"
        response = requests.post(url, data={"username":username,"action":"logout"})
        print(response.text)
        print("logout")
        return jsonify({'message': '用户已退出', "status_code": 200})
    return jsonify({'message': '用户不存在', "status_code": 404})

#接收图像
@app.route('/receive_image', methods=['POST'])
def receive_image():
    db = g.db
    data = request.form
    client_username = data["username"]
    server_username = from_user_get_serveruser(db, client_username)
    public_key,private_key = get_keys_for_user(client_username, server_username)
    if private_key is None:
        return jsonify({'message': '用户未绑定', "status_code": 404})
    encryted_data = eval(data["encryptedPost"])
    sc = EncryptedCommunicationServer(private_key)
    try:
        # data = sc.serverDecrypt(request.form)
        data_extra = sc.serverDecrypt(encryted_data)
    except Exception as e:
        app.logger.error("解密失败：%s" % str(e))
        return jsonify({"error": "Decryption failed", "status_code": 500})
    image_data = data_extra["image_data"]
    if not image_data or not client_username:
        return jsonify({'message': '接收失败', "status_code": 500})

    try:
        img_data = base64.b64decode(image_data.encode('utf-8'))
        if not os.path.exists(f'screenshots/{server_username}/{client_username}'):
            os.makedirs(f'screenshots/{server_username}/{client_username}', exist_ok=True)
        
        with open(f'screenshots/{server_username}/{client_username}/{int(time.time())}.jpeg', 'wb') as f:
            f.write(img_data)

        return jsonify({'message': '图像接收成功', 'status_code': 200})
    except Exception as e:
        return jsonify({'message': f'图像接收失败: {e}', "status_code": 500})

#生成密钥
@app.route("/generate_keys", methods=["POST"])
def generate_keys():
    data = request.form
    client_username = data['username']
    # print(client_username)
    try:
        server_username_tmp = data['server_username']
    except:
        server_username_tmp = from_user_get_serveruser(g.db, client_username)
        
    if not client_username or not server_username_tmp:
        return jsonify({'message': '请求有误', "status_code": 400})
    #查询是否已经生成密钥
    public_key, private_key = get_keys_for_user(client_username, server_username_tmp)
    if public_key is None:
        #生成密钥
        public_key, private_key = generate_keys_for_user(client_username, server_username_tmp)
    response = {
        "public_key": public_key.decode('utf-8'),
        "status_code": 200
    }
    return jsonify(response)
    
#服务器用户注册
@app.route("/Sregister", methods=["POST"])
def Sregister():
    db = g.db
    data = request.form
    username = data.get('username')
    password = data.get('password')
    ip_address = data.get('ip_address')
    mac_address = data.get('mac_address')
    if not username or not password or not ip_address or not mac_address:
        return jsonify({'message': '注册信息有误', "status_code": 400})

    user = register_serveruser(db, username, password, mac_address)
    if user is not None:
        return jsonify({'message': '注册成功', "status_code": 200})
    else:
        return jsonify({'message': '注册失败', "status_code": 500})

#服务器用户登录
@app.route("/Slogin", methods=["POST"])
def Slogin():
    db = g.db
    data = request.form
    username = data.get('username')
    password = data.get('password')
    ip_address = data.get('ip_address')
    mac_address = data.get('mac_address')
    if not username or not password or not mac_address:
        return jsonify({'message': '登录信息有误', "status_code": 400})

    success = login_serveruser(db, username, password, ip_address)
    if success is not None:
        
        return jsonify({'message': '登录成功', "status_code": 200})
    else:
        return jsonify({'message': '用户名或密码错误', "status_code": 401})

#服务器用户登出
@app.route("/Slogout", methods=["POST"])
def Slogout():
    db = g.db
    data = request.form
    username = data["username"]
    if not username :
        return jsonify({'message': '登出信息有误', "status_code": 400})

    success = logout_serveruser(db, username)
    if success is not None:
        # session.pop('username', None)
        return jsonify({'message': '用户已退出', "status_code": 200})
    return jsonify({'message': '用户不存在', "status_code": 404})

#查询客户表，基于客户归属的服务器查询所有的users
@app.route("/getUser",methods=["POST"])
def getUser():
    db = g.db
    data = request.form
    serveruser = data.get('serveruser')
    users = get_username_from_serveruser(db,serveruser)
    return jsonify({'message':'请求成功','users':str(users),'status_code':200})

if __name__ == '__main__':
    os.makedirs('screenshots', exist_ok=True)
    app.run(host='0.0.0.0', port=5000,debug=True)

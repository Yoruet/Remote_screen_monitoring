import uuid
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "mysql+mysqlconnector://root:123456@127.0.0.1/screenmonitor"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    idusers = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    mac_address = Column(String(255), nullable=True)
    ip_address = Column(String(255), nullable=True)
    serveruser=Column(String(255), nullable=True)
    online = Column(Boolean, default=False)

class ServerUser(Base):
    __tablename__ = 'serverusers'

    idserverusers = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    mac_address = Column(String(255), nullable=True)
    ip_address = Column(String(255), nullable=True)
    online = Column(Boolean, default=False)

# 如果已经手动创建了表，可以注释掉这行
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def register_user(db, username, password, mac,serverusername=None):
    # 客户注册
    new_user = User(username=username, password=password, mac_address=mac, serveruser=serverusername)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

def login_user(db, username, password, ip):
    # 客户登录
    user = db.query(User).filter(User.username == username, User.password == password).first()
    if user:
        user.ip_address = ip
        user.online = True
        db.commit()
        db.refresh(user)
        return user
    return None

def logout_user(db, username):
    # 客户退出登录
    user = db.query(User).filter(User.username == username).first()
    if user:
        user.ip_address = None
        user.online = False
        db.commit()
        db.refresh(user)
        return user
    return None
def register_serveruser(db, username, password, mac):
    # 服务器用户注册
    new_user = ServerUser(username=username, password=password, mac_address=mac)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user
def login_serveruser(db, username, password, ip):
    # 服务器用户登录
    user = db.query(ServerUser).filter(ServerUser.username == username, ServerUser.password == password).first()
    if user:
        user.ip_address = ip
        user.online = True
        db.commit()
        db.refresh(user)
        return user
    return None
def logout_serveruser(db, username):
    # 服务器用户退出登录
    user = db.query(ServerUser).filter(ServerUser.username == username).first()
    if user:
        user.ip_address = None
        user.online = False
        db.commit()
        db.refresh(user)
        return user
    return None
def from_user_get_serveruser(db, username):
    # 查询客户表，基于客户的username查询其对应的serverusername
    serverusername = db.query(User).filter(User.username == username).first().serveruser
    return serverusername

def get_username_from_serveruser(db, serverusername):
    # 查询客户表，基于客户的username查询其对应的serverusername
    user = db.query(User).filter(User.serveruser == serverusername).all()
    res = []
    for user in user:
        res.append({'username': user.username, 'online': user.online})
    return res
def get_ip_from_username(db,username):
    # 查询客户表，基于客户的username查询其对应的ip
    ip = db.query(User).filter(User.username == username).first().ip_address
    return ip
# 测试代码
if __name__ == "__main__":
    db = next(get_db())
    users=get_username_from_serveruser(db,"1")
    print(users)
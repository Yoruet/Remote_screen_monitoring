from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "mysql+mysqlconnector://root:760312@127.0.0.1/screenmonitor"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    idusers = Column(Integer, primary_key=True, index=True)
    user_identifier = Column(String(255), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    mac_address = Column(String(255), nullable=True)
    ip_address = Column(String(255), nullable=True)
    online = Column(Boolean, default=False)

# 如果已经手动创建了表，可以注释掉这行
#Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def register_user(db, user_identifier, password, mac):
    new_user = User(user_identifier=user_identifier, password=password, mac_address=mac)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

def login_user(db, user_identifier, password, ip):
    user = db.query(User).filter(User.user_identifier == user_identifier, User.password == password).first()
    if user:
        user.ip_address = ip
        user.online = True
        db.commit()
        db.refresh(user)
        return user
    return None

def logout_user(db, user_identifier):
    user = db.query(User).filter(User.user_identifier == user_identifier).first()
    if user:
        user.ip_address = None
        user.online = False
        db.commit()
        db.refresh(user)
        return user
    return None

# 测试代码
if __name__ == "__main__":
    db = next(get_db())
    register_user(db, "test@1234", "test", "1234")


import os
from dotenv import load_dotenv
import psycopg2
from psycopg2 import pool
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from sqlmodel import SQLModel, Session, create_engine as create_sqlmodel_engine


load_dotenv()

class Settings:
    def __init__(self):
        self.db_url = os.getenv("DATABASE")
        self.db_name=os.getenv("DATANAME")
        self.db_user=os.getenv("DATAUSER")
        self.db_password=os.getenv("DATAPASS")
        self.db_port=os.getenv("DATEPORT")
        #创建链接字符
        self.db_conn_str = f"postgresql://{self.db_user}:{self.db_password}@{self.db_url}:{self.db_port}/{self.db_name}"
        self.pool_size = 10 #连接池大小
        self.max_overflow = 20 #最大溢出连接数
        self.engine = create_sqlmodel_engine(self.db_conn_str,pool_size=self.pool_size,max_overflow=self.max_overflow,echo=True)
    
    @contextmanager
    def get_session(self):
        session = Session(self.engine)
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

engine = create_engine('sqlite:///database.db', echo=False)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, index=True)
    balance = Column(Float, default=1000.0)
    server_seed = Column(String, nullable=False)
    server_seed_hash = Column(String, nullable=False)
    client_seed = Column(String, default="client-seed")
    nonce = Column(Integer, default=0)

class BetHistory(Base):
    __tablename__ = 'bets'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, index=True)
    amount = Column(Float)
    payout = Column(Float)
    result_grid = Column(String)  # JSON string 5x3
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(engine)
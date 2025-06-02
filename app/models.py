from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from .settings import load_dotenv, ENV_PATH
from datetime import datetime
load_dotenv(dotenv_path=ENV_PATH)

Base = declarative_base()

DATABASE_URL = "sqlite:///./storage/database.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Template(Base):
    __tablename__ = 'templates'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text, nullable=True)

    input_mappings = relationship("InputMapping", back_populates="template")
    output_mappings = relationship("OutputMapping", back_populates="template")
    identity_mappings = relationship("IdentityMapping", back_populates="template")


class InputMapping(Base):
    __tablename__ = 'input_mappings'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    source = Column(String)
    cell = Column(String)
    forced_value = Column(String, nullable=True)
    template_id = Column(Integer, ForeignKey('templates.id'))

    template = relationship("Template", back_populates="input_mappings")


class OutputMapping(Base):
    __tablename__ = 'output_mappings'

    id = Column(Integer, primary_key=True, index=True)
    field = Column(String)
    cell = Column(String)
    template_id = Column(Integer, ForeignKey('templates.id'))

    template = relationship("Template", back_populates="output_mappings")
    
class IdentityMapping(Base):
    __tablename__ = 'identity_mappings'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    template_id = Column(Integer, ForeignKey('templates.id'))

    template = relationship("Template", back_populates="identity_mappings")

class ResultLogs(Base):
    __tablename__ = "result_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    datetime_started = Column(DateTime)
    datetime_ended = Column(DateTime)
    duration_seconds = Column(Integer) 
    template_id = Column(Integer, ForeignKey("templates.id"))
    excel_filename = Column(String)
    csv_filename = Column(String, nullable=True)
    num_of_records = Column(Integer, default=0)
    location_json = Column(String, nullable=True)
    location_csv = Column(String, nullable=True)
    
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

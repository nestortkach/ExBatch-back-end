import os
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from .settings import DATABASES


DATABASE_URL = f"postgresql://{DATABASES['USER']}:{DATABASES['PASSWORD']}@{DATABASES['HOST']}:{DATABASES['PORT']}/{DATABASES['NAME']}"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

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


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

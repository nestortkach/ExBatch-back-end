from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import ForeignKey
from .settings import DB_FILE

Base = declarative_base()


class Template(Base):
    __tablename__ = 'templates'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text, nullable=True)

    input_mappings = relationship("InputMapping", back_populates="template")
    output_mappings = relationship("OutputMapping", back_populates="template")


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




engine = create_engine(f"sqlite:///{DB_FILE}", connect_args={"check_same_thread": False})
Base.metadata.create_all(bind=engine)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)



def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

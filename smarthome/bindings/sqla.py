from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, ForeignKey, String

Base = declarative_base()

class ThingTypes(Base):

    __tablename__ = 'thing_types'
    type_id = Column(Integer, primary_key=True)
    type_name = Column(String)

class BaseThing(Base):

    __tablename__ = 'things'
    thing_type = Column(Integer, ForeignKey())

    __mapper_args__ = {
        'polymorphic_on': type_id,
        'polymorphic_identity': 'base_device'
    }

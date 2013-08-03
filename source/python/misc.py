import sqlalchemy as sa
from sqlalchemy.ext import declarative
from sqlalchemy import orm
from sqlalchemy import types

Base = declarative.declarative_base()
Session = orm.sessionmaker()

class TimeDelta(types.TypeDecorator):
    impl = types.BigInteger

    
    SEC = int(10e6)
    DAYS = int(10e6) * 24 * 60 * 60

    def process_bind_param(self, value, dialect):
        if value:
            y = (value.days * self.DAYS +
                 value.seconds * self.SEC +
                 value.microseconds)
        else:
            y = None
        return y

    def process_result_value(self, value, dialect):
        if value:
            return datetime.timedelta(microseconds=value)
        else:
            return None

class ForeignKey(sa.ForeignKey):
    """ Subclass sqlalchemy.ForeignKey with different defaults """
    def __init__(self, column, **kwargs):
        ## ondelete = CASCADE makes it easier when unloading tables
        ## initially deferred and deferrable are useful in loading
        defaults = {'onupdate' : "CASCADE",
                  'ondelete' : "CASCADE",
                  'initially' : "DEFERRED",
                  'deferrable' : True}

        defaults.update(kwargs)
        super(ForeignKey, self).__init__(column, **defaults)

class Mixin(object):
    """ Project mixin class

    All objects mapping to tables in this database inherit
    from this class. 

    """
    @classmethod
    def columns(kls):
        """ names of columns in the table mapped to the class """ 
        return [x.name for x in kls.__table__.c]


class FactorMixin(object):
    """ Factor (Categorical) data table
    """
    label = sa.Column(sa.Unicode)
    
class CharFactorMixin(FactorMixin):
    """ Factor (Categorical) data table with character values """
    value = sa.Column(sa.Unicode, primary_key=True)


class IntFactorMixin(FactorMixin):
    """ Factor (Categorical) data table with integer values """
    value = sa.Column(sa.Integer, primary_key=True)


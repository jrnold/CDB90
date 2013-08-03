import sqlalchemy as sa
from sqlalchemy.ext import declarative
from sqlalchemy import orm
from sqlalchemy import types

from .misc import *

class Cdb90PosType(Base, IntFactorMixin):
    __tablename__ = 'cdb90_postype'

class Cdb90Post(Base, CharFactorMixin):
    __tablename__ = 'cdb90_post'

class Cdb90Pri(Base, CharFactorMixin):
    __tablename__ = 'cdb90_pri'

class Cdb90Reso(Base, CharFactorMixin):
    __tablename__ = 'cdb90_reso'

class Cdb90Cea(Base, IntFactorMixin):
    __tablename__ = 'cdb90_cea'

class Cdb90Surpa(Base, IntFactorMixin):
    __tablename__ = 'cdb90_surpa'

class Cdb90Aeroa(Base, IntFactorMixin):
    __tablename__ = 'cdb90_aeroa'

class Cdb90CodeAD(Base, IntFactorMixin):
    __tablename__ = 'cdb90_codead'

class Cdb90Crit(Base, IntFactorMixin):
    __tablename__ = 'cdb90_crit'

class Cdb90WinA(Base, IntFactorMixin):
    __tablename__ = 'cdb90_wina'

class Cdb90Terra1(Base, CharFactorMixin):
    __tablename__ = 'cdb90_terra1'

class Cdb90Terra2(Base, CharFactorMixin):
    __tablename__ = 'cdb90_terra2'

class Cdb90Terra3(Base, CharFactorMixin):
    __tablename__ = 'cdb90_terra3'

class Cdb90Wx1(Base, CharFactorMixin):
    __tablename__ = 'cdb90_wx1'

class Cdb90Wx2(Base, CharFactorMixin):
    __tablename__ = 'cdb90_wx2'

class Cdb90Wx3(Base, CharFactorMixin):
    __tablename__ = 'cdb90_wx3'

class Cdb90Wx4(Base, CharFactorMixin):
    __tablename__ = 'cdb90_wx4'

class Cdb90Wx5(Base, CharFactorMixin):
    __tablename__ = 'cdb90_wx5'

class Version(Base, Mixin):
    __tablename__ = 'version'
    version = sa.Column(sa.Unicode, primary_key=True)

class Cdb90Battle(Base, Mixin):
    __tablename__ = "cdb90_battles"
    __table_args__ = (
        # Total tanks = light tanks + MBT
        sa.CheckConstraint('lta + mbta = tanka'),
        sa.CheckConstraint('ltd + mbtd = tankd'),
        # Cavalry < personnel
        sa.CheckConstraint('cava <= stra'),
        sa.CheckConstraint('cavd <= strd'),        
        # Casualties < available weaponry
        # Tanks
        sa.CheckConstraint('ctanka <= tanka'),
        sa.CheckConstraint('ctankd <= tankd'),
        # artillery
        sa.CheckConstraint('cartya <= artya'),
        sa.CheckConstraint('cartyd <= artyd'),
        # Air support
        sa.CheckConstraint('cflya <= flya'),
        sa.CheckConstraint('cflyd <= flyd'),
        # Casualties and strength
        # Initial + Reinforcements - Casualties = Final
        sa.CheckConstraint('intsta + rerpa - casa = finsta'),
        sa.CheckConstraint('intstd + rerpd - casd = finstd'),
        # Strength >= casualties (only if str[ad] is not total strength)
        sa.CheckConstraint('stra >= casa or codea != 3'),
        sa.CheckConstraint('strd >= casd or coded != 3'),
        sa.CheckConstraint('(intsta = stra) or (codea != 1)'),
        sa.CheckConstraint('(intsta is not null) or (codea != 1)'),
        sa.CheckConstraint('(intstd = strd) or (coded != 1)'),
        sa.CheckConstraint('(intstd is not null) or (coded != 1)'),                
        sa.CheckConstraint('(intsta + rerpa = stra) or (codea != 3)'),
        sa.CheckConstraint('(intstd + rerpd = strd) or (coded != 3)'),
        sa.CheckConstraint('(finsta + casa = stra) or (codea != 3)'),
        sa.CheckConstraint('(finstd + casd = strd) or (coded != 3)'),
        # Cannot be parent of oneself
        sa.CheckConstraint('isqno != parent')
        )
        
    isqno = sa.Column(sa.Integer,
                      primary_key=True)
    war = sa.Column(sa.Unicode)
    name = sa.Column(sa.Unicode)
    locn = sa.Column(sa.Unicode)
    campgn = sa.Column(sa.Unicode)
    nama = sa.Column(sa.Unicode)
    coa = sa.Column(sa.Unicode)
    namd = sa.Column(sa.Unicode)
    cod = sa.Column(sa.Unicode)
    wofa1 = sa.Column(sa.Float,
                      sa.CheckConstraint('wofa1 > 0'))
    wofd1 = sa.Column(sa.Float,
                      sa.CheckConstraint('wofd1 > 0'))
    front1_time_min = sa.Column(sa.DateTime)
    front1_time_max  = sa.Column(sa.DateTime)
    wofa2 = sa.Column(sa.Float,
                      sa.CheckConstraint('wofd3 > 0'))
    wofd2 = sa.Column(sa.Float,
                      sa.CheckConstraint('wofd3 > 0'))
    front2_time_min = sa.Column(sa.DateTime)
    front2_time_max  = sa.Column(sa.DateTime)
    wofa3 = sa.Column(sa.Float,
                      sa.CheckConstraint('wofd3 > 0'))
    wofd3 = sa.Column(sa.Float,
                      sa.CheckConstraint('wofd3 > 0'))
    front3_time_min = sa.Column(sa.DateTime)
    front3_time_max  = sa.Column(sa.DateTime)
    postype = sa.Column(sa.Integer,
                        ForeignKey(Cdb90PosType.__table__.c.value))
    post1 = sa.Column(sa.Unicode,
                      ForeignKey(Cdb90Post.__table__.c.value))
    post2 = sa.Column(sa.Unicode,
                       ForeignKey(Cdb90Post.__table__.c.value))
    front = sa.Column(sa.Boolean)
    depth = sa.Column(sa.Boolean)
    time = sa.Column(sa.Boolean)
    # terra1 = sa.Column(sa.Unicode)
    # terra2 = sa.Column(sa.Unicode)
    # wx1 = sa.Column(sa.Unicode(5))
    # wx2 = sa.Column(sa.Unicode(5))
    # wx3 = sa.Column(sa.Unicode(5))
    surpa = sa.Column(sa.Integer,
                      ForeignKey(Cdb90Surpa.__table__.c.value))
    aeroa = sa.Column(sa.Integer,
                      ForeignKey(Cdb90Aeroa.__table__.c.value))
    stra = sa.Column(sa.Integer,
                     sa.CheckConstraint('stra > 0'))
    codea = sa.Column(sa.Integer,
                      ForeignKey(Cdb90CodeAD.__table__.c.value))
    intsta = sa.Column(sa.Integer,
                       sa.CheckConstraint('intsta > 0'))
    rerpa = sa.Column(sa.Integer,
                      sa.CheckConstraint('rerpa >= 0'))
    casa = sa.Column(sa.Integer,
                     sa.CheckConstraint('casa > 0'))
    finsta = sa.Column(sa.Integer,
                       sa.CheckConstraint('finsta > 0'))
    strd = sa.Column(sa.Integer,
                     sa.CheckConstraint('strd > 0'))
    coded = sa.Column(sa.Integer,
                      ForeignKey(Cdb90CodeAD.__table__.c.value))
    intstd = sa.Column(sa.Integer,
                       sa.CheckConstraint('intstd > 0'))
    rerpd = sa.Column(sa.Integer,
                      sa.CheckConstraint('rerpd >= 0'))
    casd = sa.Column(sa.Integer,
                     sa.CheckConstraint('casd > 0'))
    finstd = sa.Column(sa.Integer,
                       sa.CheckConstraint('finstd >= 0'))
    cava = sa.Column(sa.Integer,
                     sa.CheckConstraint('cava >= 0'))
    tanka = sa.Column(sa.Integer,
                      sa.CheckConstraint('tanka >= 0'))
    lta = sa.Column(sa.Integer,
                    sa.CheckConstraint('lta >= 0'))
    mbta = sa.Column(sa.Integer,
                     sa.CheckConstraint('mbta >= 0'))
    artya = sa.Column(sa.Integer,
                      sa.CheckConstraint('artya >= 0'))
    flya = sa.Column(sa.Integer,
                     sa.CheckConstraint('flya >= 0'))
    ctanka = sa.Column(sa.Integer,
                       sa.CheckConstraint('ctanka >= 0'))
    cartya = sa.Column(sa.Integer,
                       sa.CheckConstraint('cartya >= 0'))
    cflya = sa.Column(sa.Integer,
                      sa.CheckConstraint('cflya >= 0'))
    cavd = sa.Column(sa.Integer,
                     sa.CheckConstraint('cavd >= 0'))
    tankd = sa.Column(sa.Integer,
                      sa.CheckConstraint('tankd >= 0'))
    ltd = sa.Column(sa.Integer,
                    sa.CheckConstraint('ltd >= 0'))
    mbtd = sa.Column(sa.Integer,
                     sa.CheckConstraint('mbtd >= 0'))
    artyd = sa.Column(sa.Integer,
                      sa.CheckConstraint('artyd >= 0'))
    flyd = sa.Column(sa.Integer,
                     sa.CheckConstraint('flyd >= 0'))
    ctankd = sa.Column(sa.Integer,
                       sa.CheckConstraint('ctankd >= 0'))
    cartyd = sa.Column(sa.Integer,
                       sa.CheckConstraint('cartyd >= 0'))
    cflyd = sa.Column(sa.Integer,
                      sa.CheckConstraint('cflyd >= 0'))
    cea = sa.Column(sa.Integer,
                    ForeignKey(Cdb90Cea.__table__.c.value))
    leada = sa.Column(sa.Integer,
                      ForeignKey(Cdb90Cea.__table__.c.value))
    trnga = sa.Column(sa.Integer,
                      ForeignKey(Cdb90Cea.__table__.c.value))
    morala = sa.Column(sa.Integer,
                       ForeignKey(Cdb90Cea.__table__.c.value))
    logsa = sa.Column(sa.Integer,
                      ForeignKey(Cdb90Cea.__table__.c.value))
    momnta = sa.Column(sa.Integer,
                       ForeignKey(Cdb90Cea.__table__.c.value))
    intela = sa.Column(sa.Integer,
                       ForeignKey(Cdb90Cea.__table__.c.value))
    techa = sa.Column(sa.Integer,
                      ForeignKey(Cdb90Cea.__table__.c.value))
    inita = sa.Column(sa.Integer,
                      ForeignKey(Cdb90Cea.__table__.c.value))
    wina = sa.Column(sa.Integer,
                     ForeignKey(Cdb90WinA.__table__.c.value))
    kmda = sa.Column(sa.Float)
    acha = sa.Column(sa.Integer,
                     sa.CheckConstraint('acha >= 1 and acha <= 10'))
    achd = sa.Column(sa.Integer,
                     sa.CheckConstraint('achd >= 1 and achd <= 10'))
    crit = sa.Column(sa.Integer,
                     ForeignKey(Cdb90Crit.__table__.c.value))
    quala = sa.Column(sa.Integer,
                      ForeignKey(Cdb90Cea.__table__.c.value))
    resa = sa.Column(sa.Integer,
                     ForeignKey(Cdb90Cea.__table__.c.value))
    mobila = sa.Column(sa.Integer,
                       ForeignKey(Cdb90Cea.__table__.c.value))
    aira = sa.Column(sa.Integer,
                     ForeignKey(Cdb90Cea.__table__.c.value))
    fprepa = sa.Column(sa.Integer,
                       ForeignKey(Cdb90Cea.__table__.c.value))
    wxa = sa.Column(sa.Integer,
                    ForeignKey(Cdb90Cea.__table__.c.value))
    terra = sa.Column(sa.Integer,
                      ForeignKey(Cdb90Cea.__table__.c.value))
    leadaa = sa.Column(sa.Integer,
                       ForeignKey(Cdb90Cea.__table__.c.value))
    plana = sa.Column(sa.Integer,
                      ForeignKey(Cdb90Cea.__table__.c.value))
    surpaa = sa.Column(sa.Integer,
                       ForeignKey(Cdb90Cea.__table__.c.value))
    mana = sa.Column(sa.Integer,
                     ForeignKey(Cdb90Cea.__table__.c.value))
    logsaa = sa.Column(sa.Integer,
                       ForeignKey(Cdb90Cea.__table__.c.value))
    fortsa = sa.Column(sa.Integer,
                       ForeignKey(Cdb90Cea.__table__.c.value))
    deepa = sa.Column(sa.Integer,
                      ForeignKey(Cdb90Cea.__table__.c.value))
    pria1 = sa.Column(sa.Unicode,
                      ForeignKey(Cdb90Pri.__table__.c.value))
    pria2 = sa.Column(sa.Unicode,
                      ForeignKey(Cdb90Pri.__table__.c.value))
    pria3 = sa.Column(sa.Unicode,
                      ForeignKey(Cdb90Pri.__table__.c.value))
    seca1 = sa.Column(sa.Unicode,
                      ForeignKey(Cdb90Pri.__table__.c.value))
    seca2 = sa.Column(sa.Unicode,
                      ForeignKey(Cdb90Pri.__table__.c.value))
    seca3 = sa.Column(sa.Unicode,
                      ForeignKey(Cdb90Pri.__table__.c.value))
    resoa1 = sa.Column(sa.Unicode,
                       ForeignKey(Cdb90Reso.__table__.c.value))
    resoa2 = sa.Column(sa.Unicode,
                       ForeignKey(Cdb90Reso.__table__.c.value))
    resoa3 = sa.Column(sa.Unicode,
                       ForeignKey(Cdb90Reso.__table__.c.value))
    prid1 = sa.Column(sa.Unicode,
                      ForeignKey(Cdb90Pri.__table__.c.value))
    prid2 = sa.Column(sa.Unicode,
                      ForeignKey(Cdb90Pri.__table__.c.value))
    prid3 = sa.Column(sa.Unicode,
                      ForeignKey(Cdb90Pri.__table__.c.value))
    secd1 = sa.Column(sa.Unicode,
                      ForeignKey(Cdb90Pri.__table__.c.value))
    secd2 = sa.Column(sa.Unicode,
                      ForeignKey(Cdb90Pri.__table__.c.value))
    secd3 = sa.Column(sa.Unicode,
                      ForeignKey(Cdb90Pri.__table__.c.value))
    resod1 = sa.Column(sa.Unicode,
                       ForeignKey(Cdb90Reso.__table__.c.value))
    resod2 = sa.Column(sa.Unicode,
                       ForeignKey(Cdb90Reso.__table__.c.value))
    resod3 = sa.Column(sa.Unicode,
                       ForeignKey(Cdb90Reso.__table__.c.value))
    strapl = sa.Column(sa.Integer,
                       sa.CheckConstraint('strapl >= 0'))
    strami = sa.Column(sa.Integer,
                       sa.CheckConstraint('strami <= 0'))                       
    casapl = sa.Column(sa.Integer,
                       sa.CheckConstraint('casapl >= 0'))
    casami = sa.Column(sa.Integer,
                       sa.CheckConstraint('casami <= 0'))                       
    strdpl = sa.Column(sa.Integer,
                       sa.CheckConstraint('strdpl >= 0'))
    strdmi = sa.Column(sa.Integer,
                       sa.CheckConstraint('strdmi <= 0'))
    casdpl = sa.Column(sa.Integer,
                       sa.CheckConstraint('casdpl >= 0'))
    casdmi = sa.Column(sa.Integer,
                       sa.CheckConstraint('casdmi <= 0'))
    parent = sa.Column(sa.Integer,
                       ForeignKey('cdb90_battles.isqno'))
    war2 = sa.Column(sa.Unicode)
    war3 = sa.Column(sa.Unicode)


class Cdb90Forces(Base, Mixin):
    __tablename__ = "cdb90_forces"
    __table_args__ = (
        # Total tanks = light tanks + MBT
        sa.CheckConstraint('lt + mbt = tank'),
        # Cavalry < personnel
        sa.CheckConstraint('cav <= str'),
        # Casualties < available weaponry
        # Tanks
        sa.CheckConstraint('ctank <= tank'),
        # artillery
        sa.CheckConstraint('carty <= arty'),
        # Air support
        sa.CheckConstraint('cfly <= fly'),
        # Casualties and strength
        # Initial + Reinforcements - Casualties = Final
        sa.CheckConstraint('intst + rerp - cas = finst'),
        # Strength >= casualties (only if str[ad] is not total strength)
        sa.CheckConstraint('str >= cas or code != 3'),
        sa.CheckConstraint('(intst = str) or (code != 1)'),
        sa.CheckConstraint('(intst = str) or (code != 1)'),
        sa.CheckConstraint('(intst + rerp = str) or (code != 3)'),
        sa.CheckConstraint('(finst + cas = str) or (code != 3)'),
        )
        
    isqno = sa.Column(sa.Integer, primary_key=True)
    attacker = sa.Column(sa.Boolean, primary_key = True)
    nam = sa.Column(sa.Unicode) # nama, namd
    co = sa.Column(sa.Unicode)
    wof1 = sa.Column(sa.Numeric,
                     sa.CheckConstraint('wof1 > 0')) # wofa1, wofd1
    wof2 = sa.Column(sa.Numeric,
                     sa.CheckConstraint('wof2 > 0')) # wofa2, wofd2
    wof3 = sa.Column(sa.Numeric,
                     sa.CheckConstraint('wof3 > 0')) # wofa3, wofd3
    str = sa.Column(sa.Integer,
                    sa.CheckConstraint('str > 0'))
    code = sa.Column(sa.Integer,
                     ForeignKey(Cdb90CodeAD.__table__.c.value))
    intst = sa.Column(sa.Integer,
                      sa.CheckConstraint('intst > 0'))
    rerp = sa.Column(sa.Integer,
                     sa.CheckConstraint('rerp >= 0'))
    cas = sa.Column(sa.Integer,
                    sa.CheckConstraint('cas > 0'))
    finst = sa.Column(sa.Integer,
                      sa.CheckConstraint('finst > 0'))
    cav = sa.Column(sa.Integer,
                    sa.CheckConstraint('cav >= 0'))
    tank = sa.Column(sa.Integer,
                     sa.CheckConstraint('tank >= 0'))
    lt = sa.Column(sa.Integer,
                   sa.CheckConstraint('lt >= 0'))
    mbt = sa.Column(sa.Integer,
                    sa.CheckConstraint('mbt >= 0'))
    artya = sa.Column(sa.Integer,
                      sa.CheckConstraint('arty >= 0'))
    fly = sa.Column(sa.Integer,
                     sa.CheckConstraint('fly >= 0'))
    ctank = sa.Column(sa.Integer,
                       sa.CheckConstraint('ctank >= 0'))
    carty = sa.Column(sa.Integer,
                       sa.CheckConstraint('carty >= 0'))
    cfly = sa.Column(sa.Integer,
                      sa.CheckConstraint('cfly >= 0'))
    pri1 = sa.Column(sa.Unicode,
                      ForeignKey(Cdb90Pri.__table__.c.value))
    pri2 = sa.Column(sa.Unicode,
                      ForeignKey(Cdb90Pri.__table__.c.value))
    pri3 = sa.Column(sa.Unicode,
                      ForeignKey(Cdb90Pri.__table__.c.value))
    sec1 = sa.Column(sa.Unicode,
                      ForeignKey(Cdb90Pri.__table__.c.value))
    sec2 = sa.Column(sa.Unicode,
                      ForeignKey(Cdb90Pri.__table__.c.value))
    sec3 = sa.Column(sa.Unicode,
                      ForeignKey(Cdb90Pri.__table__.c.value))
    reso1 = sa.Column(sa.Unicode,
                       ForeignKey(Cdb90Reso.__table__.c.value))
    reso2 = sa.Column(sa.Unicode,
                       ForeignKey(Cdb90Reso.__table__.c.value))
    reso3 = sa.Column(sa.Unicode,
                       ForeignKey(Cdb90Reso.__table__.c.value))
    strpl = sa.Column(sa.Integer,
                       sa.CheckConstraint('strpl >= 0'))
    strmi = sa.Column(sa.Integer,
                       sa.CheckConstraint('strmi <= 0'))                       
    caspl = sa.Column(sa.Integer,
                       sa.CheckConstraint('caspl >= 0'))
    casmi = sa.Column(sa.Integer,
                       sa.CheckConstraint('casmi <= 0'))                       
    
class Cdb90Terra(Base, Mixin):
    __tablename__ = 'cdb90_terra'
    
    isqno = sa.Column(sa.Integer,
                      ForeignKey(Cdb90Battle.__table__.c.isqno),
                      primary_key=True)
    terrano = sa.Column(sa.Integer, primary_key=True)
    terra1 = sa.Column(sa.Unicode,
                       ForeignKey(Cdb90Terra1.__table__.c.value))
    terra2 = sa.Column(sa.Unicode,
                       ForeignKey(Cdb90Terra2.__table__.c.value))
    terra3 = sa.Column(sa.Unicode,
                       ForeignKey(Cdb90Terra3.__table__.c.value))


class Cdb90Wx(Base, Mixin):
    __tablename__ = 'cdb90_wx'
    
    isqno = sa.Column(sa.Integer,
                      ForeignKey(Cdb90Battle.__table__.c.isqno),
                      primary_key=True)
    wxno = sa.Column(sa.Integer, primary_key=True)
    wx1 = sa.Column(sa.Unicode(1),
                    ForeignKey(Cdb90Wx1.__table__.c.value))
    wx2 = sa.Column(sa.Unicode(1),
                    ForeignKey(Cdb90Wx2.__table__.c.value))
    wx3 = sa.Column(sa.Unicode(1),
                    ForeignKey(Cdb90Wx3.__table__.c.value))
    wx4 = sa.Column(sa.Unicode(1),
                    ForeignKey(Cdb90Wx4.__table__.c.value))
    wx5 = sa.Column(sa.Unicode(1),                    
                    ForeignKey(Cdb90Wx5.__table__.c.value))


class Cdb90Atp(Base, Mixin):
    __tablename__ = 'cdb90_atp'
    __table_args__ = (sa.CheckConstraint('start_time_min <= start_time_max'),
                      sa.CheckConstraint('end_time_min <= end_time_max'),
                      sa.CheckConstraint('end_time_max >= start_time_max'),
                      sa.CheckConstraint('end_time_min >= start_time_min'))
    isqno = sa.Column(sa.Integer,
                      ForeignKey(Cdb90Battle.__table__.c.isqno),
                      primary_key=True)
    atpno = sa.Column(sa.Integer, primary_key=True)
    start_time_min = sa.Column(sa.DateTime)
    start_time_max = sa.Column(sa.DateTime)
    end_time_min = sa.Column(sa.DateTime)
    end_time_max = sa.Column(sa.DateTime)
    duration = sa.Column(TimeDelta)

class Cdb90Link(Base, Mixin):
    __tablename__ = 'cdb90_links'
    isqno = sa.Column(sa.Integer,
                      ForeignKey(Cdb90Battle.__table__.c.isqno),
                      primary_key=True)
    linkno = sa.Column(sa.Integer, primary_key=True)
    dbpedia = sa.Column(sa.Unicode)
    
class Cdb90ToCwsac(Base, Mixin):
    __tablename__ = 'cdb90_to_cwsac'
    isqno = sa.Column(sa.Integer,
                      ForeignKey(Cdb90Battle.__table__.c.isqno),
                      primary_key=True)
    cwsac = sa.Column(sa.Unicode(5))

class Cdb90ToCow(Base, Mixin):
    __tablename__ = 'cdb90_to_cow'
    isqno = sa.Column(sa.Integer,
                      ForeignKey(Cdb90Battle.__table__.c.isqno),
                      primary_key=True)
    cow_warno = sa.Column(sa.Integer)

class Cdb90Extra(Base, Mixin):
    __tablename__ = 'cdb90_extra'
    isqno = sa.Column(sa.Integer,
                      ForeignKey(Cdb90Battle.__table__.c.isqno),
                      primary_key=True)
    war = sa.Column(sa.Unicode, nullable=False)
    theater = sa.Column(sa.Unicode)
    belligerenta = sa.Column(sa.Unicode, nullable=False)
    sidea = sa.Column(sa.Boolean, nullable=False)
    belligerentd = sa.Column(sa.Unicode, nullable=False)

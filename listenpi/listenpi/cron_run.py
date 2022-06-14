import sys
import os
import time

from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey
from sqlalchemy import create_engine, update
from sqlalchemy.orm import relationship

#Acceso a la base de datos
engine = create_engine('sqlite:////home/pi/listenpi/listenpi/dbase.db')
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()

class Configuracion(Base):
    __tablename__= 'configuracion'
    id = Column(Integer, primary_key = True)
    Nombre = Column(String(50))
    IP = Column(String(50))
    Puerto = Column(String(50))
    Estatus = Column(Boolean, default=False)
    #Descripcion = Column(String(100))
    
class Relevadores(Base):
    __tablename__ = 'relevadores'
    id = Column(Integer, primary_key = True)
    Nombre = Column(String(50))
    Estatus = Column(Boolean, default=False)
    Pin = Column(String(10))
    Descripcion = Column(String(100))
    Logica = Column(Boolean, default=False)


from sqlalchemy.orm import sessionmaker
Session = sessionmaker(bind = engine)
session = Session()

#cambio de estado relay
def change_relay(logica, pin, estatus):
    #os.system('gpio -g mode '+str(pin)+' output')
    drasp = session.query(Relevadores).filter(Relevadores.Pin == str(pin)).one()
    if drasp:
        if estatus == '1': #relay ON
            drasp.Estatus = 1 #guardo estatus
            drasp.Logica = int(logica) #guardo logica
            if logica == '0': #logica normal
                os.system('gpio -g write '+str(pin)+' 1')
            else:
                os.system('gpio -g write '+str(pin)+' 0')
        else:   #relay OFF
            drasp.Estatus = 0
            drasp.Logica = int(logica)
            if logica == '0': #logica normal
                os.system('gpio -g write '+str(pin)+' 0')
            else:
                os.system('gpio -g write '+str(pin)+' 1')
        session.commit()
        #os.system("clear")
        # print(logica, pin, estatus)
        # return "Cambio de estado exitoso"
    else:
        # os.system("clear")
        return "Error"

data = sys.argv
pin = data[1]
estatus = data[2]
logica = data[3]
# print(data[1])
change_relay(logica, pin, estatus)
# os.system('gpio -g write '+str(data[1])+' 0')
# print(data)
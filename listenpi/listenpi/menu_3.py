from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey
from sqlalchemy import create_engine, update
from sqlalchemy.orm import relationship

import socket
import json
import sys
import os
import time

#variables importantes
ban = 0
datos = None
ip_nuevo = None
puerto_nuevo = None
codigo = None
sock = None
server_address = None

#cambio de ip y puerto
def change_static_ip(ip_address, routers, dns):
    conf_file = '/etc/dhcpcd.conf'
    try:
        with open(conf_file, 'r') as file:
            data = file.readlines()
            
        wlanFound = next((x for x in data if 'interface wlan0' in x), None)
        
        if wlanFound:
            wlanIndex = data.index(wlanFound)
            if data[wlanIndex].startswith('#'):
                data[wlanIndex].replace('#', '')
            
        if wlanIndex:
            data[wlanIndex+1] = f'static ip_address={ip_address}/24\n'
            data[wlanIndex+2] = f'static routers={routers}\n'
            data[wlanIndex+3] = f'static domain_name_servers={dns}\n'
            
        with open(conf_file, 'w') as file:
            file.writelines( data )
            os.system('sudo ifconfig wlan0 down')
            os.system('sudo ifconfig wlan0 '+ip_address)
            os.system('sudo ifconfig wlan0 netmask '+'255.255.255.0') #comprobar dato del server
            os.system('sudo ifconfig wlan0 broadcast '+dns)  #comprobar 
            os.system('sudo ifconfig wlan0 up')
            #os.system('sudo reboot')
        
    
    except Exception as ex:
        logging.exception('IP changing error: %s', ex)
    
    finally:
        pass

#change_static_ip('192.168.100.99', '192.168.100.1', '192.168.100.1')

#Acceso a la base de datos
engine = create_engine('sqlite:////home/pi/listenpi/listenpi/dbase.db', echo = True)
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

from sqlalchemy.orm import sessionmaker
Session = sessionmaker(bind = engine)
session = Session()

#commit configuracion
def commitconfig(d_ip, d_puerto):
    a_rasp = session.query(Configuracion).filter(Configuracion.id == 1).one()
    a_rasp.IP = d_ip
    a_rasp.Puerto = d_puerto
    session.commit()

#consulta configuracion
def consulta():
    drasp = session.query(Configuracion).all()
    ip = 0
    puerto = 0
    for row in drasp:
        ip = row.IP
        puerto = row.Puerto
    print("ip", ip)
    print("puerto", puerto)
    conf_socket(ip, puerto)

#cambio de estado relay
def change_relay(rele, pin, estatus):
    os.system('gpio -g mode '+str(pin)+' output')
    drasp = session.query(Relevadores).filter(Relevadores.Pin == str(pin)).one()
    if estatus == 'True':
        drasp.Estatus = 1
        os.system('gpio -g write '+str(pin)+' 1')
    else:
        drasp.Estatus = 0
        os.system('gpio -g write '+str(pin)+' 0')
    session.commit()
    print(rele, estatus, pin)
    
#cambio de nombre y/o pin
def rename_relay(nameAnt, pinAnt, nameNew, pinNew):
    bandera = 0
    drasp = session.query(Relevadores).all()
    
    if pinNew != pinAnt:
        for row in drasp:
            if str(pinNew) == str(row.Pin):
                bandera = 1
    
    if bandera == 0:
        rasp = session.query(Relevadores).filter(Relevadores.Pin == str(pinAnt)).one()
        os.system('gpio -g mode '+str(pinNew)+' output')
        if rasp.Estatus == 1:
            os.system('gpio -g write '+str(pinNew)+' 1')
        else:
            os.system('gpio -g write '+str(pinNew)+' 0')
        os.system('gpio -g write '+str(pinAnt)+' 0')
        #change_relay(rasp.Nombre, rasp.Pin, rasp.Estatus)
        rasp.Nombre = nameNew
        rasp.Pin = pinNew
        session.commit()
        return 0
    else:
        return 1

# configurar socket
def conf_socket(dir_ip, dir_puerto):
    global sock
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = (dir_ip, int(dir_puerto))
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(server_address)
    sock.listen(1)
    
#consulta estado relays
def consultaRelay():
    drasp = session.query(Relevadores).all()
    print(drasp)
    relay = {}
    for row in drasp:
        dato = str(row.Pin)+','+str(row.Estatus)
        item = {row.Nombre: dato}
        relay.update(item)
    reles = json.dumps(relay)
    return reles
    
#conexion web socket
def conexion():
    global codigo
    global datos
    while True:
        print('Esperando conexion')
        connection, client_address = sock.accept()
        try:
            print('conectado con:', client_address)
            while True:
                data = connection.recv(1024)
                if len(data) > 1:
                    data = data.decode("utf-8")
                    datos = json.loads(data)
                    codigo = format(datos["codigo"])
                    print(codigo) #comando para acciones
                    
                    if codigo == 'estatus_relay': #pregunta todos los estados de los reles
                        dato = json.dumps(consultaRelay())
                        connection.sendall(bytes(dato, encoding="utf-8"))
                    if codigo == 'change_relay': #cambia el estado del rele y lo guarda
                        change_relay(format(datos["relay"]),format(datos["pin"]), format(datos["estatus"]))
                        dato = 'ok'
                        connection.sendall(dato.encode())
                    if codigo == 'cambio_pin': #cambia el nombre y/o pin
                        existe = rename_relay(format(datos["name_ant"]), format(datos["pin_ant"]), format(datos["name_new"]), format(datos["pin_new"]) )
                        if existe == 1:
                            dato = 'error'
                            connection.sendall(dato.encode())
                        else:
                            dato = 'ok'
                            connection.sendall(dato.encode())
                    
                if data: 
                    dato = 'ok' 
                    print('send data back the client')
                    connection.sendall(dato.encode())
                else: #ultimo dato para finalizar sesion
                    print('no data from', client_address)
                    break
        finally:
            connection.close()
            break
        
#bucle principal
while True:
    if ban == 0:
        consulta()
        ban = 1
        
    if ban == 1:
        conexion()
        #aqui pueden ir las diferentes funciones o codigos
        if codigo == 'ip':
            ban = 2
    
    if ban == 2:
        print("ip nuevo:", format(datos['ip_n']))
        print("puerto nuevo:", format(datos['puerto_n']))
        #aqui va funcion para guardar en la bd
        commitconfig(format(datos['ip_n']), format(datos['puerto_n']))
        #funcion que cambia la ip y puerto desde la bd, checar dns y host
        if format(datos['ip_a']) != format(datos['ip_n']):
            change_static_ip(format(datos['ip_n']), '192.168.100.1', '192.168.100.1')
        codigo = 0 #cambiar codigo o reset
        ban = 0 # cambiar bandera o lugar para iniciar nuevo conexion de escucha en socket
        
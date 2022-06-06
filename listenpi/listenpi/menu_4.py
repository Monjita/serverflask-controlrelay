from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey
from sqlalchemy import create_engine, update, insert
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
            os.system('sudo ifconfig wlan0 netmask '+'255.255.255.0')
            os.system('sudo ifconfig wlan0 broadcast '+dns)
            os.system('sudo ifconfig wlan0 up')
            #os.system('sudo reboot')
        
    
    except Exception as ex:
        logging.exception('IP changing error: %s', ex)
    
    finally:
        pass

#change_static_ip('192.168.100.99', '192.168.100.1', '192.168.100.1')

#Acceso a la base de datos
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

engine = create_engine('sqlite:////home/pi/listenpi/listenpi/dbase.db', echo = True)
Session = sessionmaker(bind = engine)
session = Session()
# from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()

# from sqlalchemy.orm import sessionmaker
# Session = sessionmaker(bind = engine)
# session = Session()

class Configuracion(Base):
    __tablename__= 'configuracion'
    id = Column(Integer, primary_key = True)
    Nombre = Column(String(100))
    IP = Column(String(50))
    Puerto = Column(String(50))
    Estatus = Column(Boolean, default=False)
    #Descripcion = Column(String(100))
    
class Relevadores(Base):
    __tablename__ = 'relevadores'
    id = Column(Integer, primary_key = True)
    Nombre = Column(String(500))
    Estatus = Column(Boolean, default=False)
    Pin = Column(String(10))
    Descripcion = Column(String(500))
    Logica = Column(Boolean, default=False)
    
    def to_dict(self):
        return {
            'ID': self.id,
            'Nombre': self.Nombre,
            'Pin': self.Pin,
            'Estatus': self.Estatus,            
            'Logica': self.Logica,            
        }

class Tareas(Base):
    __tablename__ = 'tareas'
    id = Column(Integer, primary_key = True)
    Nombre_tarea = Column(String(500))
    Fecha = Column(String(50))
    Dias = Column(String(50))
    Hora = Column(String(50))
    Nombre = Column(String(500))
    Pin = Column(String(10))
    Estatus = Column(Boolean, default = False)
    Logica_rele = Column(Boolean, default = False)
    
    def __repr__(self):
        return (u'<{self.__class__.__name__}: {self.id}>'.format(self=self))
    
    def to_dict(self):
        return {
            'ID': self.id,
            'Nombre_tarea': self.Nombre_tarea,
            'Fecha': self.Fecha,
            'Dias': self.Dias,
            'Hora': self.Hora,
            'Nombre': self.Nombre,
            'Pin': self.Pin,
            'Estatus': self.Estatus,            
            'Logica': self.Logica_rele,            
        }

# from sqlalchemy.orm import sessionmaker
# Session = sessionmaker(bind = engine)
# session = Session()

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
    #pendiente de verificar con raspberry en produccion
    st = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:       
        st.connect(('10.255.255.255', 80))
        IP = st.getsockname()[0]
        
    except Exception:
        IP = ip
    finally:
        st.close()
    #pendiente verificar
    
    print("ip", IP)
    print("puerto", puerto)
    
    conf_socket(IP, puerto)
    
#obtener la ip con consulta   
def extract_ip():
    st = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:       
        st.connect(('10.255.255.255', 1))
        IP = st.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        st.close()
    return IP

#cambio de estado relay
def change_relay(rele, pin, estatus):
    os.system('gpio -g mode '+str(pin)+' output')
    drasp = session.query(Relevadores).filter(Relevadores.Pin == str(pin)).one()
    if estatus == 'True':
        drasp.Estatus = 1
        if drasp.Logica == 0: #logica normal 0 - off, 1 - on
            os.system('gpio -g write '+str(pin)+' 1')
        if drasp.Logica == 1: #logica inversa 1 - off, 0 - on
            os.system('gpio -g write '+str(pin)+' 0')
    else:
        drasp.Estatus = 0
        if drasp.Logica == 0:
            os.system('gpio -g write '+str(pin)+' 0')
        if drasp.Logica == 1: #logica inversa
            os.system('gpio -g write '+str(pin)+' 1')
    session.commit()
    print(rele, estatus, pin)

#Cambio de logica, 0 - logica normal, 1 - logica inversa
def change_logica(pin, polaridad, estatus):
    os.system('gpio -g mode '+str(pin)+' output')
    drasp = session.query(Relevadores).filter(Relevadores.Pin == str(pin)).one()
    if polaridad == '1':
        drasp.Logica = 0
    else:
        drasp.Logica = 1
    session.commit()
    if estatus == 'False':
        if polaridad == '0': #logica normal 0 - off, 1 - on
            os.system('gpio -g write '+str(pin)+' 1')
        if polaridad == '1': #logica inversa 1 - off, 0 - on
            os.system('gpio -g write '+str(pin)+' 0')
    if estatus == 'True':
        if polaridad == '0': #logica normal 0 - off, 1 - on
            os.system('gpio -g write '+str(pin)+' 0')
        if polaridad == '1': #logica inversa 1 - off, 0 - on
            os.system('gpio -g write '+str(pin)+' 1')
    print(pin, estatus, polaridad)
    
#agregar tarea semanal en la bd
def add_tarea_semanal(nombre, hora, dias, pin, estatus, logica):
    rele = session.query(Relevadores).filter(Relevadores.Pin == str(pin)).one()
    tabla = "tareas" #verificar porque no inserta la nueva fila
    columnas = ("Nombre_tarea","Fecha", "Dias", "Hora", "Nombre", "Pin", "Estatus", "Logica_rele")
    valores = (str(nombre), '', str(dias), str(hora), str(rele.Nombre) ,str(pin), estatus, logica)
    session.execute(f"INSERT INTO {tabla} {columnas} VALUES {valores}")
    session.commit()

#editar tarea semanal en la bd
def editar_tarea_semanal(id, nombre, hora, dias, pin, estatus, logica):
    rele = session.query(Relevadores).filter(Relevadores.Pin == pin).one()
    tarea = session.query(Tareas).filter(Tareas.id == id).one()
    tarea.Nombre_tarea = str(nombre)
    # tarea.Fecha = ''
    tarea.Dias = str(dias)
    tarea.Hora = str(hora)
    tarea.Nombre = str(rele.Nombre)
    tarea.Pin = str(pin)
    tarea.Estatus = int(estatus)
    tarea.Logica_rele = int(logica)
    session.commit()


#borrar tarea
def borrar_tarea(id):
    tarea = session.query(Tareas).filter(Tareas.id == id).one()
    session.delete(tarea)
    session.commit()
    
#funcion de inicio y/o reinicio forzado
def inicio():
    reles = session.query(Relevadores).all()
    for row in reles:
        os.system('gpio -g mode '+str(row.Pin)+' output')
        if row.Estatus == 1:
            if row.Logica == 0: #logica normal 0 - off, 1 - on
                os.system('gpio -g write '+str(row.Pin)+' 1')
            if row.Logica == 1: #logica inversa 1 - off, 0 - on
                os.system('gpio -g write '+str(row.Pin)+' 0')
            #os.system('gpio -g write '+str(row.Pin)+' 1')
        else:
            if row.Logica == 0: #logica normal
                os.system('gpio -g write '+str(row.Pin)+' 0')
            if row.Logica == 1: #logica inversa
                os.system('gpio -g write '+str(row.Pin)+' 1')
            #os.system('gpio -g write '+str(row.Pin)+' 0')
            
    
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
    

def cambios_all(datos):
    #valores = {'A': 4, 'E': 3, 'I': 1, 'O': 0}
    for pin, valor in datos.items():
        if pin != 'codigo' and pin != 'ip':
            x =valor.split(",")
            estatus = x[0]
            logica = x[1]
            rasp = session.query(Relevadores).filter(Relevadores.Pin == str(pin)).one()
            #rasp.Estatus = estatus
            #rasp.Logica = int(logica)
            os.system('gpio -g mode '+str(pin)+' output')
            if estatus == 'true':
                rasp.Estatus = 1
                if logica == '0':
                    rasp.Logica = 0
                    os.system('gpio -g write '+str(pin)+' 1')
                if logica == '1':
                    rasp.Logica = 1
                    os.system('gpio -g write '+str(pin)+' 0')
            else:
                rasp.Estatus = 0
                if logica == '0':
                    rasp.Logica = 0
                    os.system('gpio -g write '+str(pin)+' 0')
                if logica == '1':
                    rasp.Logica = 1
                    os.system('gpio -g write '+str(pin)+' 1')
            session.commit()
            #print('pin=', pin, ', estatus=', estatus, ', logica=', logica)
    

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
        dato = str(row.Pin)+','+str(row.Estatus)+','+str(row.Logica)
        item = {row.Nombre: dato}
        relay.update(item)
    reles = json.dumps(relay)
    return reles

#consulta reles para tareas PENDIENTE CHECAR
# def consultaRelay():
#     drasp = session.query(Relevadores).all()
#     print(drasp)
#     relay = {}
#     for row in drasp:
#         dato = str(row.Pin)+','+str(row.Estatus)+','+str(row.Logica)
#         item = {row.Nombre: dato}
#         relay.update(item)
#     reles = json.dumps(relay)
#     return reles

def consulta_tareas():
    tareas = session.query(Tareas).all()
    array_tareas = {}
    
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
                    #pregunta todos los estados de los reles
                    if codigo == 'estatus_relay':
                        dato = json.dumps(consultaRelay())
                        connection.sendall(bytes(dato, encoding="utf-8"))
                    #cambia la logica de funcionamiento por cada rele 
                    if codigo == 'invertir_rele': 
                        change_logica(format(datos["rele"]), format(datos["check"]), format(datos["estatus"]))
                        dato = 'ok'
                        connection.sendall(dato.encode())
                    #cambia el estado del rele y lo guarda
                    if codigo == 'change_relay':
                        change_relay(format(datos["relay"]),format(datos["pin"]), format(datos["estatus"]))
                        dato = 'ok'
                        connection.sendall(dato.encode())
                    #cambia el nombre y/o pin
                    if codigo == 'cambio_pin':
                        existe = rename_relay(format(datos["name_ant"]), format(datos["pin_ant"]), format(datos["name_new"]), format(datos["pin_new"]) )
                        if existe == 1:
                            dato = 'error'
                            connection.sendall(dato.encode())
                        else:
                            dato = 'ok'
                            connection.sendall(dato.encode())
                    #cambio de todos los parametros
                    if codigo == 'acciones_all':
                        cambios_all(datos)
                        dato = 'ok'
                        connection.sendall(dato.encode())
                    #consulta de todas las tareas
                    if codigo == 'tareas':
                        dato= [Tareas.to_dict() for Tareas in session.query(Tareas).all()]
                        dato = json.dumps(dato)
                        connection.sendall(bytes(dato, encoding="utf-8"))
                    #consulta de los relevadores
                    if codigo == 'reles_tareas':
                        dato= [Relevadores.to_dict() for Relevadores in session.query(Relevadores).all()]
                        dato = json.dumps(dato)
                        connection.sendall(bytes(dato, encoding="utf-8"))
                    #borrar tarea por id
                    if codigo == 'borrar_tarea':
                        borrar_tarea(format(datos["id"]))
                        dato = 'ok'
                        connection.sendall(dato.encode())
                    # agregar una nueva tarea
                    if codigo == 'add_tarea_semanal':
                        add_tarea_semanal(format(datos["nombre_tarea"]), format(datos["hora"]), format(datos["dias"]), format(datos["pin"]), format(datos["estatus"]), format(datos["logica"]))
                        dato = 'ok'
                        connection.sendall(dato.encode())
                    # editar una tarea con el id
                    if codigo == 'editar_tarea_semanal':
                        editar_tarea_semanal(format(datos["id"]), format(datos["nombre_tarea"]), format(datos["hora"]), format(datos["dias"]), format(datos["pin"]), format(datos["estatus"]), format(datos["logica"]))
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
        inicio()
        ban = 1
    
    if ban == 1:
        consulta()
        ban = 2
        
    if ban == 2:
        conexion()
        #aqui pueden ir las diferentes funciones o codigos
        if codigo == 'ip':
            ban = 3
    
    if ban == 3:
        print("ip nuevo:", format(datos['ip_n']))
        print("puerto nuevo:", format(datos['puerto_n']))
        #aqui va funcion para guardar en la bd
        commitconfig(format(datos['ip_n']), format(datos['puerto_n']))
        #funcion que cambia la ip y puerto desde la bd, checar dns y host
        if format(datos['ip_a']) != format(datos['ip_n']):
            change_static_ip(format(datos['ip_n']), '192.168.100.1', '192.168.100.1')
        codigo = 0 #cambiar codigo o reset
        ban = 1 # cambiar bandera o lugar para iniciar nuevo conexion de escucha en socket
        

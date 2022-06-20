from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey
from sqlalchemy import create_engine, update, select
from sqlalchemy.orm import relationship

import socket
import json
import sys
import os
import time
import ipaddress
from crontab import CronTab
from datetime import datetime

#variables importantes
ban = 0
datos = None
ip_nuevo = None
puerto_nuevo = None
codigo = None
sock = None
server_address = None

#cambio de ip y puerto wlan 0
def change_static_wlan(ip_address, routers, dns):
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

#cambio de ip y puerto ethernet
def change_static_eth(ip_address, routers, dns):
    conf_file = '/etc/dhcpcd.conf'
    try:
        with open(conf_file, 'r') as file:
            data = file.readlines()
            
        #wlanFound = next((x for x in data if 'interface wlan0' in x), None)
        wlanFound = next((x for x in data if 'interface eth0' in x), None)
        
        if wlanFound:
            wlanIndex = data.index(wlanFound)
            if data[wlanIndex].startswith('#'):
                data[wlanIndex].replace('#', '')
            
        if wlanIndex:
            data[wlanIndex+1] = f'static ip_address={ip_address}/22\n'
            # data[wlanIndex+2] = f'static routers={routers}\n'
            # data[wlanIndex+3] = f'static domain_name_servers={dns}\n'
            data[wlanIndex+2] = f'static routers=120.10.6.236\n'
            data[wlanIndex+3] = f'static domain_name_servers=8.8.8.8\n'
            data[wlanIndex+4] = f'static domain_search=8.8.4.4\n'
            
        with open(conf_file, 'w') as file:
            file.writelines( data )
            os.system('sudo ifconfig eth0 down')
            os.system('sudo ifconfig eth0 '+ip_address)
            os.system('sudo ifconfig eth0 netmask 255.255.252.0')
            os.system('sudo ifconfig eth0 broadcast 120.10.7.255')
            os.system('sudo ifconfig eth0 up')
            #os.system('sudo reboot')
        
    except Exception as ex:
        logging.exception('IP changing error: %s', ex)
    
    finally:
        pass

#change_static_ip('192.168.100.99', '192.168.100.1', '192.168.100.1')

#Acceso a la base de datos
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Table, MetaData

engine = create_engine('sqlite:////home/pi/listenpi/listenpi/dbase.db', echo = True)
metadata = MetaData(engine)
Session = sessionmaker(bind = engine)
session = Session()
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

class Tareas_sem(Base):
    __tablename__ = 'tareas_sem'
    id = Column(Integer, primary_key = True)
    Nombre_tarea = Column(String(500))
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
            'Dias': self.Dias,
            'Hora': self.Hora,
            'Nombre': self.Nombre,
            'Pin': self.Pin,
            'Estatus': self.Estatus,            
            'Logica': self.Logica_rele,            
        }

class Tareas_ind(Base):
    __tablename__ = 'tareas_ind'
    id = Column(Integer, primary_key = True)
    Nombre_tarea = Column(String(500))
    Fecha = Column(String(50))
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
            'Hora': self.Hora,
            'Nombre': self.Nombre,
            'Pin': self.Pin,
            'Estatus': self.Estatus,            
            'Logica': self.Logica_rele,            
        }

#cambio IP
def commit_ip(d_ip):
    a_rasp = session.query(Configuracion).filter(Configuracion.id == 1).one()
    a_rasp.IP = d_ip
    session.commit()

#cambio Puerto
def commit_puerto(d_puerto):
    a_rasp = session.query(Configuracion).filter(Configuracion.id == 1).one()
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
    os.system("clear")
    print("Los parametros actuales son")
    print("Direccion IP: ", ip,", Puerto: ", puerto)
    print("\n")

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
        print(logica, pin, estatus)
        return "Cambio de estado exitoso"
    else:
        os.system("clear")
        return "Error"

#funcion de inicio y/o reinicio forzado
def inicio():
    reles = session.query(Relevadores).all()
    for row in reles:
        os.system('gpio -g mode '+str(row.Pin)+' output')
        if row.Estatus == 1:
            os.system('gpio -g write '+str(row.Pin)+' 1')
        else:
            os.system('gpio -g write '+str(row.Pin)+' 0')
            
#cambio de nombre al pin
def rename(pin, name):
    raspberry = session.query(Relevadores).filter(Relevadores.Pin == str(pin)).one()
    if raspberry:
        raspberry.Nombre = name
        session.commit()
        os.system("clear")
        print("Cambio de nombre exitoso")
        print("\n")
    else:
        print("\n")
        print("Error")


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
    
#consulta estado relays
def consultaRelay():
    drasp = session.query(Relevadores).all()
    os.system('clear')
    print("\n")
    print("Nombre del relevador  --  Pin   --  Estatus -- Logica")
    print("\n")
    for row in drasp:
        if row.Logica == 0:
            print("Nombre: ",row.Nombre,", Pin:", row.Pin,", Estado: ", row.Estatus, " Logica: normal")
        else:
            print("Nombre: ",row.Nombre,", Pin:", row.Pin,", Estado: ", row.Estatus, " Logica: inversa")

#consulta tareas semanales
def consulta_tareas_sem():
    tareas = session.query(Tareas_sem).all()
    os.system('clear')
    print("\n")
    print("ID   -   Tarea   -   Nombre Pin     -   Pin    -    Dias    -    Hora    -   Acción     -    Lógica")
    print("\n")
    dias_sem = ['D', 'L', 'M', 'Mi', 'J', 'V', 'S']
    for tarea in tareas:
        dias = tarea.Dias
        dias = str(dias).split(',')
        str_dias = ""
        i = 0
        for dia in dias:
            if dia == "1":
                str_dias = str_dias+str(dias_sem[i])+", "
            i=i+1
        print("ID: ", tarea.id, ", Tarea: ", tarea.Nombre_tarea, ", Pin: ", tarea.Pin, ", Dias: ", str_dias, "Hora: ", tarea.Hora, ", Accion: ", "ON" if tarea.Estatus == 1 else "OFF", ", Logica: ", "Normal" if tarea.Logica_rele == 0 else "Inversa")
    print("\n")
    
#consulta tareas independientes
def consulta_tareas_ind():
    tareas = session.query(Tareas_ind).all()
    os.system('clear')
    print("\n")
    print("ID   -   Tarea   -   Nombre Pin  -   Pin    -   Fecha    -   Hora    -   Acción  -   Lógica")
    print("\n")
    for tarea in tareas:
        fecha = str(tarea.Fecha).split('-')
        print("ID: ", tarea.id, ", Tarea: ", tarea.Nombre, ", Nombre Pin: ", tarea.Nombre_tarea, ", Fecha: ", fecha[2]+"/"+fecha[1]+"/"+fecha[0], ", Hora: ", tarea.Hora, "Pin: ", tarea.Pin,", Accion: ", "ON" if tarea.Estatus == 1 else "OFF", ", Logica: ", "Normal" if tarea.Logica_rele == 0 else "Inversa")
    print("\n")

#agregar tarea semanal en la bd
def add_tareas_sem():
    print("\n")
    print("Crear nueva tarea semanal")
    pin = input("Elige el PIN del relevador: ")
    reles = session.query(Relevadores).all()
    ban = 1
    existe_rele = 0
    for rele in reles:
        if rele.Pin == str(pin):
            existe_rele = 1
            break

    while existe_rele == 0:
        print("¡El PIN del relevador no existe!")
        pin = input("Elige el PIN del relevador: ")
        for rele in reles:
            if rele.Pin == str(pin):
                existe_rele = 1
                break
    
    nombre_tarea = input("Elige el nombre de la tarea: ")
    dias_sem = ["Domingo", "Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado"]
    str_dias = ""
    i = 0
    for dia in dias_sem:
        dia =  input("Seleccionar dia: "+dias_sem[i]+" (SI - s, NO - n) : ")
        while dia is not "s" and dia is not "n":
            print("Selecciona una opción valida")
            print("Escribre s para SI y n para NO")
            dia =  input("Seleccionar dia "+dias_sem[i]+" (SI - s, NO - n) : ")
        if dia == "s" and i < 6:
            str_dias = str_dias+"1,"
        elif dia == "n" and i < 6:
            str_dias = str_dias+"0,"
        elif dia == "s" and i == 6:
            str_dias = str_dias+"1"
        elif dia == "n" and i == 6:
            str_dias = str_dias+"0"
        i = i+1

    print("Define la hora de programación")
    hora_prog = input("Digita la hora en formato 24Hrs (00 a 23 Hrs y 00 a 59 Min): ")
    
    while isTimeFormat(hora_prog) is False:
        print("Digita una hora valida")
        hora_prog = input("Digita la hora en formato 24Hrs (00:00 - 23:59 Hrs): ")
    
    hora_prog = str(hora_prog).split(":")
    hora= hora_prog[0] if int(hora_prog[0]) > 9 else "0"+str(int(hora_prog[0]))
    minuto = hora_prog[1] if int(hora_prog[1]) > 9 else "0"+str(int(hora_prog[1]))

    print("Selecciona la accion de la tarea")
    estatus = input("Digita 0 para OFF - Digita 1 para ON: ")
    while estatus is not "0" and estatus is not "1":
         print("Selecciona una opción valida")
         estatus = input("Digita 0 para OFF - Digita 1 para ON: ")

    print("Selecciona la logica a emplear")
    logica = input("Digita 0 para Logica normal - Digita 1 para Logica inversa: ")
    while logica is not "0" and logica is not "1":
         print("Selecciona una opción valida")
         logica = input("Digita 0 para Logica normal - Digita 1 para Logica inversa: ")
    
    print(pin, nombre_tarea, str_dias, hora+":"+minuto, hora, minuto, estatus, logica)
    
    agregar_tarea_sem(nombre_tarea, hora, minuto, str_dias, pin, estatus, logica)

def isTimeFormat(input):
    try:
        time.strptime(input, '%H:%M')
        return True
    except ValueError:
        return False

def isDateFormat(input):
    try:
        time.strptime(input, '%d/%m/%Y')
        return True
    except ValueError:
        return False


def agregar_tarea_sem(nombre, hora, minuto, dias, pin, estatus, logica):
    rele = session.query(Relevadores).filter(Relevadores.Pin == pin).one()
    tabla = "tareas_sem"
    columnas = ("Nombre_tarea", "Dias", "Hora", "Nombre", "Pin", "Estatus", "Logica_rele")
    valores = (nombre, dias, hora+":"+minuto, str(rele.Nombre) , pin, int(estatus), int(logica))
    session.execute(f"INSERT INTO {tabla} {columnas} VALUES {valores}")
    session.commit()

    tarea = session.query(Tareas_sem).filter(Tareas_sem.Nombre_tarea == nombre).one()
    cron = CronTab(user='pi')
    job = cron.new(command='/home/pi/listenpi/listenpienv/bin/python3 /home/pi/listenpi/listenpi/cron_run.py '+pin+' '+estatus+' '+logica, comment='semanal_'+str(tarea.id)) #pin, estatus, logica
    # tiempo = str(hora).split(":")
    cron_hora = hora
    cron_min = minuto
    time_dias = dias.split(",")
    array = []
    i=0
    for dia in time_dias:
        if int(dia) == 1:
            array.append(i)
        i=i+1
    str_dias = ""
    i=0
    for ele in array:
        if i == 0:
            str_dias += str(ele)
        else:
            str_dias += ','+str(ele)
        i=i+1

    job.setall(str(cron_min)+' '+str(cron_hora)+' * * '+str(str_dias))
    cron.write()

#editar tareas semanales
def editar_tareas_sem():
    print("\n")
    print("Editar Tarea")
    id = input("Elige el ID de la tarea a editar: ")
    tareas = session.query(Tareas_sem).all()
    existe_tarea = 0
    for tarea in tareas:
        if tarea.id == int(id):
            existe_tarea = 1
            break
    while existe_tarea == 0:
        print("¡EL ID de la terea no existe!")
        id = input("Elige el ID de la tarea a editar: ")
        for tarea in tareas:
            if tarea.id == int(id):
                existe_tarea = 1
                break
    dias_sem = ['D', 'L', 'M', 'Mi', 'J', 'V', 'S']
    str_dias = ""
    i = 0
    for dia in tarea.Dias:
            if dia == "1":
                str_dias = str_dias+str(dias_sem[i])+", "
            i=i+1
    print("\n")
    consultaRelay()
    print("\n")
    print("Tarea seleccionada:")
    print("ID: ", tarea.id, ", Tarea: ", tarea.Nombre_tarea, ", Pin: ", tarea.Pin, ", Dias: ", str_dias, "Hora: ", tarea.Hora, ", Accion: ", "ON" if tarea.Estatus == 1 else "OFF", ", Logica: ", "Normal" if tarea.Logica_rele == 0 else "Inversa")
    print("\n")
    pin = input("Elige el PIN del relevador: ")
    reles = session.query(Relevadores).all()
    existe_rele = 0
    for rele in reles:
        if rele.Pin == str(pin):
            existe_rele = 1
            break

    while existe_rele == 0:
        print("¡El PIN del relevador no existe!")
        pin = input("Elige el PIN del relevador: ")
        for rele in reles:
            if rele.Pin == str(pin):
                existe_rele = 1
                break
    nombre_tarea = input("Elige el nombre de la tarea: ")
    dias_sem = ["Domingo", "Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado"]
    str_dias = ""
    i = 0
    for dia in dias_sem:
        dia =  input("Seleccionar dia: "+dias_sem[i]+" (SI - s, NO - n) : ")
        while dia is not "s" and dia is not "n":
            print("Selecciona una opción valida")
            print("Escribre s para SI y n para NO")
            dia =  input("Seleccionar dia "+dias_sem[i]+" (SI - s, NO - n) : ")
        if dia == "s" and i < 6:
            str_dias = str_dias+"1,"
        elif dia == "n" and i < 6:
            str_dias = str_dias+"0,"
        elif dia == "s" and i == 6:
            str_dias = str_dias+"1"
        elif dia == "n" and i == 6:
            str_dias = str_dias+"0"
        i = i+1
    
    print("Define la hora de programación")
    timeformat = "%H:%M"
    hora_prog = input("Digita la hora en formato 24Hrs (00 a 23 Hrs y 00 a 59 Min): ")
    
    while isTimeFormat(hora_prog) is False:
        print("Digita una hora valida")
        hora_prog = input("Digita la hora en formato 24Hrs (00:00 - 23:59 Hrs): ")
    
    hora_prog = str(hora_prog).split(":")
    hora= hora_prog[0] if int(hora_prog[0]) > 9 else "0"+str(int(hora_prog[0]))
    minuto = hora_prog[1] if int(hora_prog[1]) > 9 else "0"+str(int(hora_prog[1]))

    print("Selecciona la accion de la tarea")
    estatus = input("Digita 0 para OFF - Digita 1 para ON: ")
    while estatus is not "0" and estatus is not "1":
         print("Selecciona una opción valida")
         estatus = input("Digita 0 para OFF - Digita 1 para ON: ")

    print("Selecciona la logica a emplear")
    logica = input("Digita 0 para Logica normal - Digita 1 para Logica inversa: ")
    while logica is not "0" and logica is not "1":
         print("Selecciona una opción valida")
         logica = input("Digita 0 para Logica normal - Digita 1 para Logica inversa: ")
    
    print(id, pin, nombre_tarea, str_dias, hora+":"+minuto, hora, minuto, estatus, logica)

    editar_tarea_semanal(id, nombre_tarea, hora, minuto, str_dias, pin, estatus, logica)

def editar_tarea_semanal(id, nombre, hora, minuto, dias, pin, estatus, logica):

    rele = session.query(Relevadores).filter(Relevadores.Pin == pin).one()
    tarea = session.query(Tareas_sem).filter(Tareas_sem.id == id).one()
    tarea.Nombre_tarea = str(nombre)
    # tarea.Fecha = ''
    tarea.Dias = str(dias)
    tarea.Hora = str(hora+":"+minuto)
    tarea.Nombre = str(rele.Nombre)
    # tarea.Pin = str(pin)
    tarea.Estatus = int(estatus)
    tarea.Logica_rele = int(logica)
    session.commit()

    my_cron = CronTab(user='pi')
    job_ant = my_cron.find_comment('semanal_'+str(id))
    my_cron.remove(job_ant)
    my_cron.write()
    cron = CronTab(user='pi')
    job = cron.new(command='/home/pi/listenpi/listenpienv/bin/python3 /home/pi/listenpi/listenpi/cron_run.py '+str(pin)+' '+str(estatus)+' '+str(logica), comment='semanal_'+str(id)) #pin, estatus, logica
    # tiempo = str(hora).split(":")
    cron_hora = hora
    cron_min = minuto
    time_dias = str(dias).split(",")
    array = []
    i=0
    for dia in time_dias:
        if int(dia) == 1:
            array.append(i)
        i=i+1
    
    str_dias = ""
    i=0
    for ele in array:
        if i == 0:
            str_dias += str(ele)
        else:
            str_dias += ','+str(ele)
        i=i+1

    job.setall(str(cron_min)+' '+str(cron_hora)+' * * '+str(str_dias))
    cron.write()

#borrar tarea semanal
def borrar_tareas_sem():
    print("\n")
    print("Borrar Tarea")
    id = input("Elige el ID de la tarea a eliminar: ")
    tareas = session.query(Tareas_sem).all()
    existe_tarea = 0
    tarea = ""
    for tar in tareas:
        if tar.id == int(id):
            tarea = tar
            existe_tarea = 1
            break
    while existe_tarea == 0:
        print("¡EL ID de la terea no existe!")
        id = input("Elige el ID de la tarea a eliminar: ")
        for tar in tareas:
            if tar.id == int(id):
                tarea = tar
                existe_tarea = 1
                break
    
    confirmar =  input("Seguro de eliminar tarea:"+tarea.Nombre_tarea+"(SI - s, NO - n) : ")
    while confirmar is not "s" and confirmar is not "n":
        print("Selecciona una opción valida")
        print("Escribre s para SI y n para NO")
        confirmar =  input("Seguro de eliminar tarea:"+tarea.Nombre_tarea+"(SI - s, NO - n) : ")
    # tarea = session.query(Tareas_sem).filter(Tareas_sem.id == id).one()
    my_cron = CronTab(user='pi')
    job = my_cron.find_comment('semanal_'+str(tarea.id))
    my_cron.remove(job)
    my_cron.write()
    session.delete(tarea)
    session.commit()

def add_tareas_ind():
    print("\n")
    print("Crear nueva tarea independiente")
    pin = input("Elige el PIN del relevador: ")
    reles = session.query(Relevadores).all()
    ban = 1
    existe_rele = 0
    for rele in reles:
        if rele.Pin == str(pin):
            existe_rele = 1
            break

    while existe_rele == 0:
        print("¡El PIN del relevador no existe!")
        pin = input("Elige el PIN del relevador: ")
        for rele in reles:
            if rele.Pin == str(pin):
                existe_rele = 1
                break
    nombre_tarea = input("Elige el nombre de la tarea: ")

    print("Define la fecha de programación")
    fecha = input("Digita la fecha en formato dd/mm/yyyy : ")
    
    while isDateFormat(fecha) is False:
        print("Digita una fecha valida")
        fecha = input("Digita la fecha en formato dd/mm/yyyy : ")
    fecha_prog = str(fecha).split("/")
    fecha = fecha_prog[2]+"-"+fecha_prog[1]+"-"+fecha_prog[0]

    print("Define la hora de programación")
    hora_prog = input("Digita la hora en formato 24Hrs (00 a 23 Hrs y 00 a 59 Min): ")
    
    while isTimeFormat(hora_prog) is False:
        print("Digita una hora valida")
        hora_prog = input("Digita la hora en formato 24Hrs (00:00 - 23:59 Hrs): ")
    
    hora_prog = str(hora_prog).split(":")
    hora= hora_prog[0] if int(hora_prog[0]) > 9 else "0"+str(int(hora_prog[0]))
    minuto = hora_prog[1] if int(hora_prog[1]) > 9 else "0"+str(int(hora_prog[1]))

    print("Selecciona la accion de la tarea")
    estatus = input("Digita 0 para OFF - Digita 1 para ON: ")
    while estatus is not "0" and estatus is not "1":
         print("Selecciona una opción valida")
         estatus = input("Digita 0 para OFF - Digita 1 para ON: ")

    print("Selecciona la logica a emplear")
    logica = input("Digita 0 para Logica normal - Digita 1 para Logica inversa: ")
    while logica is not "0" and logica is not "1":
         print("Selecciona una opción valida")
         logica = input("Digita 0 para Logica normal - Digita 1 para Logica inversa: ")
    
    print(pin, nombre_tarea, fecha, hora+":"+minuto, hora, minuto, estatus, logica)
    
    agregar_tarea_ind(nombre_tarea, hora, minuto, fecha, pin, estatus, logica, fecha_prog[0], fecha_prog[1])

#agregar tarea independiente en la bd
def agregar_tarea_ind(nombre, hora, minuto, fecha, pin, estatus, logica, dia, mes):
    rele = session.query(Relevadores).filter(Relevadores.Pin == str(pin)).one()
    tabla = 'tareas_ind'
    columnas = ("Nombre_tarea", "Fecha", "Hora", "Nombre", "Pin", "Estatus", "Logica_rele" )
    valores = (str(nombre), str(fecha), str(hora+":"+minuto), str(rele.Nombre), str(pin), int(estatus), int(logica))
    session.execute(f"INSERT INTO {tabla} {columnas} VALUES {valores}")
    session.commit()

    tarea = session.query(Tareas_ind).filter(Tareas_ind.Nombre_tarea == str(nombre)).one()
    cron = CronTab(user='pi')
    job = cron.new(command='/home/pi/listenpi/listenpienv/bin/python3 /home/pi/listenpi/listenpi/cron_run.py '+str(pin)+' '+str(estatus)+' '+str(logica), comment='independiente_'+str(tarea.id)) #pin, estatus, logica
    # tiempo = str(hora).split(":")
    cron_hora = hora
    cron_min = minuto

    job.setall(str(cron_min)+' '+str(cron_hora)+' '+str(dia)+' '+str(mes)+' *')
    cron.write()

#editar tareas independientes
def editar_tareas_ind():
    print("\n")
    print("Editar Tarea Independiente")
    id = input("Elige el ID de la tarea a editar: ")
    tareas = session.query(Tareas_ind).all()
    existe_tarea = 0
    for tarea in tareas:
        if tarea.id == int(id):
            existe_tarea = 1
            break
    while existe_tarea == 0:
        print("¡EL ID de la terea no existe!")
        id = input("Elige el ID de la tarea a editar: ")
        for tarea in tareas:
            if tarea.id == int(id):
                existe_tarea = 1
                break
    print("\n")
    consultaRelay()
    print("\n")
    print("Tarea seleccionada:")
    print("ID: ", tarea.id, ", Tarea: ", tarea.Nombre_tarea, ", Pin: ", tarea.Pin, ", Fecha: ", tarea.Fecha, "Hora: ", tarea.Hora, ", Accion: ", "ON" if tarea.Estatus == 1 else "OFF", ", Logica: ", "Normal" if tarea.Logica_rele == 0 else "Inversa")

    print("\n")
    pin = input("Elige el PIN del relevador: ")
    reles = session.query(Relevadores).all()
    existe_rele = 0
    for rele in reles:
        if rele.Pin == str(pin):
            existe_rele = 1
            break

    while existe_rele == 0:
        print("¡El PIN del relevador no existe!")
        pin = input("Elige el PIN del relevador: ")
        for rele in reles:
            if rele.Pin == str(pin):
                existe_rele = 1
                break
    nombre_tarea = input("Elige el nombre de la tarea: ")
    print("Define la fecha de programación")
    fecha = input("Digita la fecha en formato dd/mm/yyyy : ")
    
    while isDateFormat(fecha) is False:
        print("Digita una fecha valida")
        fecha = input("Digita la fecha en formato dd/mm/yyyy : ")
    fecha_prog = str(fecha).split("/")
    fecha = fecha_prog[2]+"-"+fecha_prog[1]+"-"+fecha_prog[0]

    print("Define la hora de programación")
    hora_prog = input("Digita la hora en formato 24Hrs (00 a 23 Hrs y 00 a 59 Min): ")
    
    while isTimeFormat(hora_prog) is False:
        print("Digita una hora valida")
        hora_prog = input("Digita la hora en formato 24Hrs (00:00 - 23:59 Hrs): ")
    
    hora_prog = str(hora_prog).split(":")
    hora= hora_prog[0] if int(hora_prog[0]) > 9 else "0"+str(int(hora_prog[0]))
    minuto = hora_prog[1] if int(hora_prog[1]) > 9 else "0"+str(int(hora_prog[1]))

    print("Selecciona la accion de la tarea")
    estatus = input("Digita 0 para OFF - Digita 1 para ON: ")
    while estatus is not "0" and estatus is not "1":
         print("Selecciona una opción valida")
         estatus = input("Digita 0 para OFF - Digita 1 para ON: ")

    print("Selecciona la logica a emplear")
    logica = input("Digita 0 para Logica normal - Digita 1 para Logica inversa: ")
    while logica is not "0" and logica is not "1":
         print("Selecciona una opción valida")
         logica = input("Digita 0 para Logica normal - Digita 1 para Logica inversa: ")
    
    print(pin, nombre_tarea, fecha, hora+":"+minuto, hora, minuto, estatus, logica)
    
    editar_tarea_independiente(id, nombre_tarea, hora, minuto, fecha, pin, estatus, logica, fecha_prog[0], fecha_prog[1])

#agregar cambios a la bd y borrar tarea cron independiente
def editar_tarea_independiente(id, nombre, hora, minuto, fecha, pin, estatus, logica, dia, mes):
    rele = session.query(Relevadores).filter(Relevadores.Pin == pin).one()
    tarea = session.query(Tareas_ind).filter(Tareas_ind.id == id).one()
    tarea.Nombre_tarea = str(nombre)
    # tarea.Fecha = ''
    tarea.Fecha = str(fecha)
    tarea.Hora = str(hora+":"+minuto)
    tarea.Nombre = str(rele.Nombre)
    tarea.Pin = str(pin)
    tarea.Estatus = int(estatus)
    tarea.Logica_rele = int(logica)
    session.commit()

    my_cron = CronTab(user='pi')
    job_ant = my_cron.find_comment('independiente_'+str(id))
    my_cron.remove(job_ant)
    my_cron.write()

    cron = CronTab(user='pi')
    job = cron.new(command='/home/pi/listenpi/listenpienv/bin/python3 /home/pi/listenpi/listenpi/cron_run.py '+str(pin)+' '+str(estatus)+' '+str(logica), comment='independiente_'+str(tarea.id)) #pin, estatus, logica
    # tiempo = str(hora).split(":")
    cron_hora = hora
    cron_min = minuto

    job.setall(str(cron_min)+' '+str(cron_hora)+' '+str(dia)+' '+str(mes)+' *')
    cron.write()

#borrar tarea independiente
def borrar_tarea_ind():
    print("\n")
    print("Borrar Tarea independiente")
    id = input("Elige el ID de la tarea a eliminar: ")
    tareas = session.query(Tareas_ind).all()
    existe_tarea = 0
    tarea = ""
    for tar in tareas:
        if tar.id == int(id):
            tarea = tar
            existe_tarea = 1
            break
    while existe_tarea == 0:
        print("¡EL ID de la terea no existe!")
        id = input("Elige el ID de la tarea a eliminar: ")
        for tar in tareas:
            if tar.id == int(id):
                tarea = tar
                existe_tarea = 1
                break
    
    confirmar =  input("Seguro de eliminar tarea:"+tarea.Nombre_tarea+"(SI - s, NO - n) : ")
    while confirmar is not "s" and confirmar is not "n":
        print("Selecciona una opción valida")
        print("Escribre s para SI y n para NO")
        confirmar =  input("Seguro de eliminar tarea:"+tarea.Nombre_tarea+"(SI - s, NO - n) : ")

    # tarea = session.query(Tareas_ind).filter(Tareas_ind.id == id).one()
    my_cron = CronTab(user='pi')
    job = my_cron.find_comment('independiente_'+str(tarea.id))
    my_cron.remove(job)
    my_cron.write()
    session.delete(tarea)
    session.commit()
    
def crear_tablas():
    tareas_sem = Table( 'tareas_sem', metadata,
                       Column( 'id', Integer, primary_key = True ),
                       Column( 'Nombre_tarea', String(500) ),
                       Column( 'Dias', String(50) ),
                       Column( 'Hora', String(50) ),
                       Column( 'Nombre', String(500) ),
                       Column( 'Pin', String(10) ),
                       Column( 'Estatus', Boolean),
                       Column( 'Logica_rele', Boolean))
    
    tareas_ind = Table( 'tareas_ind', metadata,
                       Column( 'id', Integer, primary_key = True ),
                       Column( 'Nombre_tarea', String(500) ),
                       Column( 'Fecha', String(50) ),
                       Column( 'Hora', String(50) ),
                       Column( 'Nombre', String(500) ),
                       Column( 'Pin', String(10) ),
                       Column( 'Estatus', Boolean),
                       Column( 'Logica_rele', Boolean))
    tareas_sem.create(engine)
    tareas_ind.create(engine)
    
#bucle principal
os.system("clear")

if __name__ == "__main__":
    while True:
        #inicio()
        #ban = 1
        print(" Listado de acciones ")
        print("\n")
        print(" 1 - Lista de relevadores ")
        print(" 2 - Cambiar estado de un relevador ")
        print(" 3 - Cambiar nombre de un relevador ")
        print(" 4 - Tareas programadas semanales ")
        print(" 5 - Tareas programadas independientes ")
        print(" 6 - Cambiar IP estatica WLAN del dispositivo ")
        print(" 7 - Cambiar IP estatica ETHERNET del dispositivo ")
        print(" 8 - Cambiar PUERTO de conexion al portal ")
        print(" 9 - Ingresar IP y PUERTO en la Base de datos del dispotivo ")
        print(" 10 - Crear TABLAS para TAREAS PROGRAMADAS")
        print(" 11 - Salir ")
        print("\n")
        dato = input(" Selecciona una opcion: ")
        comando = int(dato)
        if comando == 1:
            consultaRelay()
            print('\n')
            ban = 0
            
        elif comando == 2:
            consultaRelay()
            print("\n")
            pin = input("Escriba el pin que desea cambiar el estado: ")
            logica = input("Digite 0 para logica normal, 1 para logica inversa: ")
            estado = input("Digete 0 para apagar, 1 para encender: ")
            respuesta = change_relay(logica,pin, estado)
            print(respuesta)
            print("\n")
            ban = 0
        elif comando == 3:
            consultaRelay()
            print("\n")
            pin = input("Escriba el pin al que desea cambiar el nombre: ")
            nombre = input("Escriba el nuevo nombre del pin: ")
            rename(pin, nombre)
            ban = 0
        elif comando == 4:
            while True:
                print("1 - Listado de tareas")
                print("2 - Crear nueva tarea")
                print("3 - Editar una tarea")
                print("4 - Eliminar una tarea")
                print("5 - Regresar al menu anterior")
                print("\n")
                opcion = int(input(" Selecciona una opcion: "))
                if opcion == 1:
                    os.system("clear")
                    consulta_tareas_sem()
                if opcion == 2:
                    os.system("clear")
                    consultaRelay()
                    add_tareas_sem()
                if opcion == 3:
                    os.system("clear")
                    consulta_tareas_sem()
                    editar_tareas_sem()
                if opcion == 4:
                    os.system("clear")
                    consulta_tareas_sem()
                    borrar_tareas_sem()
                elif opcion == 5:
                    break
        elif comando == 5:
            while True:
                print("1 - Listado de tareas")
                print("2 - Crear nueva tarea")
                print("3 - Editar una tarea")
                print("4 - Eliminar una tarea")
                print("5 - Regresar al menu anterior")
                print("\n")
                opcion = int(input(" Selecciona una opcion: "))
                if opcion == 1:
                    os.system("clear")
                    consulta_tareas_ind()
                if opcion == 2:
                    os.system("clear")
                    consultaRelay()
                    add_tareas_ind()
                if opcion == 3:
                    os.system("clear")
                    consulta_tareas_ind()
                    editar_tareas_ind()
                if opcion == 4:
                    os.system("clear")
                    consulta_tareas_ind()
                    borrar_tarea_ind()
                elif opcion == 5:
                    break
        
        elif comando == 6:
            ip2 = 0
            consulta()
            print("La direccion IP del dispositivo va cambiar, actulizar la IP en el portal")
            print("Al cambiar la direccion IP, va perder esta sesion ssh")
            print("\n")
            ip = input("Introduce una direccion IP: ")
            try:
                ip2 = ipaddress.ip_address(ip)
                print('%s is correct IP%s address.' % (ip2, ip2.version))
                change_static_wlan(ip, '192.168.1.254', '192.168.1.254') #verificar, mask y dns
                commit_ip(ip) 
                os.system('nohup /home/pi/listenpi/listenpienv/bin/python3 /home/pi/listenpi/listenpi/menu_4.py &')
                sys.exit()
            except ValueError:
                print('address/netmask is invalid: %s' % ip2)
            except:
                print('Usage : %s ip' % sys.argv[0])
            ban = 0
        
        elif comando == 7:
            ip2 = 0
            consulta()
            print("La direccion IP del dispositivo va cambiar, actulizar la IP en el portal")
            print("Al cambiar la direccion IP, va perder esta sesion ssh")
            print("\n")
            ip = input("Introduce una direccion IP: ")
            try:
                ip2 = ipaddress.ip_address(ip)
                print('%s is correct IP%s address.' % (ip2, ip2.version))
                change_static_eth(ip, '120.10.6.236', '120.10.6.236') #verificar, mask y dns
                commit_ip(ip) 
                os.system('nohup /home/pi/listenpi/listenpienv/bin/python3 /home/pi/listenpi/listenpi/menu_4.py &')
                sys.exit()
            except ValueError:
                print('address/netmask is invalid: %s' % ip2)
            except:
                print('Usage : %s ip' % sys.argv[0])
            ban = 0
        
        elif comando == 8:
            consulta()
            print("Este cambio es para el puerto de acceso al portal")
            puerto = input("Introduce un puerto entre el 3000 y 65500: ")
            print("\n")
            if puerto.isnumeric() and int(puerto) >= 3000 and int(puerto) <= 65500 :
                commit_puerto(puerto)
                os.system("clear")
                print("El puerto de conexion del dispositivo a cambiado, actulizar valor en el portal")
                print("\n")
                ban = 0
            else:
                print("Valor del puerto invalido")
                
        elif comando == 9:
            consulta()
            ip2 = 0
            ip = input("Ingresa la direccion IP: ")
            puerto = input("Ingresa el PUERTO: ")
            try:
                ip2 = ipaddress.ip_address(ip)
                print('%s is correct IP%s address.' % (ip2, ip2.version))
                #change_static_ip(ip, '192.168.100.1', '192.168.100.1') #verificar, mask y dns
                if puerto.isnumeric() and int(puerto) >= 3000 and int(puerto) <= 65500 :
                    commit_ip(ip)
                    commit_puerto(puerto)
                    os.system("clear")
                    print('IP y puerto actualizados en la base de datos')
                    print("\n")
                else:
                    print("Valor del puerto invalido")
            except ValueError:
                print('address/netmask is invalid: %s' % ip2)
            except:
                print('Usage : %s ip' % sys.argv[0])
            ban = 0
            
        elif comando == 10:
            crear_tablas()
            # session.create_all()
            print("tablas creadas")
        elif comando == 11:
            os.system('nohup /home/pi/listenpi/listenpienv/bin/python3 /home/pi/listenpi/listenpi/menu_4.py &')
            sys.exit()
        else:
            print(" Introduce una opcion valida ")


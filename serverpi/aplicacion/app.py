from operator import eq
from typing import final
from flask import Flask, render_template, redirect, url_for, jsonify, request, abort,\
    session
    
from flask_cors import CORS   
    
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from aplicacion import config
from aplicacion.forms import FormEquipo, FormSINO, LoginForm,\
    FormUsuario, FormChangePassword
from werkzeug.utils import secure_filename
from flask_login import LoginManager, login_user, logout_user, login_required,\
    current_user
import os

app = Flask(__name__)
app.config.from_object(config)

Bootstrap(app)
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@app.route('/test', methods =['POST'])
def test():
    import socket
    import json   
    import sys

    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Connect the socket to the port where the server is listening
    server_address = ('192.168.100.99', 3000)
    #print('connecting to {} port {}'.format(*server_address))
    sock.connect(server_address)
    
    dato = None
    try:
        # Send data
        #message = request.json['name']
        #print('sending {!r}'.format(message))
        message = json.dumps(request.json)
        #sock.sendall(message.encode())
        sock.sendall(bytes(message, encoding="utf-8"))
        
        # Look for the response
        amount_received = 0
        amount_expected = len(message)

        while amount_received < amount_expected:
            #data = sock.recv(1024) forma 1
            #dato = data.decode() forma 1
            data = sock.recv(1024)
            data = data.decode("utf-8")
            dato = json.loads(data)
            amount_received += len(dato['estatus'])
            #print('received {!r}'.format(data))
            sock.sendall('')

    finally:
        #print('closing socket')
        sock.close()
        #return jsonify({ "Result": dato[13:15] })
        return jsonify({ "Result": dato['estatus'] })

# Index
@app.route('/')
def index():
    return render_template('index.html')

# Comandos
@app.route('/comandos')
@login_required
def comandos():
    from aplicacion.models import Equipo
    equipos = Equipo.query.all()
    return render_template('comandos.html', equipos=equipos)

#Cliente SSH desde front
@app.route('/paramiko', methods=['POST'])
@login_required
def paramiko():
    import paramiko
    #from aplicacion.models import Equipo
    import json
    
    #raspberry = Equipo.query.filter_by(IP=request.json['ip'])
    
    # Inicia un cliente SSH
    ssh_client = paramiko.SSHClient()
    # Establecer política por defecto para localizar la llave del host localmente
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    # Conectarse, cambiar credebciales por raspberry correcta
    ssh_client.connect(request.json['ip'], 22, 'pi', 'zero123')
    comando = request.json['comando']
    # Ejecutar un comando de forma remota capturando entrada, salida y error estándar
    if comando == 'reinicio':
        msg = 'sudo nohup /home/pi/listenpi/listenpienv/bin/python3 /home/pi/listenpi/listenpi/menu_4.py &'
        entrada, salida, error = ssh_client.exec_command(msg)
        ssh_client.close()
        return 'Comunicación reiniciada'
    elif comando == 'detener':
        msg = 'sudo killall python3'
        entrada, salida, error = ssh_client.exec_command(msg)
        ssh_client.close()
        return 'Comunicación detenida'
    else:
        # Mostrar la salida estándar en pantalla
        entrada, salida, error = ssh_client.exec_command(comando)
        dato = salida.read()
        print(dato)
        # Cerrar la conexión
        ssh_client.close()
    if request.json['comando'] == 'reboot':
        return 'ok'
    return format(dato)

#Tareas programadas test
@app.route('/tareas_test', methods=['GET','POST'])
@login_required
def tareas_test():
    return render_template("tareas.html")

#Tareas agregar tarea
@app.route('/add_tarea', methods=['GET','POST'])
@login_required
def add_tarea():
    from aplicacion.models import Equipo
    import json
    import socket
    dato = None
    raspberry = Equipo.query.filter_by(IP=request.json['ip']).first()
    if raspberry:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_address = (raspberry.IP, int(raspberry.Puerto))
        sock.connect(server_address)
        try:
            message = json.dumps(request.json)
            sock.sendall(bytes(message, encoding="utf-8"))
            dato = sock.recv(1024)
            #data = data.decode("utf-8")
            #dato = json.loads(data)
            if dato == 'ok':
                sock.sendall('')
        finally:
            sock.close()
    return dato
    
#Tareas test raspberry
@app.route('/consulta_tareas', methods=['GET','POST'])
@login_required
def consulta_tareas():
    from aplicacion.models import Equipo
    import json
    import socket
    dato = None
    # raspberry = Equipo.query.filter_by(IP='192.168.100.33').first()
    raspberry = Equipo.query.filter_by(IP=request.args.get('ip')).first()
    if raspberry:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_address = (raspberry.IP, int(raspberry.Puerto))
        sock.connect(server_address)
        try:
            msg = {'codigo': 'tareas'}
            message = json.dumps(msg)
            sock.sendall(bytes(message, encoding="utf-8"))
            data = sock.recv(1024)
            data = data.decode("utf-8")
            # print(data)
            dato = json.loads(data)
            if data == 'ok':
                sock.sendall('')
        finally:
            sock.close()
    return { 'data': dato}

@app.route('/api/data', methods=['GET','POST'])
def data():
    from aplicacion.models import Equipo
    return {'data': [Equipo.to_dict() for Equipo in Equipo.query]}

#Tareas programadas
@app.route('/tareas/<id>', methods=['GET','POST'])
@login_required
def tareas(id):
    from aplicacion.models import Equipo
    import json
    import socket
    raspberry = Equipo.query.filter_by(id=id).first()
    dato = None
    if raspberry is None:
        return render_template("acciones.html")
    else:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_address = (raspberry.IP, int(raspberry.Puerto))
        sock.connect(server_address)
        try:
            msg = {'codigo': 'estatus_relay'}
            #data = json.dumps(msg)
            message = json.dumps(msg)
            sock.sendall(bytes(message, encoding="utf-8"))
            data = sock.recv(1024)
            data = data.decode("utf-8")
            dato = json.loads(data)
            if dato == 'ok':
                sock.sendall('')
        finally:
            sock.close()
            return render_template('tareas.html', raspberry = raspberry, reles = dato)
        
        return render_template("acciones.html")
    
#Polaridad relevadores -----------------
@app.route('/polaridad', methods=['GET','POST'])
@login_required
def polaridad():
    from aplicacion.models import Equipo
    import json
    import socket
    dato = None
    raspberry = Equipo.query.filter_by(IP=request.json['ip']).first()
    if raspberry:
        raspberry.Polaridad_rele = request.json['check']
        db.session.commit()
        #agregar retorno de validacion, y cambio de polaridad real

@app.route('/acciones_all', methods=['GET', 'POST'])
@login_required
def acciones_all():
    from aplicacion.models import Equipo
    import json
    import socket
    dato  = None
    raspberry = Equipo.query.filter_by(IP=request.json['ip']).first()
    if raspberry:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_address = (raspberry.IP, int(raspberry.Puerto))
        sock.connect(server_address)
        try:
            message = json.dumps(request.json)
            sock.sendall(bytes(message, encoding="utf-8"))
            dato = sock.recv(1024)
            if dato == 'ok':
                sock.sendall('')
        finally:
            sock.close()
    return dato 

#Cambio de Polaridad por relevador
@app.route('/polaridad_rele', methods=['GET', 'POST'])
@login_required
def polaridad_rele():
    from aplicacion.models import Equipo
    import json
    import socket
    dato = None
    raspberry = Equipo.query.filter_by(IP=request.json['ip']).first()
    if raspberry:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_address = (raspberry.IP, int(raspberry.Puerto))
        sock.connect(server_address)
        try:
            message = json.dumps(request.json)
            sock.sendall(bytes(message, encoding="utf-8"))
            dato = sock.recv(1024)
            if dato == 'ok':
                sock.sendall('')
        finally:
            sock.close()
    return dato

    
#Cambio rele manual
@app.route('/change_relay', methods=['POST'])
@login_required
def change_relay():
    from aplicacion.models import Equipo
    import json
    import socket
    dato = None
    raspberry = Equipo.query.filter_by(Nombre=request.json['name']).first()
    if raspberry:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_address = (raspberry.IP, int(raspberry.Puerto))
        sock.connect(server_address)
        try:
            message = json.dumps(request.json)
            sock.sendall(bytes(message, encoding="utf-8"))
            dato = sock.recv(1024)
            #data = data.decode("utf-8")
            #dato = json.loads(data)
            if dato == 'ok':
                sock.sendall('')
        finally:
            sock.close()
    return dato

#Modal datos reles
@app.route('/reles', methods=['GET', 'POST'])
# @login_required
def reles():
    from aplicacion.models import Equipo
    import json
    import socket
    dato = None
    raspberry = Equipo.query.filter_by(IP=request.json['ip']).first()
    if raspberry:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_address = (raspberry.IP, int(raspberry.Puerto))
        sock.connect(server_address)
        try:
            message = json.dumps(request.json)
            sock.sendall(bytes(message, encoding="utf-8"))
            data = sock.recv(1024)
            data = data.decode("utf-8")
            dato = json.loads(data)
            if data == 'ok':
                sock.sendall('')
        finally:
            sock.close()
    return dato

#Editar relevadores
@app.route('/reles/editar', methods=["get", "post"])
@login_required
def editarreles():
    from aplicacion.models import Equipo
    import json
    import socket
    dato = None
    raspberry = Equipo.query.filter_by(IP=request.json['ip']).first()
    if raspberry:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_address = (raspberry.IP, int(raspberry.Puerto))
        sock.connect(server_address)
        try:
            message = json.dumps(request.json)
            sock.sendall(bytes(message, encoding="utf-8"))
            dato = sock.recv(1024)
            #data = data.decode("utf-8")
            #dato = json.loads(data)
            if dato == 'ok' or dato == 'error':
                sock.sendall('')
        finally:
            sock.close()
    return dato
    

#Acciones
@app.route('/acciones')
@login_required
def acciones():
    from aplicacion.models import Equipo
    raspberrys = Equipo.query.all()
    return render_template('acciones.html', raspberrys=raspberrys)

# @app.route('/configuracion')
# @app.route('/configuracion/<id>')
# @login_required
# def configuracion(id='0'):
#     from aplicacion.models import Equipo
#     raspberry = Equipo.query.get(id)
#     if id == '0':
#         # equipos = Equipo.query.all()
#         raspberry = Equipo.query.first()
#     else:
#         raspberry = Equipo.query.get(id)
#     equipos = Equipo.query.all()
#     return render_template('configuracion.html', equipos=equipos, raspberry=raspberry)

#Actualizar parametros a la raspberry con websockets
@app.route('/actualizar_parametros', methods=['POST'])
@login_required
def actualizar_parametros():
    import socket
    import json
    import sys
    ip_a = request.json['ip_a'] #ip anterior
    puerto_a = request.json['puerto_a'] #puerto anterior
    ip_n  = request.json['ip_n'] #ip nuevo
    puerto_n = request.json['puerto_n'] #puerto nuevo
    dato = None
    from aplicacion.models import Equipo
    raspberry = Equipo.query.filter_by(IP=ip_n).first()
    if raspberry is None or (ip_a == ip_n and puerto_a != puerto_n):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_address = (request.json['ip_a'], int(request.json['puerto_a']))
        sock.connect(server_address)
        try:
            message = json.dumps(request.json)
            sock.sendall(bytes(message, encoding="utf-8"))
            data = sock.recv(1024)
            dato = data.decode()
            if data == 'ok':
                sock.sendall('')
        finally:
            sock.close()
            rasp = Equipo.query.filter_by(Nombre = request.json['nombre']).first()
            rasp.IP = ip_n
            rasp.Puerto = puerto_n
            db.session.commit()
        #print('connecting to {} port {}'.format(*server_address))
    else: 
        dato = 'error'
    return jsonify({"estatus" : format(dato) })
    #return jsonify({"codigo" : request.json['codigo']
     #               ,"ip actual" : request.json['ip_a'],
      #              "puerto actual" : request.json['puerto_a'],
       #             "ip nuevo" : request.json['ip_n'],
        #            "puerto nuevo" : request.json['puerto_n'],
         #           })
    

# Anexar nuevos dispositivos
@app.route('/raspberrynew', methods=["get", "post"])
@login_required
def raspberrynew():
    from aplicacion.models import Equipo
    form = FormEquipo()
    if form.validate_on_submit():
        existe_nombre = Equipo.query.\
            filter_by(Nombre=form.Nombre.data).first()
        existe_puerto = Equipo.query.\
            filter_by(Puerto=form.Puerto.data).first()
        existe_ip = Equipo.query.\
            filter_by(IP=form.IP.data).first()
        if existe_nombre:
            form.Nombre.errors.append("¡El nombre del dispositivo ya existe!")
        elif existe_ip:
            form.IP.errors.append("¡La direccion IP ya existe!")
        elif existe_puerto:
            form.Puerto.errors.append("¡El puerto ya existe!")
        else:
            eq = Equipo()
            form.populate_obj(eq)
            db.session.add(eq)
            db.session.commit()
            rasp_id = Equipo.query.filter_by(Nombre=form.Nombre.data).first()
            return redirect(url_for('configuracion', id=rasp_id.id))
    equipos = Equipo.query.all()
    return render_template('raspberrynew.html', form=form, raspberry = None, equipos = equipos )

# Edicion de dispositivos existentes
@app.route('/configuracion/edit', methods=["get", "post"])
@app.route('/configuracion/edit/<id>', methods=["get", "post"])
@login_required
def configuracion(id='0'):
    from aplicacion.models import Equipo
    raspberry = Equipo.query.filter_by(id=id).first()
    # if raspberry is None OR not current_user.is_admin():
    if raspberry is None:
        raspberry = Equipo.query.first()
    form = FormEquipo(request.form, obj=raspberry)
    if form.validate_on_submit():
        existe_nombre = Equipo.query.\
            filter_by(Nombre=form.Nombre.data).first()
        existe_ip = Equipo.query.\
            filter_by(IP=form.IP.data).first()
        existe_puerto = Equipo.query.\
            filter_by(Puerto=form.Puerto.data).first()
        if existe_nombre is None or raspberry.Nombre == form.Nombre.data:
            if existe_ip is None or raspberry.IP == form.IP.data:
                if existe_puerto is None or raspberry.Puerto == form.Puerto.data:
                    form.populate_obj(raspberry)
                    db.session.add(raspberry)
                    db.session.commit()
                    return redirect(url_for('configuracion', id = raspberry.id))
        if existe_nombre and form.Nombre.data != raspberry.Nombre:
            form.Nombre.errors.append("¡El nombre del dispositivo ya existe!")
        if existe_ip and form.IP.data != raspberry.IP:
            form.IP.errors.append("¡La direccion IP ya existe!")
        if existe_puerto and form.Puerto.data != raspberry.Puerto:
            form.Puerto.errors.append("¡El puerto ya existe!")
    equipos = Equipo.query.all()
    return render_template('raspberrynew.html', form=form, ban=True, raspberry = raspberry, equipos = equipos)

# Eliminar dispositivo
@app.route('/raspberry/delete/<id>', methods=["get", "post"])
@login_required
def raspberrydelete(id):
    from aplicacion.models import Equipo
    # Control de permisos
    if not current_user.is_admin():
        abort(404)
    raspberry = Equipo.query.get(id)
    if raspberry is None:
        abort(404)
    form = FormSINO()
    if form.validate_on_submit():
        if form.si.data:
            db.session.delete(raspberry)
            db.session.commit()
            return redirect(url_for("configuracion"))
        return redirect(url_for("configuracion", id=id))
    return render_template("raspberrydelete.html", form=form, raspberry=raspberry)

###########################################################

# @app.route('/categoria')
# @app.route('/categoria/<id>')
# @login_required
# def inicio(id='0'):
#     from aplicacion.models import Articulos, Categorias
#     categoria = Categorias.query.get(id)
#     if id == '0':
#         articulos = Articulos.query.all()
#     else:
#         articulos = Articulos.query.filter_by(CategoriaId=id)
#     categorias = Categorias.query.all()
#     return render_template("inicio.html", articulos=articulos,
#                            categorias=categorias, categoria=categoria)


# @app.route('/categorias')
# @login_required
# def categorias():
#     from aplicacion.models import Categorias
#     categorias = Categorias.query.all()
#     return render_template("categorias.html", categorias=categorias)


# @app.route('/categorias/new', methods=["get", "post"])
# @login_required
# def categorias_new():
#     from aplicacion.models import Categorias
#     # Control de permisos
#     if not current_user.is_admin():
#         abort(404)
#     form = FormCategoria(request.form)
#     if form.validate_on_submit():
#         cat = Categorias(nombre=form.nombre.data)
#         db.session.add(cat)
#         db.session.commit()
#         return redirect(url_for("categorias"))
#     else:
#         return render_template("categorias_new.html", form=form)


# @app.route('/categorias/<id>/edit', methods=["get", "post"])
# @login_required
# def categorias_edit(id):
#     from aplicacion.models import Categorias
#     # Control de permisos
#     if not current_user.is_admin():
#         abort(404)
#     cat = Categorias.query.get(id)
#     if cat is None:
#         abort(404)
#     form = FormCategoria(request.form, obj=cat)
#     if form.validate_on_submit():
#         form.populate_obj(cat)
#         db.session.commit()
#         return redirect(url_for("categorias"))
#     return render_template("categorias_new.html", form=form)


# @app.route('/categorias/<id>/delete', methods=["get", "post"])
# @login_required
# def categorias_delete(id):
#     from aplicacion.models import Categorias
#     # Control de permisos
#     if not current_user.is_admin():
#         abort(404)
#     cat = Categorias.query.get(id)
#     if cat is None:
#         abort(404)
#     form = FormSINO()
#     if form.validate_on_submit():
#         if form.si.data:
#             db.session.delete(cat)
#             db.session.commit()
#         return redirect(url_for("categorias"))
#     return render_template("categorias_delete.html", form=form, cat=cat)


# @app.route('/articulos/new', methods=["get", "post"])
# @login_required
# def articulos_new():
#     from aplicacion.models import Articulos, Categorias
#     # Control de permisos
#     if not current_user.is_admin():
#         abort(404)
#     form = FormArticulo()
#     categorias = [(c.id, c.nombre) for c in Categorias.query.all()[1:]]
#     form.CategoriaId.choices = categorias
#     if form.validate_on_submit():
#         try:
#             f = form.photo.data
#             nombre_fichero = secure_filename(f.filename)
#             f.save(app.root_path + "/static/upload/" + nombre_fichero)
#         except:
#             nombre_fichero = ""
#         art = Articulos()
#         form.populate_obj(art)
#         art.image = nombre_fichero
#         db.session.add(art)
#         db.session.commit()
#         return redirect(url_for("inicio"))
#     else:
#         return render_template("articulos_new.html", form=form)


# @app.route('/articulos/<id>/edit', methods=["get", "post"])
# @login_required
# def articulos_edit(id):
#     from aplicacion.models import Articulos, Categorias
#     # Control de permisos
#     if not current_user.is_admin():
#         abort(404)
#     art = Articulos.query.get(id)
#     if art is None:
#         abort(404)
#     form = FormArticulo(obj=art)
#     categorias = [(c.id, c.nombre) for c in Categorias.query.all()[1:]]
#     form.CategoriaId.choices = categorias
#     if form.validate_on_submit():
#         # Borramos la imagen anterior si hemos subido una nueva
#         if form.photo.data:
#             os.remove(app.root_path + "/static/upload/" + art.image)
#             try:
#                 f = form.photo.data
#                 nombre_fichero = secure_filename(f.filename)
#                 f.save(app.root_path + "/static/upload/" + nombre_fichero)
#             except:
#                 nombre_fichero = ""
#         else:
#             nombre_fichero = art.image
#         form.populate_obj(art)
#         art.image = nombre_fichero
#         db.session.commit()
#         return redirect(url_for("inicio"))
#     return render_template("articulos_new.html", form=form)


# @app.route('/articulos/<id>/delete', methods=["get", "post"])
# @login_required
# def articulos_delete(id):
#     from aplicacion.models import Articulos
#     # Control de permisos
#     if not current_user.is_admin():
#         abort(404)
#     art = Articulos.query.get(id)
#     if art is None:
#         abort(404)
#     form = FormSINO()
#     if form.validate_on_submit():
#         if form.si.data:
#             if art.image != "":
#                 os.remove(app.root_path + "/static/upload/" + art.image)
#             db.session.delete(art)
#             db.session.commit()
#         return redirect(url_for("inicio"))
#     return render_template("articulos_delete.html", form=form, art=art)


@app.route('/login', methods=['get', 'post'])
def login():
    from aplicacion.models import Usuarios
    # Control de permisos
    if current_user.is_authenticated:
        return redirect(url_for("inicio"))
    form = LoginForm()
    if form.validate_on_submit():
        user = Usuarios.query.filter_by(username=form.username.data).first()
        if user is not None and user.verify_password(form.password.data):
            login_user(user)
            next = request.args.get('next')
            return redirect(next or url_for('acciones'))
        form.username.errors.append("Usuario o contraseña incorrectas.")
    return render_template('login.html', form=form)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route("/registro", methods=["get", "post"])
def registro():
    from aplicacion.models import Usuarios
    # Control de permisos
    # if current_user.is_authenticated:
    #     return redirect(url_for("inicio"))
    form = FormUsuario()
    if form.validate_on_submit():
        existe_usuario = Usuarios.query.\
            filter_by(username=form.username.data).first()
        if existe_usuario is None:
            user = Usuarios()
            form.populate_obj(user)
            user.admin = False
            db.session.add(user)
            db.session.commit()
            if current_user.is_authenticated and current_user.admin == 1:
                return redirect(url_for('perfil', username = form.username.data))
            return redirect(url_for("login"))
        form.username.errors.append("Nombre de usuario ya existe.")
    if current_user.is_authenticated and current_user.admin == 1:
        users = Usuarios.query.all()
        return render_template("usuarios_new.html", form=form, users=users, user_a = None)
    return render_template("usuarios_new.html", form=form)


@app.route('/perfil/<username>', methods=["get", "post"])
@login_required
def perfil(username):
    if username == current_user.username or current_user.admin == 1:
        from aplicacion.models import Usuarios
        user = Usuarios.query.filter_by(username=username).first()
        if user is None:
            abort(404)
        form = FormUsuario(request.form, obj=user)
        del form.password
        if form.validate_on_submit():
            existe_usuario = Usuarios.query.\
            filter_by(username=form.username.data).first()
            if existe_usuario is None or user.username == form.username.data:
                form.populate_obj(user)
                db.session.commit()
                return redirect(url_for('perfil', username = form.username.data))
            form.username.errors.append("Nombre de usuario ya existe.")
        if current_user.admin == 1:
            users = Usuarios.query.all()
            return render_template("usuarios_new.html", form=form, perfil=True, users=users, user_a = user)
        else:
            return render_template("usuarios_new.html", form=form, perfil=True, user_a = user)
    else:
        return redirect(url_for('index'))

@app.route('/perfil/delete/<username>', methods=["get", "post"])
@login_required
def perfildelete(username):
    from aplicacion.models import Usuarios
    if not current_user.is_admin():
        abort(404)
    user = Usuarios.query.\
            filter_by(username= username).first()
    if user is None or user.admin == 1:
        abort(404)
    form = FormSINO()
    if form.validate_on_submit():
        if form.si.data:
            db.session.delete(user)
            db.session.commit()
            return redirect(url_for('perfil', username = current_user.username))
        return redirect(url_for('perfil', username = username))
    return render_template('perfildelete.html', form=form, user = user.username)


@app.route('/changepassword/<username>', methods=["get", "post"])
@login_required
def changepassword(username):
    if username == current_user.username or current_user.admin == 1:
        from aplicacion.models import Usuarios
        user = Usuarios.query.filter_by(username=username).first()
        if user is None:
            abort(404)
        form = FormChangePassword()
        if form.validate_on_submit():
            form.populate_obj(user)
            db.session.commit()
            return redirect(url_for('perfil', username=username))
        return render_template("changepassword.html", form=form, user=user.username)
    else:
        return redirect(url_for('index'))


@login_manager.user_loader
def load_user(user_id):
    from aplicacion.models import Usuarios
    return Usuarios.query.get(int(user_id))


@app.errorhandler(404)
def page_not_found(error):
    return render_template("error.html", error="Página no encontrada..."), 404

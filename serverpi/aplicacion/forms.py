from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, DecimalField, IntegerField,\
    TextAreaField, SelectField, PasswordField
from wtforms.fields.core import BooleanField
from wtforms.fields.html5 import EmailField
from flask_wtf.file import FileField
from wtforms.validators import Required

class FormEquipo(FlaskForm):
    Nombre = StringField("Nombre:",
                         validators=[Required("Tienes que introducir el Nombre")])
    IP = StringField("Direccion IP:",
                          validators=[Required("Tienes que introducir una IP")])
    Puerto = StringField("Puerto:",
                        validators=[Required("Tienes que introducir un Puerto")])
    Polaridad_rele = BooleanField("Invertido:")
    Descripcion = StringField("Descripción:",
                          validators=[Required("Tienes que introducir una descripción")
                                      ])
    # photo = FileField('Selecciona imagen:')
    # stock = IntegerField("Stock:", default=1,
    #                      validators=[Required("Tienes que introducir el dato")]
    #                      )
    # CategoriaId = SelectField("Categoría:", coerce=int)
    submit = SubmitField('Guardar')


# class FormCategoria(FlaskForm):
#     nombre = StringField("Nombre:",
#                          validators=[Required("Tienes que introducir el dato")]
#                          )
#     submit = SubmitField('Enviar')


# class FormArticulo(FlaskForm):
#     nombre = StringField("Nombre:",
#                          validators=[Required("Tienes que introducir el nombre")]
#                          )
#     precio = DecimalField("Precio:", default=0,
#                           validators=[Required("Tienes que introducir el precio")
#                                       ])
#     iva = IntegerField("IVA:", default=21,
#                        validators=[Required("Tienes que introducir el dato")])
#     descripcion = TextAreaField("Descripción:")
#     photo = FileField('Selecciona imagen:')
#     stock = IntegerField("Stock:", default=1,
#                          validators=[Required("Tienes que introducir el dato")]
#                          )
#     CategoriaId = SelectField("Categoría:", coerce=int)
#     submit = SubmitField('Enviar')


class FormSINO(FlaskForm):
    si = SubmitField('Si')
    no = SubmitField('No')


class LoginForm(FlaskForm):
    username = StringField('Usuario', validators=[Required()])
    password = PasswordField('Contraseña', validators=[Required()])
    submit = SubmitField('Entrar')


class FormUsuario(FlaskForm):
    username = StringField('Usuario', validators=[Required()])
    password = PasswordField('Contraseña', validators=[Required()])
    nombre = StringField('Nombre completo')
    email = EmailField('Correo eléctronico')
    submit = SubmitField('Aceptar')


class FormChangePassword(FlaskForm):
    password = PasswordField('Contraseña nueva', validators=[Required()])
    submit = SubmitField('Aceptar')

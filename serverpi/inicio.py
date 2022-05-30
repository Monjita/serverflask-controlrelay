import os
import sys

path = '/home/servidor/serverpi/serverpi'

os.chdir( path )

#os.system('source home/servidor/serverpi/serverpienv/bin/activate')
#--virtualenv /path/to/virtual/environment.
#/home/servidor/serverpi/serverpienv/bin/uwsgi
os.system('~/serverpi/serverpienv/bin/uwsgi --virtualenv /home/servidor/serverpi/serverpienv/ --socket 0.0.0.0:8080 --protocol=http --enable-threads --processes 5 --threads 3 --wsgi-file wsgi.py --callable app')


#~/serverpi/serverpienv/bin/uwsgi --virtualenv /home/servidor/serverpi/serverpienv/ --socket 0.0.0.0:8765 --protocol=http --enable-threads --processes 5 --threads 3 --wsgi-file wsgi.py --callable app

#comando de crontab
# @reboot /home/servidor/serverpi/serverpienv/bin/python3 /home/servidor/serverpi/serverpi/inicio.py

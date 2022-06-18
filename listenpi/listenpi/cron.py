from crontab import CronTab
cron = CronTab(user='pi')
job = cron.new(command='/home/pi/listenpi/listenpienv/bin/python3 /home/pi/listenpi/listenpi/cron_run.py 5 1 0', comment='cron_1') #pin, estatus, logica
job.setall("48 11 30 5 1")
cron.write()
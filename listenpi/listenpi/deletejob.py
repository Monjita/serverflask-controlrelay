from crontab import CronTab
my_cron = CronTab(user='pi')
for job in my_cron:
    print(job.comment)
    # if job.comment == 'cron_1':
        # my_cron.remove(job)
        # my_cron.write()
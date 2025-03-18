from datetime import datetime, timedelta


print(datetime.now() + timedelta(minutes=-(datetime.now().minute % 30), seconds=-datetime.now().second))

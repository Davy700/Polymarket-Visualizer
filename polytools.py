from datetime import datetime
import pytz

def GetQuarterEpoch():
    et_now = datetime.now(pytz.timezone("EST"))
    quarter_minute = (et_now.minute // 15) * 15
    floored_dt = et_now.replace(minute=quarter_minute, second=0, microsecond=0)
    return int(floored_dt.timestamp())
import re

from app.services.joi_tool import extract_last_code_block, parse_scenarios


def extract_last_code_block2(text):
  """
  문자열에서 마지막 코드 블록을 추출합니다.
  코드 블록은 ```로 시작하고 끝나는 부분으로 정의됩니다.
  """
  pattern = r"```(?:[^\n]*)\n(.*?)```"
  matches = re.findall(pattern, text, re.DOTALL)
  return matches[-1].strip() if matches else None
s = """
```plaintext
# Input
```
Current Time: 2025-06-18 02:52:59
Generate JOI Lang code for "Toggle the lights in all Greenhouse B every 2 seconds, and close all the windows in each greenhouse when the soil moisture in that greenhouse is above 30."
```

# Output
```
name = "Scenario1"
cron = ""
period = 2000
all(#Light #greenhouseB).switch_toggle()

---
name = "Scenario2"
cron = ""
period = 100
all(#Window #greenhouseA).windowControl_close()
all(#Window #greenhouseB).windowControl_close()
all(#Window #greenhouseC).windowControl_close()

---
name = "Scenario3"
cron = ""
period = 100
if (any(#SoilMoistureSensor #greenhouseA).soilHumidityMeasurement_soilHumidity > 30.0) {
  all(#Window #greenhouseA).windowControl_close()
}

if (any(#SoilMoistureSensor #greenhouseB).soilHumidityMeasurement_soilHumidity > 30.0) {
  all(#Window #greenhouseB).windowControl_close()
}

if (any(#SoilMoistureSensor #greenhouseC).soilHumidityMeasurement_soilHumidity > 30.0) {
  all(#Window #greenhouseC).windowControl_close()
}
```

# Explanation
- **Scenario1**: Toggles the lights in all greenhouses B every 2 seconds continuously.
- **Scenario2**: Closes all windows in all greenhouses A, B, and C every 100 ms continuously.
- **Scenario3**: Checks the soil moisture in all greenhouses A, B, and C every 100 ms. If the soil moisture is greater than 30%, it closes all windows in those respective greenhouses.

This setup ensures continuous control while also checking conditions periodically.
"""
s = """
```plaintext
name = "Scenario1"
cron = ""
period = -1  # period comment
(#Window #GreenhouseA).windowControl_open() // this is a comment
all(#Irrigator #GreenhouseA).switch_on()  //also
```

This script will execute immediately upon generation and close all windows and turn on all irrigators located in Greenhouse A.
"""
print(extract_last_code_block(s))
ret = parse_scenarios(extract_last_code_block(s))
print(ret)
print(ret['code'][0]['code'])
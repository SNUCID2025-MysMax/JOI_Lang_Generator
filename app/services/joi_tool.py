import re,json,os,copy

def remove_line_comment(line: str) -> str:
    # //로 시작하는 주석 제거 (줄 끝 주석 포함)
    return re.sub(r'\s*//.*$', '', line).rstrip()

def parse_scenarios(script: str):
    """
    생성된 문자열에서 시나리오 코드를 파싱하여 딕셔너리 형태로 반환합니다.
    """
    parts = [part.strip() for part in script.strip().split('---') if part.strip()]
    scenarios = []

    for part in parts:
        raw_lines = part.strip().splitlines()
        lines = [remove_line_comment(line) for line in raw_lines if remove_line_comment(line).strip()]

        name = lines[0].split('=', 1)[1].strip().strip('"')
        cron = lines[1].split('=', 1)[1].strip().strip('"')
        period = int(lines[2].split('=', 1)[1].strip())
        code = "\n".join(lines[3:]).strip() + "\n"  # 줄바꿈 포함시켜 | 출력 유도

        scenarios.append({
            "name": name,
            "cron": cron,
            "period": period,
            "code": code
        })

    return {
      "code": scenarios
    }

def extract_last_code_block(text):
  """
  문자열에서 마지막 코드 블록을 추출합니다.
  코드 블록은 ```로 시작하고 끝나는 부분으로 정의됩니다.
  """
  pattern = r"```(?:[^\n]*)\n(.*?)```"
  matches = re.findall(pattern, text, re.DOTALL)
  return matches[-1].strip() if matches else None

def extract_device_tags(connected_devices: dict, device_classes: dict) -> tuple:
    """
    연결된 디바이스의 태그를 추출하고, 디바이스 클래스에 해당하는 태그와
    다른 태그를 분리하여 딕셔너리 형태로 반환합니다.
    """
    unique_tag_sets = {frozenset(connected_devices[k]['tags']) for k in connected_devices}
    tag_sets = [list(tag_set) for tag_set in unique_tag_sets]

    tag_device = {}
    for tag_set in tag_sets:
        device_tags = [tag for tag in tag_set if tag in device_classes]
        other_tags = [tag for tag in tag_set if tag not in device_classes]

        for device_tag in device_tags:
            if device_tag not in tag_device:
                tag_device[device_tag] = []
            tag_device[device_tag].extend(other_tags)
    
    return tag_device, tag_sets

def add_device_tags(device_classes: dict, tag_device: dict) -> dict:
    """
    각 디바이스 설명에 태그를 추가합니다.
    """
    updated_classes = copy.deepcopy(device_classes)
    
    for device_tag, extra_tags in tag_device.items():
        doc = updated_classes[device_tag]
        lines = doc.splitlines()
        new_lines = lines[:4] + [f"    #{tag}" for tag in sorted(set(extra_tags))] + lines[4:]
        updated_classes[device_tag] = "\n".join(new_lines)
    
    return updated_classes

if __name__ == "__main__":
    script = """
    name = "Scenario1"
    cron = "0 9 * * 1-5"
    period = 0
    if (((#Window).contactContactSensor_contact == 'closed') and (#AirQualityDetector).carbonDioxideMeasurement_carbonDioxide >= 1000 and (#AirQualityDetector).temperatureMeasurement_temperature >= 30.0) {
      (#Clock).clock_delay(0, 0, 5)
      (#Window).windowControl_open()
      if ((#Fan).switch_switch == 'off' ) {
        (#Fan).switch_on()
      }
    }
    ---
    name = "Scenario2"
    cron = ""
    period = 100
    count := 0
    if ((#AirQualityDetector).dustSensor_fineDustLevel >= 50) {
      count = count + 1
    } else {
      count = 0
      }
    if (count >= 60) {
      (#Window).windowControl_close()
      (#Fan).switch_off()
      if ((#HumiditySensor).relativeHumidityMeasurement_humidity <= 40.0){
        (#Humidifier).switch_on()
      }
      if ((#SoilMoistureSensor).soilHumidityMeasurement_soilHumidity <= 25.0 and (#Irrigator).switch_switch == 'off') {
        (#Irrigator).switch_on()
      }
    }
    """
    
    print(parse_scenarios(extract_last_code_block(script)))
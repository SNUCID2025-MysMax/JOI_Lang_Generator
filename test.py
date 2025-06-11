import re

text = '''Device Speaker:
  """
  Tags:
    #Speaker

  Enums:
    switchEnum: [on, off]
    playbackEnum: [paused, playing, stopped, fast forward, rewinding, buffering]'''


match = re.search(r'Device\s+\w+:(?:.*?\n)*?(?=^\s*Enums:)', text, re.MULTILINE)
if match:
    print(match.group().strip())
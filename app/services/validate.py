import re, json
from sentence_transformers import SentenceTransformer, util
from services.translate import deepl_translate

THRESHOLD = 0.7 

def extract_classes_by_name(text: str):
    # pattern = r'class\s+(\w+)\s*:\s*\n\s+"""(.*?)"""'
    pattern = r'Device\s+(\w+)\s*:\s*\n\s+"""(.*?)"""'
    matches = re.finditer(pattern, text, re.DOTALL)

    class_dict = {}
    for match in matches:
        class_name = match.group(1)
        full_class_def = match.group(0)  # 전체 클래스 문자열
        class_dict[class_name] = full_class_def

    return class_dict


def extract_accessors(dsl_text: str):
    block_patterns = {
        "Tags": re.compile(r"Tags:\n((?:\s+#[^\n]*\n)+)"),
        # "Enums": re.compile(r"Enums:\n((?:\s+\w+: \[[^\]]+\]\n*)+)"),
        "Attributes": re.compile(r"Attributes:\n((?:\s+\w+_\w+: [^\n]+\n*)+)"),
        "Methods": re.compile(r"Methods:\n((?:\s+\w+\([^\)]*\) -> \w+[^\n]*\n*)+)")
    }

    # Apply all patterns to the sample DSL text
    blocks = {
        name: (pattern.search(dsl_text).group(1).strip()).split("\n    ")
        for name, pattern in block_patterns.items()
        if pattern.search(dsl_text)
    }

    if blocks.get("Attributes"):
        blocks["Attributes"] = [line.split(":")[0].strip() for line in blocks.get("Attributes", [])]
    if blocks.get("Methods"):
        blocks["Methods"] = [line.split("(")[0].strip() for line in blocks.get("Methods", [])]
    return blocks

def validate_accessors(code: str, tag_list, method_list, attribute_list, model) -> str:

    # 문자열 리터럴을 임시로 보호하기 위한 함수들
    def protect_strings(code):
        """문자열 리터럴을 플레이스홀더로 치환"""
        strings = []
        
        # 삼중 따옴표 문자열 (먼저 처리)
        def replace_triple_quotes(match):
            strings.append(match.group(0))
            return f"__STRING_PLACEHOLDER_{len(strings)-1}__"
        
        # 단일/이중 따옴표 문자열
        def replace_quotes(match):
            strings.append(match.group(0))
            return f"__STRING_PLACEHOLDER_{len(strings)-1}__"
        
        # 삼중 따옴표 문자열 처리 (""" 또는 ''')
        code = re.sub(r'""".*?"""', replace_triple_quotes, code, flags=re.DOTALL)
        code = re.sub(r"'''.*?'''", replace_triple_quotes, code, flags=re.DOTALL)
        
        # 일반 문자열 처리 (이스케이프 문자 고려)
        code = re.sub(r'"(?:[^"\\]|\\.)*"', replace_quotes, code)
        code = re.sub(r"'(?:[^'\\]|\\.)*'", replace_quotes, code)
        
        return code, strings
    
    def restore_strings(code, strings):
        """플레이스홀더를 원래 문자열로 복원"""
        for i, string in enumerate(strings):
            code = code.replace(f"__STRING_PLACEHOLDER_{i}__", string)
        return code

    # 문자열 보호
    protected_code, string_literals = protect_strings(code)

    tag_embeddings = model.encode(tag_list, convert_to_tensor=True)
    method_embeddings = model.encode(method_list, convert_to_tensor=True)
    attribute_embeddings = model.encode(attribute_list, convert_to_tensor=True)

    tag_pattern = r"(#[a-zA-Z0-9_]+)\b"
    method_pattern = r"\.([a-zA-Z_][a-zA-Z0-9_]*)\("
    attribute_pattern = r"\.([a-zA-Z_][a-zA-Z0-9_]*)\b(?!\s*\()"

    def validate_tag(match):
        tag = match.group(1)
        if tag in tag_list:
            return tag
        query = model.encode(tag, convert_to_tensor=True)
        scores = util.cos_sim(query, tag_embeddings)[0]
        best_score = scores.max().item()
        if best_score < THRESHOLD:
            return tag
        best_match = tag_list[scores.argmax().item()]
        return best_match
    
    def validate_method(match):
        method = match.group(1)
        if method in method_list:
            return f".{method}("
        query = model.encode(method, convert_to_tensor=True)
        scores = util.cos_sim(query, method_embeddings)[0]
        best_score = scores.max().item()
        if best_score < THRESHOLD:
            return f".{method}("
        best_match = method_list[scores.argmax().item()]
        return f".{best_match}("

    def validate_attribute(match):
        attr = match.group(1)
        if attr in attribute_list:
            return f".{attr}"
        query = model.encode(attr, convert_to_tensor=True)
        scores = util.cos_sim(query, attribute_embeddings)[0]
        best_score = scores.max().item()
        if best_score < THRESHOLD:
            return f".{attr}"
        best_match = attribute_list[scores.argmax().item()]
        return f".{best_match}"
        
    # code = re.sub(tag_pattern, validate_tag, code)
    # code = re.sub(method_pattern, validate_method, code)
    # code = re.sub(attribute_pattern, validate_attribute, code)
    # 보호된 코드에서 패턴 매칭 수행
    protected_code = re.sub(tag_pattern, validate_tag, protected_code)
    protected_code = re.sub(method_pattern, validate_method, protected_code)
    protected_code = re.sub(attribute_pattern, validate_attribute, protected_code)
    
    # 문자열 복원
    code = restore_strings(protected_code, string_literals)
    return code

def validate_tag_group(code: str, devices: list = []) -> bool:
    tag_list_pattern = r"\((#[^)]+)\)"
    devices = [set(d) for d in devices]
    tag_group = [set(r.strip().split()) for r in re.findall(tag_list_pattern, code)]

    # 각 그룹이 최소 하나의 device 집합에 포함되는지 확인
    for group in tag_group:
        if not any(group.issubset(device) for device in devices):
            return False  # 하나라도 안 맞으면 실패

    return True  # 모두 만족

def translate_string_literals(code: str) -> str:
    pattern = r'(["\'])(.*?)(\1)'

    # 대체 함수 정의
    def replacer(match):
        quote = match.group(1)
        content = match.group(2)
        try:
            translated = deepl_translate(content, source="EN", target="KO")
        except Exception:
            translated = content
        print(content, translated, sep=" -> ")
        return f"{quote}{translated}{quote}"

    return re.sub(pattern, replacer, code)

def validate(code:str, classes: dict, selected_devices: list, devices_available: list, model) -> str:
    classes = {device:extract_accessors(classes[device]) for device in selected_devices}

    tags = set()
    attributes = set()
    methods = set()

    for device_info in classes.values():
        tags.update(device_info.get("Tags", []))
        attributes.update(device_info.get("Attributes", []))
        methods.update(device_info.get("Methods", []))
  
    code = validate_accessors(code, list(tags), list(methods), list(attributes), model)
    devices_available = [[f"#{t}" for t in tags]for tags in devices_available]

    if not validate_tag_group(code, devices_available):
        return ""

    code = translate_string_literals(code)
    
    return code


# 코드 교정만 수행
def validate_tmp(code:str, classes: dict, selected_devices: list, model) -> str:
    classes = {device:extract_accessors(classes[device]) for device in selected_devices}

    tags = set()
    attributes = set()
    methods = set()

    for device_info in classes.values():
        tags.update(device_info.get("Tags", []))
        attributes.update(device_info.get("Attributes", []))
        methods.update(device_info.get("Methods", []))
    
    
    code = validate_accessors(code, list(tags), list(methods), list(attributes), model)
    return code

if __name__ == "__main__":

    model = SentenceTransformer('paraphrase-MiniLM-L6-v2')

    with open("./resources/service_list_ver1.1.8.txt", "r") as f:
        service_doc = f.read()
    device_classes = extract_classes_by_name(service_doc)

    with open("./resources/things.json", "r", encoding="utf-8") as f:
        cd = json.load(f)

    code = "(#Bulb #livingRoom).turn_on('Hi')"

    unique_tag_sets = {frozenset(cd[k]['tags']) for k in cd}
    tag_sets = [list(tag_set) for tag_set in unique_tag_sets]

    tag_device = {}

    for tag_set in tag_sets:
        device_tags = [tag for tag in tag_set if tag in device_classes]
        other_tags = [tag for tag in tag_set if tag not in device_classes]

        for device_tag in device_tags:
            if device_tag not in tag_device:
                tag_device[device_tag] = []
            tag_device[device_tag].extend(other_tags)
    print(tag_sets, tag_device, sep="\n")

    # 디바이스 클래스에 태그 주석 추가
    for device_tag, extra_tags in tag_device.items():
        doc = device_classes[device_tag]
        lines = doc.splitlines()

        new_lines = lines[:4] + [f"    #{tag}" for tag in sorted(set(extra_tags))] + lines[4:]
        device_classes[device_tag] = "\n".join(new_lines)

    print(validate(code, device_classes, list(tag_device.keys()), tag_sets, model))
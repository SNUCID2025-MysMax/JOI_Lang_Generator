import os
import numpy as np
import re, json, pickle
from sklearn.metrics.pairwise import cosine_similarity
from FlagEmbedding import BGEM3FlagModel
from functools import lru_cache

def split_camel_case(identifier):
    """
    문장에서 디바이스를 찾기 위해 카멜 케이스를 단어별로 분리합니다.
    """
    matches = re.finditer('.+?(?:(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|$)', identifier)
    result = [m.group(0) for m in matches]
    if not result or (len(result) == 1 and result[0] == identifier):
        return [identifier]
    return result

# 디바이스가 쿼리에 포함되어 있는지 확인
def device_in_query(device_name, query, debug=False):
    """
    디바이스 이름이 쿼리에 포함되어 있는지 확인합니다. 
    (단어 경계 기반, 복수형 포함)
    """
    # 카멜 케이스 분리하고 공백으로 연결, 소문자 변환
    parts = split_camel_case(device_name)
    device_str = ' '.join(parts).lower()
    query_lower = query.lower()
    
    if debug:
        print(f"검사 중: '{device_name}' -> parts: {parts} -> device_str: '{device_str}'")

    # 단어 경계를 사용한 정확한 매칭
    patterns = [
        # 단수형 정확한 매칭
        f'\\b{re.escape(device_str)}\\b',
        # 복수형 s
        f'\\b{re.escape(device_str)}s\\b',
        # 복수형 es
        f'\\b{re.escape(device_str)}es\\b'
    ]
    
    # 패턴 중 하나라도 매칭되면 True
    for i, pattern in enumerate(patterns):
        if re.search(pattern, query_lower):
            if debug:
                pattern_type = ["단수형", "복수형(s)", "복수형(es)"][i]
                print(f"  -> ✓ {pattern_type} 매칭: '{pattern}'")
            return True
    
    if debug:
        print(f"  -> ✗ 매칭 없음")
    return False

# 캐싱을 이용한 성능 향상
@lru_cache(maxsize=1000)
def cached_device_check(device_name, query):
    return device_in_query(device_name, query)

# 우선순위 적용 함수
def prioritize_devices_in_results(results, query, max_k=7):
    """
    쿼리에 직접적으로 언급된 디바이스를 우선순위로 배치하고,
    나머지는 점수순 정렬 후 max_k개를 반환합니다.
    """
    prioritized = []
    others = []

    # 우선순위 디바이스와 일반 디바이스 분리
    for r in results:
        if cached_device_check(r['key'], query):
        # if device_in_query(r['key'], query):
            prioritized.append(r)
        else:
            others.append(r)

    # 우선순위 디바이스들을 점수 순으로 정렬 (높은 점수부터)
    prioritized.sort(key=lambda x: x['combined_score'], reverse=True)
    
    # 나머지 디바이스들도 점수 순으로 정렬 (높은 점수부터)
    others.sort(key=lambda x: x['combined_score'], reverse=True)
    
    # max_k가 기본값이면, 쿼리 길이에 따라 max_k 조정
    if max_k == 7:
        word_count = len(query.split())
        mention_count = len(prioritized)
        max_k += mention_count
        if word_count > 50:
            max_k = min(15, max_k + 3)
    
    # 우선순위 디바이스를 앞에, 나머지를 뒤에 배치하고 max_k개만 반환
    final_results = prioritized + others
    return final_results[:max_k]

# ColBERT 유사도 계산 함수
def colbert_maxsim_score(query_vecs, doc_vecs):
    sim_matrix = cosine_similarity(query_vecs, doc_vecs)  # (q_len, d_len)
    max_sims = np.max(sim_matrix, axis=1)  # 각 쿼리 토큰의 최대 유사도
    return np.mean(max_sims)  # 평균

# 하이브리드 추천 함수 (우선순위 적용)
def hybrid_recommend(model, query, embedding_data, devices_available=None, max_k=7, weights = (0.35, 0.4, 0.25)):

    dense_embeddings = embedding_data['dense']
    colbert_embeddings = embedding_data['colbert']
    sparse_embeddings = embedding_data['sparse']
    metadata = embedding_data['metadata']

    query_emb = model.encode(
        [query], 
        return_dense=True,
        return_sparse=True,
        return_colbert_vecs=True
    )
    
    dense_scores = cosine_similarity([query_emb['dense_vecs'][0]], dense_embeddings)[0]

    sparse_scores = []
    query_weights = query_emb['lexical_weights'][0]
    for doc_weights in sparse_embeddings:
        score = sum(query_weights.get(token, 0) * doc_weights.get(token, 0) for token in query_weights)
        sparse_scores.append(score)
    
    colbert_scores = [
        colbert_maxsim_score(query_emb['colbert_vecs'][0], doc_emb)
        for doc_emb in colbert_embeddings
    ]
    

    # 점수 정규화
    dense_norm = dense_scores / np.max(dense_scores)
    sparse_norm = np.array(sparse_scores) / (np.max(sparse_scores) + 1e-6)
    colbert_norm = np.array(colbert_scores) / (np.max(colbert_scores) + 1e-6)

    combined_scores = (
        weights[0] * dense_norm +
        weights[1] * sparse_norm +
        weights[2] * colbert_norm
    )

    sorted_indices = np.argsort(combined_scores)[::-1]

    if devices_available is not None:
        available_set = set(d.lower() for d in devices_available)
        sorted_indices = [i for i in sorted_indices if metadata['keys'][i].lower() in available_set]

    top_indices = sorted_indices

    # 기본 결과 생성
    results = [{
        'key': metadata['keys'][i],
        'text': metadata['texts'][i],
        'dense_score': float(dense_scores[i]),
        'sparse_score': float(sparse_scores[i]),
        'colbert_score': float(colbert_scores[i]),
        'combined_score': float(combined_scores[i])
    } for i in top_indices]
    
    # 우선순위 적용 및 max_k개 반환
    prioritized_results = prioritize_devices_in_results(results, query, max_k)
    
    return prioritized_results

# 사용 예시
if __name__ == "__main__":
    model = BGEM3FlagModel('BAAI/bge-m3', use_fp16=True)
    
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    # 데이터 로드
    dense_embeddings = np.load(os.path.join(BASE_DIR, '../resources', 'embedding_result', 'dense_embeddings.npy'))

    with open(os.path.join(BASE_DIR, '../resources', 'embedding_result', 'colbert_embeddings.pkl'), 'rb') as f:
        colbert_embeddings = pickle.load(f)

    with open(os.path.join(BASE_DIR, '../resources', 'embedding_result', 'sparse_embeddings.json')) as f:
        sparse_embeddings = json.load(f)

    with open(os.path.join(BASE_DIR, '../resources', 'embedding_result', 'metadata.json')) as f:
        metadata = json.load(f)
    
    embedding_data = {
        'dense': dense_embeddings,
        'colbert': colbert_embeddings,
        'sparse': sparse_embeddings,
        'metadata': metadata
    }
    
    # 테스트 쿼리
    query = "If the air conditioner is off, the temperature is above 29 degrees, and the humidity is above 70%, set the dehumidifier to dehumidify mode and turn it on. If the curtains are open and the lights are off, close the curtains and turn on the lights."
    print(len(query.split()))
    # results = hybrid_recommend(model, query, embedding_data)
    
    print(f"Query: {query}")
    # print("Results with priority:")
    # for i, result in enumerate(results):
    #     device_mentioned = device_in_query(result['key'], query, debug=True)
    #     priority_mark = "★" if device_mentioned else " "
    #     print(f"{priority_mark} {i+1}. {result['key']} (Score: {result['combined_score']:.4f})")
    #     print()  # 디버깅 출력과 구분하기 위한 빈 줄
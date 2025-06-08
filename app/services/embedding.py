import os
import numpy as np
import json
import pickle
from sklearn.metrics.pairwise import cosine_similarity
from FlagEmbedding import BGEM3FlagModel

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 데이터 로드
dense_embeddings = np.load(os.path.join(BASE_DIR, 'embedding_result', 'dense_embeddings.npy'))

with open(os.path.join(BASE_DIR, 'embedding_result', 'colbert_embeddings.pkl'), 'rb') as f:
    colbert_embeddings = pickle.load(f)

with open(os.path.join(BASE_DIR, 'embedding_result', 'sparse_embeddings.json')) as f:
    sparse_embeddings = json.load(f)

with open(os.path.join(BASE_DIR, 'embedding_result', 'metadata.json')) as f:
    metadata = json.load(f)

# ColBERT 유사도 계산 함수
def colbert_softmax_maxsim(query_vec, doc_vecs, temperature=0.05):
    sim_matrix = cosine_similarity(query_vec, doc_vecs)
    max_sim = np.max(sim_matrix, axis=1)
    weights = np.exp(max_sim / temperature)
    weights /= np.sum(weights)
    return np.sum(weights * max_sim)

# 하이브리드 추천 함수
def hybrid_recommend(model, query, devices_available=None, top_k=10, max_k=15, weights=(0.6, 0.3, 0.1)):
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
        colbert_softmax_maxsim(query_emb['colbert_vecs'][0], doc_emb)
        for doc_emb in colbert_embeddings
    ]
    
    max_score = max(dense_scores.max(), 1e-6)
    combined_scores = (
        weights[0] * dense_scores/max_score +
        weights[1] * np.array(sparse_scores) +
        weights[2] * np.array(colbert_scores)
    )

    sorted_indices = np.argsort(combined_scores)[::-1]

    if devices_available is not None:
        available_set = set(d.lower() for d in devices_available)
        sorted_indices = [i for i in sorted_indices if metadata['keys'][i].lower() in available_set]

    gap_threshold = 0.01
    initial_top = 5
    top_indices = []
    for i in range(len(sorted_indices)):
        if len(top_indices) >= max_k:
            break
        if i == 0:
            top_indices.append(sorted_indices[i])
            continue
        prev = combined_scores[top_indices[-1]]
        curr = combined_scores[sorted_indices[i]]
        if curr >= 0.5 or abs(prev - curr) <= gap_threshold or len(top_indices) < initial_top:
            top_indices.append(sorted_indices[i])
        else:
            break

    return [{
        'key': metadata['keys'][i],
        'text': metadata['texts'][i],
        'dense_score': float(dense_scores[i]),
        'sparse_score': float(sparse_scores[i]),
        'colbert_score': float(colbert_scores[i]),
        'combined_score': float(combined_scores[i])
    } for i in top_indices]

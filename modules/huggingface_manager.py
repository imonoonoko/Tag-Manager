"""
Hugging Face Transformers連携モジュール
事前学習済みモデルを活用した高度な自然言語処理機能を提供
"""

import json
import os
import logging
import numpy as np
import threading
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import pickle
from pathlib import Path

# Hugging Face関連のインポート（オプション）
try:
    # PyTorchの環境変数を設定してmeta tensorエラーを回避
    import os
    os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'
    os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:128'
    os.environ['TOKENIZERS_PARALLELISM'] = 'false'
    
    # 依存関係の詳細チェック
    import numpy as np
    import torch
    from transformers import AutoTokenizer, AutoModel, pipeline
    from sentence_transformers import SentenceTransformer
    HF_AVAILABLE = True
    print("Hugging Face依存関係の読み込みに成功しました")
except ImportError as e:
    HF_AVAILABLE = False
    logging.warning(f"Hugging Face Transformersがインストールされていません。高度なNLP機能は無効です。エラー: {e}")
    print(f"Hugging Face依存関係の読み込みに失敗: {e}")

from modules.config import BACKUP_DIR

# 設定
HF_MODELS_DIR = os.path.join(BACKUP_DIR, "hf_models")
EMBEDDINGS_CACHE_FILE = os.path.join(BACKUP_DIR, "tag_embeddings.pkl")
SIMILARITY_CACHE_FILE = os.path.join(BACKUP_DIR, "tag_similarity.pkl")

# 推奨モデル
RECOMMENDED_MODELS = {
    "multilingual": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "english": "sentence-transformers/all-MiniLM-L6-v2",
    "japanese": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "large": "sentence-transformers/all-mpnet-base-v2"
}

@dataclass
class TagEmbedding:
    """タグの埋め込みベクトル情報"""
    tag: str
    embedding: np.ndarray
    model_name: str
    created_at: str

@dataclass
class SimilarityResult:
    """類似度計算結果"""
    tag1: str
    tag2: str
    similarity: float
    model_name: str
    method: str

class HuggingFaceManager:
    """Hugging Face Transformers連携管理クラス"""
    
    def __init__(self, model_name: str = "multilingual", use_gpu: bool = False):
        self.logger = logging.getLogger(__name__)
        
        # HF_AVAILABLEの状態を確認
        if not HF_AVAILABLE:
            self.logger.warning("Hugging Face Transformersが利用できません")
            self.model_name = None
            self.use_gpu = False
            self.device = "cpu"
            self.model = None
            self.tokenizer = None
            self.embedding_model = None
            self.tag_embeddings = {}
            self.similarity_cache = {}
            self._loading = False
            self._loaded = False
            self._load_error = Exception("Hugging Face Transformersが利用できません")
            self._load_thread = None
            return
        
        try:
            self.model_name = RECOMMENDED_MODELS.get(model_name, RECOMMENDED_MODELS["multilingual"])
            self.use_gpu = use_gpu and torch.cuda.is_available()
            self.device = "cuda" if self.use_gpu else "cpu"
            
            self.model = None
            self.tokenizer = None
            self.embedding_model = None
            
            self.tag_embeddings = {}
            self.similarity_cache = {}
            
            # 非同期読み込み用のフラグ
            self._loading = False
            self._loaded = False
            self._load_error = None
            self._load_thread = None
            
            self._load_caches()
            
            # AI設定を確認して軽量埋め込み生成モードをチェック
            ai_settings = self._load_ai_settings()
            if ai_settings.get('use_lightweight_embeddings', True):
                print("軽量埋め込み生成モードを有効化")
                self._use_lightweight_embeddings = True
                self._loaded = True  # 軽量モードでは即座に利用可能
                self.logger.info("軽量埋め込み生成モードで初期化完了")
                return
            
            # モデル読み込みを非同期で開始
            self._start_async_load()
            
        except Exception as e:
            self.logger.error(f"HuggingFace Manager初期化エラー: {e}")
            self._load_error = e
            print(f"HuggingFace Manager初期化エラー: {e}")
    
    def _start_async_load(self):
        """モデル読み込みを非同期で開始"""
        if self._loading or self._loaded:
            return
        
        self._loading = True
        self._load_error = None
        
        def load_worker():
            try:
                self._load_model()
                self._loaded = True
                self.logger.info("モデル読み込み完了（非同期）")
            except Exception as e:
                self._load_error = e
                self.logger.error(f"モデル読み込みエラー（非同期）: {e}")
            finally:
                self._loading = False
        
        self._load_thread = threading.Thread(target=load_worker, daemon=True)
        self._load_thread.start()
    
    def is_ready(self) -> bool:
        """モデルが読み込み完了しているかどうかを確認"""
        # 軽量埋め込み生成モードの場合は常に利用可能
        if hasattr(self, '_use_lightweight_embeddings') and self._use_lightweight_embeddings:
            return True
        return self._loaded and self.embedding_model is not None
    
    def is_loading(self) -> bool:
        """モデルが読み込み中かどうかを確認"""
        return self._loading
    
    def get_load_error(self) -> Optional[Exception]:
        """読み込みエラーを取得"""
        return self._load_error
    
    def wait_for_load(self, timeout: float = 30.0) -> bool:
        """モデル読み込み完了を待機"""
        if self._load_thread and self._load_thread.is_alive():
            self._load_thread.join(timeout=timeout)
        return self.is_ready()
    
    def _load_model(self):
        """モデルを読み込み"""
        try:
            self.logger.info(f"Hugging Faceモデルを読み込み中: {self.model_name}")
            
            # AI設定を読み込み
            ai_settings = self._load_ai_settings()
            
            # CPU強制設定の確認
            force_cpu = ai_settings.get('force_cpu', True)
            skip_device_assignment = ai_settings.get('skip_model_device_assignment', True)
            use_cpu_only_init = ai_settings.get('use_cpu_only_initialization', True)
            
            if force_cpu or use_cpu_only_init:
                self.device = "cpu"
                self.use_gpu = False
                print(f"CPU強制設定により、デバイスをCPUに設定: {self.device}")
            
            # 代替実装: 軽量な埋め込み生成
            if ai_settings.get('use_lightweight_embeddings', True):
                print("軽量埋め込み生成モードを有効化")
                self._use_lightweight_embeddings = True
                self.embedding_model = None  # SentenceTransformerは使用しない
                self.logger.info("軽量埋め込み生成モードで初期化完了")
                return
            
            # SentenceTransformerモデルの読み込み（複数の方法を試行）
            embedding_model = None
            
            # 方法1: 通常の読み込み
            try:
                if skip_device_assignment:
                    self.embedding_model = SentenceTransformer(self.model_name)
                    print("SentenceTransformerをデバイス指定なしで読み込み完了")
                else:
                    self.embedding_model = SentenceTransformer(self.model_name, device=self.device)
                    print(f"SentenceTransformerをデバイス {self.device} で読み込み完了")
            except Exception as e1:
                print(f"SentenceTransformer読み込みエラー (方法1): {e1}")
                
                # 方法2: メタテンソルエラーの回避
                try:
                    if "meta tensor" in str(e1).lower():
                        print("メタテンソルエラーを検出。CPU専用初期化を試行...")
                        self.embedding_model = SentenceTransformer(self.model_name)
                        print("SentenceTransformerをCPU専用で読み込み完了")
                    else:
                        raise e1
                except Exception as e2:
                    print(f"SentenceTransformer読み込みエラー (方法2): {e2}")
                    
                    # 方法3: 最後の手段 - デバイス指定を完全に削除
                    try:
                        print("最終手段: デバイス指定を完全に削除して読み込み...")
                        self.embedding_model = SentenceTransformer(self.model_name)
                        print("SentenceTransformerを最終手段で読み込み完了")
                    except Exception as e3:
                        print(f"SentenceTransformer読み込みエラー (方法3): {e3}")
                        print("軽量埋め込み生成モードにフォールバック")
                        self._use_lightweight_embeddings = True
                        self.embedding_model = None
                        self.logger.info("軽量埋め込み生成モードでフォールバック完了")
                        return
            
            # トークナイザーとモデルも別途読み込み（必要に応じて）
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                self.model = AutoModel.from_pretrained(self.model_name)
                
                # モデルのデバイス移動（CPU強制設定が無効な場合のみ）
                if not force_cpu and self.use_gpu:
                    try:
                        self.model = self.model.to(self.device)
                    except Exception as e:
                        if "meta tensor" in str(e).lower():
                            print("メタテンソルエラーを検出。to_empty()を使用...")
                            self.model = self.model.to_empty(device=self.device)
                        else:
                            raise e
                else:
                    print("CPU強制設定により、モデルのデバイス移動をスキップ")
                    
            except Exception as e:
                print(f"トークナイザー/モデル読み込みエラー: {e}")
                # 埋め込みモデルが成功していれば、トークナイザー/モデルは必須ではない
                pass
            
            self.logger.info(f"モデル読み込み完了: {self.model_name}")
            
        except Exception as e:
            self.logger.error(f"モデル読み込みエラー: {e}")
            self.embedding_model = None
            raise e
    
    def _load_ai_settings(self) -> dict:
        """AI設定ファイルを読み込み"""
        try:
            import json
            import os
            settings_file = os.path.join('resources', 'config', 'ai_settings.json')
            if os.path.exists(settings_file):
                with open(settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"AI設定ファイル読み込みエラー: {e}")
        return {}
    
    def _load_caches(self):
        """キャッシュファイルを読み込み"""
        try:
            if os.path.exists(EMBEDDINGS_CACHE_FILE):
                with open(EMBEDDINGS_CACHE_FILE, 'rb') as f:
                    self.tag_embeddings = pickle.load(f)
                self.logger.info(f"埋め込みキャッシュを読み込み: {len(self.tag_embeddings)}タグ")
            
            if os.path.exists(SIMILARITY_CACHE_FILE):
                with open(SIMILARITY_CACHE_FILE, 'rb') as f:
                    self.similarity_cache = pickle.load(f)
                self.logger.info(f"類似度キャッシュを読み込み: {len(self.similarity_cache)}ペア")
                
        except Exception as e:
            self.logger.error(f"キャッシュ読み込みエラー: {e}")
    
    def _save_caches(self):
        """キャッシュファイルを保存"""
        try:
            os.makedirs(os.path.dirname(EMBEDDINGS_CACHE_FILE), exist_ok=True)
            
            with open(EMBEDDINGS_CACHE_FILE, 'wb') as f:
                pickle.dump(self.tag_embeddings, f)
            
            with open(SIMILARITY_CACHE_FILE, 'wb') as f:
                pickle.dump(self.similarity_cache, f)
                
            self.logger.info("キャッシュを保存しました")
            
        except Exception as e:
            self.logger.error(f"キャッシュ保存エラー: {e}")
    
    def get_tag_embedding(self, tag: str, force_recompute: bool = False) -> Optional[np.ndarray]:
        """タグの埋め込みベクトルを取得"""
        if not HF_AVAILABLE:
            return None
        
        # モデルが読み込み中またはエラーの場合
        if self._loading:
            self.logger.info("モデル読み込み中です。しばらくお待ちください。")
            return None
        
        if self._load_error:
            self.logger.error(f"モデル読み込みエラー: {self._load_error}")
            return None
        
        # 軽量埋め込み生成モードの確認
        if hasattr(self, '_use_lightweight_embeddings') and self._use_lightweight_embeddings:
            return self._get_lightweight_embedding(tag, force_recompute)
        
        if not self.embedding_model:
            # モデルがまだ読み込まれていない場合、読み込み完了を待機
            if not self.wait_for_load(timeout=5.0):
                self.logger.warning("モデル読み込みがタイムアウトしました")
                return None
        
        tag_key = tag.lower().strip()
        
        # キャッシュから取得
        if not force_recompute and tag_key in self.tag_embeddings:
            return self.tag_embeddings[tag_key].embedding
        
        try:
            # 新しい埋め込みを生成
            embedding = self.embedding_model.encode([tag], convert_to_numpy=True)[0]
            
            # キャッシュに保存
            self.tag_embeddings[tag_key] = TagEmbedding(
                tag=tag_key,
                embedding=embedding,
                model_name=self.model_name,
                created_at=str(np.datetime64('now'))
            )
            
            return embedding
            
        except Exception as e:
            self.logger.error(f"埋め込み生成エラー ({tag}): {e}")
            return None
    
    def _get_lightweight_embedding(self, tag: str, force_recompute: bool = False) -> Optional[np.ndarray]:
        """軽量埋め込み生成（SentenceTransformerを使用しない）"""
        tag_key = tag.lower().strip()
        
        # キャッシュチェック
        if not force_recompute and tag_key in self.tag_embeddings:
            return self.tag_embeddings[tag_key].embedding
        
        try:
            # 簡単なハッシュベースの埋め込み生成
            import hashlib
            
            # ハッシュを生成
            hash_obj = hashlib.md5(tag_key.encode('utf-8'))
            hash_bytes = hash_obj.digest()
            
            # 128次元のベクトルに変換
            embedding = np.zeros(128, dtype=np.float32)
            for i, byte in enumerate(hash_bytes):
                if i < 128:
                    embedding[i] = float(byte - 128) / 128.0  # -1.0 から 1.0 の範囲に正規化
            
            # 残りの次元をランダムで埋める
            if len(hash_bytes) < 128:
                # ハッシュを整数に変換してシードとして使用
                seed_value = int(hash_obj.hexdigest()[:8], 16)
                np.random.seed(seed_value)
                embedding[len(hash_bytes):] = np.random.normal(0, 0.1, 128 - len(hash_bytes))
            
            # 正規化
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm
            
            # キャッシュに保存
            self.tag_embeddings[tag_key] = TagEmbedding(
                tag=tag_key,
                embedding=embedding,
                model_name="lightweight_hash",
                created_at=str(np.datetime64('now'))
            )
            
            return embedding
            
        except Exception as e:
            self.logger.error(f"軽量埋め込み生成エラー: {e}")
            return None
    
    def calculate_similarity(self, tag1: str, tag2: str, method: str = "cosine") -> float:
        """2つのタグの類似度を計算"""
        if not HF_AVAILABLE:
            return 0.0
        
        # モデルが読み込み中またはエラーの場合
        if self._loading:
            self.logger.info("モデル読み込み中です。しばらくお待ちください。")
            return 0.0
        
        if self._load_error:
            self.logger.error(f"モデル読み込みエラー: {self._load_error}")
            return 0.0
        
        if not self.embedding_model:
            # モデルがまだ読み込まれていない場合、読み込み完了を待機
            if not self.wait_for_load(timeout=5.0):
                self.logger.warning("モデル読み込みがタイムアウトしました")
                return 0.0
        
        # キャッシュキー
        cache_key = f"{tag1.lower()}_{tag2.lower()}_{method}"
        if cache_key in self.similarity_cache:
            return self.similarity_cache[cache_key].similarity
        
        # 埋め込みを取得
        emb1 = self.get_tag_embedding(tag1)
        emb2 = self.get_tag_embedding(tag2)
        
        if emb1 is None or emb2 is None:
            return 0.0
        
        # 類似度計算
        if method == "cosine":
            similarity = self._cosine_similarity(emb1, emb2)
        elif method == "euclidean":
            similarity = self._euclidean_similarity(emb1, emb2)
        elif method == "dot":
            similarity = self._dot_product_similarity(emb1, emb2)
        else:
            similarity = self._cosine_similarity(emb1, emb2)
        
        # キャッシュに保存
        self.similarity_cache[cache_key] = SimilarityResult(
            tag1=tag1.lower(),
            tag2=tag2.lower(),
            similarity=similarity,
            model_name=self.model_name,
            method=method
        )
        
        return similarity
    
    def _cosine_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """コサイン類似度"""
        dot_product = np.dot(emb1, emb2)
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        return dot_product / (norm1 * norm2) if norm1 > 0 and norm2 > 0 else 0.0
    
    def _euclidean_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """ユークリッド距離ベースの類似度（距離を類似度に変換）"""
        distance = np.linalg.norm(emb1 - emb2)
        # 距離を類似度に変換（距離が小さいほど類似度が高い）
        return 1.0 / (1.0 + distance)
    
    def _dot_product_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """内積類似度"""
        return np.dot(emb1, emb2)
    
    def find_similar_tags(self, tag: str, candidate_tags: List[str], 
                         threshold: float = 0.5, limit: int = 10) -> List[Tuple[str, float]]:
        """類似タグを検索"""
        if not HF_AVAILABLE:
            return []
        
        # モデルが読み込み中またはエラーの場合
        if self._loading:
            self.logger.info("モデル読み込み中です。しばらくお待ちください。")
            return []
        
        if self._load_error:
            self.logger.error(f"モデル読み込みエラー: {self._load_error}")
            return []
        
        if not self.embedding_model:
            # モデルがまだ読み込まれていない場合、読み込み完了を待機
            if not self.wait_for_load(timeout=5.0):
                self.logger.warning("モデル読み込みがタイムアウトしました")
                return []
        
        similarities = []
        for candidate in candidate_tags:
            if candidate.lower() != tag.lower():
                similarity = self.calculate_similarity(tag, candidate)
                if similarity >= threshold:
                    similarities.append((candidate, similarity))
        
        # 類似度でソート
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:limit]
    
    def get_semantic_categories(self, tags: List[str], num_categories: int = 5) -> Dict[str, List[str]]:
        """意味的類似性に基づいてタグをカテゴリに分類"""
        if not HF_AVAILABLE:
            return {"未分類": tags}
        
        # モデルが読み込み中またはエラーの場合
        if self._loading:
            self.logger.info("モデル読み込み中です。しばらくお待ちください。")
            return {"未分類": tags}
        
        if self._load_error:
            self.logger.error(f"モデル読み込みエラー: {self._load_error}")
            return {"未分類": tags}
        
        if not self.embedding_model:
            # モデルがまだ読み込まれていない場合、読み込み完了を待機
            if not self.wait_for_load(timeout=5.0):
                self.logger.warning("モデル読み込みがタイムアウトしました")
                return {"未分類": tags}
        
        if len(tags) <= num_categories:
            return {f"カテゴリ{i+1}": [tag] for i, tag in enumerate(tags)}
        
        # 埋め込みを取得
        embeddings = []
        valid_tags = []
        for tag in tags:
            emb = self.get_tag_embedding(tag)
            if emb is not None:
                embeddings.append(emb)
                valid_tags.append(tag)
        
        if len(embeddings) < 2:
            return {"未分類": tags}
        
        # クラスタリング（簡易版：類似度ベース）
        categories = {}
        used_tags = set()
        
        for i, tag in enumerate(valid_tags):
            if tag in used_tags:
                continue
            
            # 新しいカテゴリを作成
            category_name = f"カテゴリ{len(categories)+1}"
            category_tags = [tag]
            used_tags.add(tag)
            
            # 類似タグを探す
            for j, other_tag in enumerate(valid_tags):
                if other_tag in used_tags:
                    continue
                
                similarity = self.calculate_similarity(tag, other_tag)
                if similarity > 0.7:  # 高類似度閾値
                    category_tags.append(other_tag)
                    used_tags.add(other_tag)
            
            categories[category_name] = category_tags
        
        # 未分類タグを追加
        uncategorized = [tag for tag in tags if tag not in used_tags]
        if uncategorized:
            categories["未分類"] = uncategorized
        
        return categories
    
    def analyze_tag_semantics(self, tag: str) -> Dict[str, Any]:
        """タグの意味的解析"""
        if not HF_AVAILABLE:
            return {"error": "Hugging Face Transformersがインストールされていません"}
        
        # モデルが読み込み中またはエラーの場合
        if self._loading:
            return {"error": "モデル読み込み中です。しばらくお待ちください。"}
        
        if self._load_error:
            return {"error": f"モデル読み込みエラー: {self._load_error}"}
        
        if not self.embedding_model:
            # モデルがまだ読み込まれていない場合、読み込み完了を待機
            if not self.wait_for_load(timeout=5.0):
                return {"error": "モデル読み込みがタイムアウトしました"}
        
        embedding = self.get_tag_embedding(tag)
        if embedding is None:
            return {"error": "埋め込み生成に失敗しました"}
        
        # 基本的な統計情報
        analysis = {
            "tag": tag,
            "embedding_dimension": len(embedding),
            "embedding_norm": float(np.linalg.norm(embedding)),
            "model_name": self.model_name,
            "semantic_features": {}
        }
        
        # 埋め込みベクトルの特徴を分析
        analysis["semantic_features"] = {
            "mean": float(np.mean(embedding)),
            "std": float(np.std(embedding)),
            "min": float(np.min(embedding)),
            "max": float(np.max(embedding)),
            "sparsity": float(np.sum(embedding == 0) / len(embedding))
        }
        
        return analysis
    
    def batch_process_tags(self, tags: List[str], batch_size: int = 32) -> Dict[str, np.ndarray]:
        """タグのバッチ処理"""
        if not HF_AVAILABLE:
            return {}
        
        # モデルが読み込み中またはエラーの場合
        if self._loading:
            self.logger.info("モデル読み込み中です。しばらくお待ちください。")
            return {}
        
        if self._load_error:
            self.logger.error(f"モデル読み込みエラー: {self._load_error}")
            return {}
        
        if not self.embedding_model:
            # モデルがまだ読み込まれていない場合、読み込み完了を待機
            if not self.wait_for_load(timeout=5.0):
                self.logger.warning("モデル読み込みがタイムアウトしました")
                return {}
        
        embeddings = {}
        
        for i in range(0, len(tags), batch_size):
            batch_tags = tags[i:i+batch_size]
            
            try:
                batch_embeddings = self.embedding_model.encode(batch_tags, convert_to_numpy=True)
                
                for tag, embedding in zip(batch_tags, batch_embeddings):
                    embeddings[tag] = embedding
                    
                    # キャッシュに保存
                    self.tag_embeddings[tag.lower()] = TagEmbedding(
                        tag=tag.lower(),
                        embedding=embedding,
                        model_name=self.model_name,
                        created_at=str(np.datetime64('now'))
                    )
                
                self.logger.info(f"バッチ処理完了: {i+len(batch_tags)}/{len(tags)}")
                
            except Exception as e:
                self.logger.error(f"バッチ処理エラー: {e}")
        
        return embeddings
    
    def export_embeddings(self, output_file: str = None) -> str:
        """埋め込みデータをエクスポート"""
        if output_file is None:
            output_file = os.path.join(BACKUP_DIR, "tag_embeddings_export.json")
        
        export_data = {}
        for tag, embedding_info in self.tag_embeddings.items():
            export_data[tag] = {
                "embedding": embedding_info.embedding.tolist(),
                "model_name": embedding_info.model_name,
                "created_at": embedding_info.created_at
            }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"埋め込みデータをエクスポート: {output_file}")
        return output_file
    
    def get_model_info(self) -> Dict[str, Any]:
        """モデル情報を取得"""
        if not HF_AVAILABLE:
            return {"available": False, "error": "Hugging Face Transformersがインストールされていません"}
        
        info = {
            "available": True,
            "model_name": self.model_name,
            "device": self.device,
            "use_gpu": self.use_gpu,
            "cached_embeddings": len(self.tag_embeddings),
            "cached_similarities": len(self.similarity_cache)
        }
        
        if self.embedding_model:
            info["model_loaded"] = True
            info["embedding_dimension"] = self.embedding_model.get_sentence_embedding_dimension()
        else:
            info["model_loaded"] = False
        
        return info
    
    def cleanup(self):
        """リソースのクリーンアップ"""
        self._save_caches()
        
        if hasattr(self, 'model') and self.model:
            del self.model
        if hasattr(self, 'tokenizer') and self.tokenizer:
            del self.tokenizer
        if hasattr(self, 'embedding_model') and self.embedding_model:
            del self.embedding_model

# グローバルインスタンス
hf_manager = HuggingFaceManager() 
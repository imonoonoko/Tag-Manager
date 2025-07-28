"""
ローカルHugging Faceモデル管理モジュール（商用利用対応）
商用利用可能なモデルをローカルで処理し、高速なオフラインAI機能を提供
"""

import json
import os
import logging
import numpy as np
import hashlib
import time
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
import pickle
from pathlib import Path
from datetime import datetime, timedelta
import threading
from concurrent.futures import ThreadPoolExecutor

# Hugging Face関連のインポート（オプション）
try:
    # PyTorchの環境変数を設定してmeta tensorエラーを回避
    import os
    os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'
    os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:128'
    os.environ['TOKENIZERS_PARALLELISM'] = 'false'
    os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'  # テレメトリを無効化
    
    # 依存関係の詳細チェック
    import numpy as np
    import torch
    from transformers import AutoTokenizer, AutoModel, pipeline
    from sentence_transformers import SentenceTransformer
    HF_AVAILABLE = True
    
    print("Local Hugging Face依存関係の読み込みに成功しました")
    
except ImportError as e:
    HF_AVAILABLE = False
    logging.warning(f"Hugging Face Transformersがインストールされていません。ローカルAI機能は無効です。エラー: {e}")
    print(f"Local Hugging Face依存関係の読み込みに失敗: {e}")

from .config import BACKUP_DIR

# 商用利用可能なモデル設定
COMMERCIAL_MODELS = {
    "multilingual": {
        "name": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        "license": "Apache-2.0",
        "commercial_use": True,
        "description": "多言語対応の軽量モデル（商用利用可能）",
        "size_mb": 471,
        "languages": ["en", "ja", "zh", "ko", "de", "fr", "es"]
    },
    "english": {
        "name": "sentence-transformers/all-MiniLM-L6-v2",
        "license": "Apache-2.0",
        "commercial_use": True,
        "description": "英語特化の軽量モデル（商用利用可能）",
        "size_mb": 91,
        "languages": ["en"]
    },
    "japanese": {
        "name": "pkshatech/GLuCoSE-base-ja",
        "license": "Apache-2.0",
        "commercial_use": True,
        "description": "日本語特化モデル（商用利用可能）",
        "size_mb": 420,
        "languages": ["ja"]
    },
    "large": {
        "name": "sentence-transformers/all-mpnet-base-v2",
        "license": "Apache-2.0",
        "commercial_use": True,
        "description": "高精度な大規模モデル（商用利用可能）",
        "size_mb": 420,
        "languages": ["en"]
    }
}

# キャッシュ設定
CACHE_DIR = os.path.join(BACKUP_DIR, "local_hf_cache")
MODEL_CACHE_DIR = os.path.join(CACHE_DIR, "models")
EMBEDDING_CACHE_FILE = os.path.join(CACHE_DIR, "embeddings_cache.json")
SIMILARITY_CACHE_FILE = os.path.join(CACHE_DIR, "similarity_cache.json")
MODEL_METADATA_FILE = os.path.join(CACHE_DIR, "model_metadata.json")

# キャッシュ有効期限（秒）
EMBEDDING_CACHE_TTL = 86400 * 30  # 30日
SIMILARITY_CACHE_TTL = 86400 * 7   # 7日
MODEL_CACHE_TTL = 86400 * 90       # 90日

@dataclass
class ModelMetadata:
    """モデルメタデータ"""
    name: str
    license: str
    commercial_use: bool
    description: str
    size_mb: int
    languages: List[str]
    downloaded_at: str
    last_used: str
    cache_size: int = 0

@dataclass
class CachedEmbedding:
    """キャッシュされた埋め込み"""
    tag: str
    embedding: List[float]
    model_name: str
    created_at: str
    expires_at: str

@dataclass
class CachedSimilarity:
    """キャッシュされた類似度"""
    tag1: str
    tag2: str
    similarity: float
    model_name: str
    method: str
    created_at: str
    expires_at: str

class LocalHuggingFaceManager:
    """ローカルHugging Faceモデル管理クラス（商用利用対応）"""
    
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
            self.embedding_cache = {}
            self.similarity_cache = {}
            self.model_metadata = {}
            self.cache_lock = threading.Lock()
            self._loading = False
            self._loaded = False
            self._load_error = Exception("Hugging Face Transformersが利用できません")
            self._load_thread = None
            return
        
        try:
            self.model_name = model_name
            self.use_gpu = use_gpu and torch.cuda.is_available()
            self.device = "cuda" if self.use_gpu else "cpu"
            
            self.model = None
            self.tokenizer = None
            self.embedding_model = None
            
            # キャッシュ管理
            self.embedding_cache = {}
            self.similarity_cache = {}
            self.model_metadata = {}
            
            # スレッドセーフなロック
            self.cache_lock = threading.Lock()
            
            # 非同期読み込み用のフラグ
            self._loading = False
            self._loaded = False
            self._load_error = None
            self._load_thread = None
            
            self._ensure_cache_directories()
            self._load_caches()
            
            # AI設定を確認して軽量埋め込み生成モードをチェック
            ai_settings = self._load_ai_settings()
            if ai_settings.get('use_lightweight_embeddings', True):
                print("Local HF: 軽量埋め込み生成モードを有効化")
                self._use_lightweight_embeddings = True
                self._loaded = True  # 軽量モードでは即座に利用可能
                self.logger.info("Local HF: 軽量埋め込み生成モードで初期化完了")
                return
            
            # モデル読み込みを非同期で開始
            self._start_async_load()
            
        except Exception as e:
            self.logger.error(f"Local HuggingFace Manager初期化エラー: {e}")
            self._load_error = e
            print(f"Local HuggingFace Manager初期化エラー: {e}")
    
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
    
    def wait_for_load(self, timeout: float = 120.0) -> bool:
        """
        モデル読み込み完了を待機（タイムアウト時間を延長）
        デフォルト: 120秒（2分）
        """
        if self._load_thread and self._load_thread.is_alive():
            self.logger.info(f"モデル読み込み完了を待機中... (タイムアウト: {timeout}秒)")
            self._load_thread.join(timeout=timeout)
            
            if self._load_thread.is_alive():
                self.logger.warning(f"モデル読み込みがタイムアウトしました ({timeout}秒)")
                return False
            else:
                self.logger.info("モデル読み込み完了を確認しました")
                return self.is_ready()
        return self.is_ready()
    
    def _ensure_cache_directories(self):
        """キャッシュディレクトリを作成"""
        os.makedirs(CACHE_DIR, exist_ok=True)
        os.makedirs(MODEL_CACHE_DIR, exist_ok=True)
    
    def _load_caches(self):
        """キャッシュファイルを読み込み"""
        try:
            # 埋め込みキャッシュ
            if os.path.exists(EMBEDDING_CACHE_FILE):
                with open(EMBEDDING_CACHE_FILE, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    current_time = time.time()
                    
                    for tag, data in cache_data.items():
                        if current_time < data.get('expires_at', 0):
                            self.embedding_cache[tag] = CachedEmbedding(
                                tag=data['tag'],
                                embedding=data['embedding'],
                                model_name=data['model_name'],
                                created_at=data['created_at'],
                                expires_at=data['expires_at']
                            )
                    
                    self.logger.info(f"埋め込みキャッシュを読み込み: {len(self.embedding_cache)}タグ")
            
            # 類似度キャッシュ
            if os.path.exists(SIMILARITY_CACHE_FILE):
                with open(SIMILARITY_CACHE_FILE, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    current_time = time.time()
                    
                    for key, data in cache_data.items():
                        if current_time < data.get('expires_at', 0):
                            self.similarity_cache[key] = CachedSimilarity(
                                tag1=data['tag1'],
                                tag2=data['tag2'],
                                similarity=data['similarity'],
                                model_name=data['model_name'],
                                method=data['method'],
                                created_at=data['created_at'],
                                expires_at=data['expires_at']
                            )
                    
                    self.logger.info(f"類似度キャッシュを読み込み: {len(self.similarity_cache)}ペア")
            
            # モデルメタデータ
            if os.path.exists(MODEL_METADATA_FILE):
                with open(MODEL_METADATA_FILE, 'r', encoding='utf-8') as f:
                    self.model_metadata = json.load(f)
                    
        except Exception as e:
            self.logger.error(f"キャッシュ読み込みエラー: {e}")
    
    def _save_caches(self):
        """キャッシュファイルを保存"""
        try:
            with self.cache_lock:
                # 埋め込みキャッシュ
                cache_data = {}
                for tag, cached in self.embedding_cache.items():
                    cache_data[tag] = {
                        'tag': cached.tag,
                        'embedding': cached.embedding,
                        'model_name': cached.model_name,
                        'created_at': cached.created_at,
                        'expires_at': cached.expires_at
                    }
                
                with open(EMBEDDING_CACHE_FILE, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f, ensure_ascii=False, indent=2)
                
                # 類似度キャッシュ
                cache_data = {}
                for key, cached in self.similarity_cache.items():
                    cache_data[key] = {
                        'tag1': cached.tag1,
                        'tag2': cached.tag2,
                        'similarity': cached.similarity,
                        'model_name': cached.model_name,
                        'method': cached.method,
                        'created_at': cached.created_at,
                        'expires_at': cached.expires_at
                    }
                
                with open(SIMILARITY_CACHE_FILE, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f, ensure_ascii=False, indent=2)
                
                # モデルメタデータ
                with open(MODEL_METADATA_FILE, 'w', encoding='utf-8') as f:
                    json.dump(self.model_metadata, f, ensure_ascii=False, indent=2)
                
                self.logger.info("キャッシュを保存しました")
                
        except Exception as e:
            self.logger.error(f"キャッシュ保存エラー: {e}")
    
    def _load_model(self):
        """商用利用可能なモデルを読み込み（リトライ機能付き）"""
        max_retries = 3
        retry_count = 0
        
        # AI設定を読み込み
        ai_settings = self._load_ai_settings()
        force_cpu = ai_settings.get('force_cpu', True)
        skip_device_assignment = ai_settings.get('skip_model_device_assignment', True)
        use_cpu_only_init = ai_settings.get('use_cpu_only_initialization', True)
        
        # CPU強制設定の確認
        if force_cpu or use_cpu_only_init:
            self.device = "cpu"
            self.use_gpu = False
            print(f"Local HF: CPU強制設定により、デバイスをCPUに設定: {self.device}")
        
        while retry_count < max_retries:
            try:
                if self.model_name not in COMMERCIAL_MODELS:
                    self.logger.error(f"不明なモデル: {self.model_name}")
                    return
                
                model_info = COMMERCIAL_MODELS[self.model_name]
                self.logger.info(f"商用利用可能なモデルを読み込み中: {model_info['name']} (試行 {retry_count + 1}/{max_retries})")
                self.logger.info(f"ライセンス: {model_info['license']}")
                self.logger.info(f"商用利用: {model_info['commercial_use']}")
                self.logger.info(f"モデルサイズ: {model_info['size_mb']}MB")
                
                # モデルをローカルにダウンロード（初回のみ）
                model_path = os.path.join(MODEL_CACHE_DIR, self.model_name)
                if not os.path.exists(model_path):
                    self.logger.info(f"モデルをダウンロード中: {model_info['name']}")
                    os.makedirs(model_path, exist_ok=True)
                else:
                    self.logger.info(f"キャッシュされたモデルを使用: {model_path}")
                
                # SentenceTransformerモデルの読み込み（複数の方法を試行）
                self.logger.info("SentenceTransformerモデルを初期化中...")
                
                # 方法1: 通常の読み込み
                try:
                    if skip_device_assignment:
                        self.embedding_model = SentenceTransformer(
                            model_info['name'], 
                            cache_folder=model_path
                        )
                        print("Local HF: SentenceTransformerをデバイス指定なしで読み込み完了")
                    else:
                        self.embedding_model = SentenceTransformer(
                            model_info['name'], 
                            device=self.device,
                            cache_folder=model_path
                        )
                        print(f"Local HF: SentenceTransformerをデバイス {self.device} で読み込み完了")
                except Exception as e1:
                    print(f"Local HF: SentenceTransformer読み込みエラー (方法1): {e1}")
                    
                    # 方法2: メタテンソルエラーの回避
                    try:
                        if "meta tensor" in str(e1).lower():
                            print("Local HF: メタテンソルエラーを検出。CPU専用初期化を試行...")
                            self.embedding_model = SentenceTransformer(
                                model_info['name'], 
                                cache_folder=model_path
                            )
                            print("Local HF: SentenceTransformerをCPU専用で読み込み完了")
                        else:
                            raise e1
                    except Exception as e2:
                        print(f"Local HF: SentenceTransformer読み込みエラー (方法2): {e2}")
                        
                        # 方法3: 最後の手段 - デバイス指定を完全に削除
                        try:
                            print("Local HF: 最終手段: デバイス指定を完全に削除して読み込み...")
                            self.embedding_model = SentenceTransformer(
                                model_info['name'], 
                                cache_folder=model_path
                            )
                            print("Local HF: SentenceTransformerを最終手段で読み込み完了")
                        except Exception as e3:
                            print(f"Local HF: SentenceTransformer読み込みエラー (方法3): {e3}")
                            raise e3
                
                # モデルの動作確認
                self.logger.info("モデルの動作確認中...")
                test_embedding = self.embedding_model.encode(["test"], convert_to_numpy=True)
                if test_embedding is not None and len(test_embedding) > 0:
                    self.logger.info("モデルの動作確認が完了しました")
                else:
                    raise Exception("モデルの動作確認に失敗しました")
                
                # メタデータを更新
                self.model_metadata[self.model_name] = {
                    'name': model_info['name'],
                    'license': model_info['license'],
                    'commercial_use': model_info['commercial_use'],
                    'description': model_info['description'],
                    'size_mb': model_info['size_mb'],
                    'languages': model_info['languages'],
                    'downloaded_at': datetime.now().isoformat(),
                    'last_used': datetime.now().isoformat(),
                    'cache_size': len(self.embedding_cache)
                }
                
                self.logger.info(f"モデル読み込み完了: {model_info['name']}")
                return  # 成功したらループを抜ける
                
            except Exception as e:
                retry_count += 1
                self.logger.error(f"モデル読み込みエラー (試行 {retry_count}/{max_retries}): {e}")
                
                if retry_count < max_retries:
                    wait_time = retry_count * 5  # 5秒、10秒、15秒と待機時間を増加
                    self.logger.info(f"{wait_time}秒後にリトライします...")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"モデル読み込みが{max_retries}回失敗しました。最後のエラー: {e}")
                    self._load_error = e
                    self.embedding_model = None
    
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
    
    def get_tag_embedding(self, tag: str, force_recompute: bool = False) -> Optional[np.ndarray]:
        """タグの埋め込みベクトルを取得（キャッシュ対応）"""
        if not HF_AVAILABLE:
            return None
        
        # 軽量埋め込み生成モードの確認
        if hasattr(self, '_use_lightweight_embeddings') and self._use_lightweight_embeddings:
            return self._get_lightweight_embedding(tag, force_recompute)
        
        # モデルが読み込み中またはエラーの場合
        if self._loading:
            self.logger.info("モデル読み込み中です。しばらくお待ちください。")
            return None
        
        if self._load_error:
            self.logger.error(f"モデル読み込みエラー: {self._load_error}")
            return None
        
        if not self.embedding_model:
            # モデルがまだ読み込まれていない場合、読み込み完了を待機
            self.logger.info("モデルがまだ読み込まれていません。読み込み完了を待機中...")
            if not self.wait_for_load(timeout=60.0):  # タイムアウトを60秒に延長
                self.logger.warning("モデル読み込みがタイムアウトしました（60秒）")
                return None
        
        tag_key = tag.lower().strip()
        
        # キャッシュから取得
        if not force_recompute and tag_key in self.embedding_cache:
            cached = self.embedding_cache[tag_key]
            if time.time() < float(cached.expires_at):
                # メタデータを更新
                if self.model_name in self.model_metadata:
                    self.model_metadata[self.model_name]['last_used'] = datetime.now().isoformat()
                return np.array(cached.embedding)
            else:
                # 期限切れのキャッシュを削除
                del self.embedding_cache[tag_key]
        
        try:
            # 新しい埋め込みを生成
            self.logger.debug(f"埋め込みベクトルを生成中: {tag}")
            embedding = self.embedding_model.encode([tag], convert_to_numpy=True)[0]
            
            # キャッシュに保存
            expires_at = time.time() + EMBEDDING_CACHE_TTL
            self.embedding_cache[tag_key] = CachedEmbedding(
                tag=tag_key,
                embedding=embedding.tolist(),
                model_name=self.model_name,
                created_at=datetime.now().isoformat(),
                expires_at=str(expires_at)
            )
            
            # メタデータを更新
            if self.model_name in self.model_metadata:
                self.model_metadata[self.model_name]['last_used'] = datetime.now().isoformat()
                self.model_metadata[self.model_name]['cache_size'] = len(self.embedding_cache)
            
            self.logger.debug(f"埋め込みベクトル生成完了: {tag}")
            return embedding
            
        except Exception as e:
            self.logger.error(f"埋め込み生成エラー ({tag}): {e}")
            return None
    
    def _get_lightweight_embedding(self, tag: str, force_recompute: bool = False) -> Optional[np.ndarray]:
        """軽量埋め込み生成（SentenceTransformerを使用しない）"""
        tag_key = tag.lower().strip()
        
        # キャッシュチェック
        if not force_recompute and tag_key in self.embedding_cache:
            cached = self.embedding_cache[tag_key]
            if time.time() < float(cached.expires_at):
                return np.array(cached.embedding)
            else:
                # 期限切れのキャッシュを削除
                del self.embedding_cache[tag_key]
        
        try:
            # 簡単なハッシュベースの埋め込み生成
            import hashlib
            
            # ハッシュを生成
            hash_obj = hashlib.md5(tag_key.encode('utf-8'))
            hash_bytes = hash_obj.digest()
            
            # 384次元のベクトルに変換（SentenceTransformerと同様）
            embedding = np.zeros(384, dtype=np.float32)
            for i, byte in enumerate(hash_bytes):
                if i < 384:
                    embedding[i] = float(byte - 128) / 128.0  # -1.0 から 1.0 の範囲に正規化
            
            # 残りの次元をランダムで埋める
            if len(hash_bytes) < 384:
                # ハッシュを整数に変換してシードとして使用
                seed_value = int(hash_obj.hexdigest()[:8], 16)
                np.random.seed(seed_value)
                embedding[len(hash_bytes):] = np.random.normal(0, 0.1, 384 - len(hash_bytes))
            
            # 正規化
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm
            
            # キャッシュに保存
            expires_at = time.time() + EMBEDDING_CACHE_TTL
            self.embedding_cache[tag_key] = CachedEmbedding(
                tag=tag_key,
                embedding=embedding.tolist(),
                model_name="lightweight_hash",
                created_at=datetime.now().isoformat(),
                expires_at=str(expires_at)
            )
            
            return embedding
            
        except Exception as e:
            self.logger.error(f"軽量埋め込み生成エラー: {e}")
            return None
    
    def calculate_similarity(self, tag1: str, tag2: str, method: str = "cosine") -> float:
        """2つのタグの類似度を計算（キャッシュ対応）"""
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
            cached = self.similarity_cache[cache_key]
            if time.time() < float(cached.expires_at):
                return cached.similarity
            else:
                # 期限切れのキャッシュを削除
                del self.similarity_cache[cache_key]
        
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
        expires_at = time.time() + SIMILARITY_CACHE_TTL
        self.similarity_cache[cache_key] = CachedSimilarity(
            tag1=tag1.lower(),
            tag2=tag2.lower(),
            similarity=similarity,
            model_name=self.model_name,
            method=method,
            created_at=datetime.now().isoformat(),
            expires_at=str(expires_at)
        )
        
        return similarity
    
    def _cosine_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """コサイン類似度"""
        dot_product = np.dot(emb1, emb2)
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        return dot_product / (norm1 * norm2) if norm1 > 0 and norm2 > 0 else 0.0
    
    def _euclidean_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """ユークリッド距離ベースの類似度"""
        distance = np.linalg.norm(emb1 - emb2)
        return 1.0 / (1.0 + distance)
    
    def _dot_product_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """内積類似度"""
        return np.dot(emb1, emb2)
    
    def get_commercial_models_info(self) -> Dict[str, Any]:
        """商用利用可能なモデル情報を取得"""
        return {
            'available_models': COMMERCIAL_MODELS,
            'current_model': self.model_name,
            'model_metadata': self.model_metadata,
            'cache_stats': {
                'embedding_cache_size': len(self.embedding_cache),
                'similarity_cache_size': len(self.similarity_cache),
                'total_cache_size_mb': self._calculate_cache_size()
            }
        }
    
    def _calculate_cache_size(self) -> float:
        """キャッシュサイズを計算（MB）"""
        total_size = 0
        
        # 埋め込みキャッシュサイズ
        for cached in self.embedding_cache.values():
            total_size += len(cached.embedding) * 8  # float64 = 8 bytes
        
        # 類似度キャッシュサイズ
        total_size += len(self.similarity_cache) * 100  # 概算
        
        return total_size / (1024 * 1024)  # MBに変換
    
    def cleanup_expired_cache(self):
        """期限切れのキャッシュを削除"""
        current_time = time.time()
        
        # 埋め込みキャッシュ
        expired_keys = []
        for tag, cached in self.embedding_cache.items():
            if current_time >= float(cached.expires_at):
                expired_keys.append(tag)
        
        for key in expired_keys:
            del self.embedding_cache[key]
        
        # 類似度キャッシュ
        expired_keys = []
        for key, cached in self.similarity_cache.items():
            if current_time >= float(cached.expires_at):
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.similarity_cache[key]
        
        if expired_keys:
            self.logger.info(f"期限切れキャッシュを削除: {len(expired_keys)}件")
            self._save_caches()
    
    def get_model_info(self) -> Dict[str, Any]:
        """モデル情報を取得"""
        if not HF_AVAILABLE:
            return {"available": False, "error": "Hugging Face Transformersがインストールされていません"}
        
        info = {
            "available": True,
            "model_name": self.model_name,
            "device": self.device,
            "use_gpu": self.use_gpu,
            "commercial_use": True,
            "cached_embeddings": len(self.embedding_cache),
            "cached_similarities": len(self.similarity_cache),
            "model_info": COMMERCIAL_MODELS.get(self.model_name, {})
        }
        
        if self.embedding_model:
            info["model_loaded"] = True
            info["embedding_dimension"] = self.embedding_model.get_sentence_embedding_dimension()
        else:
            info["model_loaded"] = False
        
        return info
    
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
local_hf_manager = LocalHuggingFaceManager() 
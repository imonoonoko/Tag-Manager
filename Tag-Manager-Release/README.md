# タグ管理ツール (Tag Manager)

## 🚀 概要

AI画像生成用のプロンプトタグを効率的に管理するためのGUIアプリケーションです。タグの分類、翻訳、重み付け、エクスポート機能を提供し、高品質なプロンプト作成をサポートします。

## ✨ 主な機能

### 🔍 タグ管理
- **タグの追加・編集・削除**: 英語タグと日本語訳の管理
- **カテゴリ分類**: 自動カテゴリ割り当てと手動分類
- **お気に入り機能**: よく使うタグをお気に入り登録
- **最近使ったタグ**: 使用履歴の自動記録

### 🎨 プロンプト作成支援
- **重み付け機能**: タグの重要度を数値で調整
- **自動並び替え**: カテゴリ優先度に基づく自動ソート
- **一括操作**: 複数タグの同時編集・削除
- **エクスポート機能**: プロンプト形式での出力

### 🤖 AI機能
- **自動カテゴリ割り当て**: キーワードベースの自動分類
- **コンテキスト認識**: タグの組み合わせを考慮した分類
- **AI予測**: 機械学習によるカテゴリ予測
- **類似タグ提案**: 既存タグとの類似性分析
- **ローカルAI**: Hugging Faceモデルによるオフライン処理

### 🎛️ カスタマイズ機能
- **カスタムキーワード**: ユーザー定義の分類キーワード
- **カスタムルール**: 独自の分類ルール設定
- **テーマ切替**: ダーク/ライトテーマ対応
- **設定の保存**: ユーザー設定の永続化

## 🏗️ アーキテクチャ

```
Tag-Manager-Nightly/
├── modules/                      # メインモジュール
│   ├── ui_main.py               # メインUI
│   ├── tag_manager.py           # タグ管理
│   ├── theme_manager.py         # テーマ管理
│   ├── dialogs.py               # ダイアログ
│   ├── constants.py             # 定数定義
│   ├── config.py                # 設定管理
│   ├── ai_predictor.py          # AI予測機能
│   ├── customization.py         # カスタマイズ機能
│   ├── huggingface_manager.py   # Hugging Face連携
│   ├── local_hf_manager.py      # ローカルAI管理
│   ├── context_analyzer.py      # コンテキスト分析
│   ├── category_manager.py      # カテゴリ管理
│   ├── common_words.py          # 共通語除外
│   ├── ui_dialogs.py            # UIダイアログ
│   ├── ui_export_import.py      # エクスポート・インポート
│   ├── ui_utils.py              # UIユーティリティ
│   └── spec_checker/            # 仕様チェッカー
├── data/                        # データファイル
│   └── tags.db                  # SQLiteデータベース
├── backup/                      # バックアップ
│   ├── YYYY-MM-DD/             # 日付別バックアップ
│   ├── test/                   # テスト用バックアップ
│   └── external_data/          # 外部データ
├── resources/                   # リソース
│   ├── config/                 # 設定ファイル
│   └── icons/                  # アイコンファイル
├── tests/                      # テスト
├── scripts/                    # 自動化スクリプト
├── logs/                       # ログファイル
└── docs/                       # ドキュメント
```

## 🚀 クイックスタート

### 1. インストール

```bash
# リポジトリをクローン
git clone https://github.com/imonoonoko/Tag-Manager.git
cd Tag-Manager-Nightly

# 依存関係をインストール
pip install -r requirements.txt
```

### 2. アプリケーション起動

```bash
# 直接実行
python main.py

# Windows用バッチファイル
run_app.bat
```

### 3. テスト実行

```bash
# 全テストを実行
pytest

# Windows用バッチファイル
run_tests.bat
```

## 📖 使用方法

### 基本的な操作

1. **タグの追加**
   - 「タグ追加」ボタンからカンマ区切りで英語タグを入力
   - 「ネガティブ追加」でネガティブプロンプト用タグを追加

2. **タグの編集**
   - タグ一覧から編集したいタグを選択
   - 右側の編集パネルで内容を修正し「保存」

3. **カテゴリ管理**
   - 左側リストでカテゴリを選択
   - 「カテゴリ一括変更」で複数タグを同時分類

4. **プロンプト作成**
   - タグをダブルクリックで出力欄に追加
   - 重み付けスライダーで重要度調整
   - 「コピー」でクリップボードに出力

### 高度な機能

1. **AI予測機能**
   - メニュー「ツール」→「AI予測機能」
   - 新しいタグのカテゴリ予測
   - 類似タグの提案

2. **カスタマイズ設定**
   - メニュー「ツール」→「カスタムキーワード設定」
   - メニュー「ツール」→「カスタムルール設定」
   - 独自の分類ルールを定義

3. **自動カテゴリ割り当て**
   - メニュー「ツール」→「未分類タグのカテゴリ自動割り当て」
   - 未分類タグの一括分類

## 🛠️ 開発環境

- **Python**: 3.10.6+
- **GUI**: ttkbootstrap 1.14.1+
- **データベース**: SQLite3
- **翻訳**: deep-translator 1.11.4+
- **AI/ML**: transformers 4.54.0+, torch 2.4.1+, scikit-learn 1.7.1+
- **テスト**: pytest 8.4.1+, mypy 1.17.0+

## 📋 開発ガイドライン

### コード品質

- **型ヒント**: 全関数・メソッドに型ヒントを付与
- **テスト**: 新機能追加時は必ずテストを作成
- **ドキュメント**: 重要な関数にはdocstringを記述
- **エラーハンドリング**: 適切な例外処理とログ出力

### 自動化機能

- **技術仕様書**: `技術仕様書_関数・ファイルパス一覧.md`
- **AI参照ガイド**: `AI_REFERENCE_GUIDE.md`
- **進捗管理**: `ToDoリスト.md`
- **自動チェック**: `check_spec.bat`

## 🛡️ 自動不具合防止・仕様整合性チェック

- コード変更時は `check_spec.bat` または `python scripts/check_spec_compliance.py` を必ず実行し、
  技術仕様書・実装・インポート等の整合性を自動チェックしてください。
- チェックロジックは `modules/spec_checker/` 配下の各モジュールに分割されており、
  関数・クラス・ファイルパス・インポートの仕様逸脱や不整合を自動検出します。
- 詳細は `AI_REFERENCE_GUIDE.md` も参照してください。

## 💾 バックアップファイルの命名規則・運用

- 本番用バックアップDBは `tags_backup_YYYYMMDD_HHMMSS.db` 形式で保存
- テスト用DBは `test_` プレフィックスまたは `tags_backup_coverage_` などで始まり、必ず `backup/test/` 配下に保存
- backup/cleanup_backup.py で30日以上前のバックアップや不要ファイルを自動削除

## 🤝 貢献

1. このリポジトリをフォーク
2. 機能ブランチを作成 (`git checkout -b feature/AmazingFeature`)
3. 変更をコミット (`git commit -m 'Add some AmazingFeature'`)
4. ブランチにプッシュ (`git push origin feature/AmazingFeature`)
5. プルリクエストを作成

## ⚠️ 重要: 利用制限

### 商用利用について
- **研究目的・個人利用**: 可能
- **商用利用**: 別途法的確認が必要

### 利用規約
- 本ソフトウェアは研究目的・個人利用を想定しています
- 商用利用を検討される場合は、専門の法律家に相談してください
- 外部APIの利用規約を遵守してください

詳細は `USAGE_TERMS.md` ファイルを参照してください。

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

### ライセンス概要
- **プロジェクト**: MIT License
- **主要ライブラリ**: ttkbootstrap (MIT), transformers (Apache-2.0), torch (BSD-3-Clause)
- **外部API**: Hugging Face (条件付き商用利用)

### 使用モデル（Hugging Face）
- **sentence-transformers/all-MiniLM-L6-v2**: Apache-2.0
- **sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2**: Apache-2.0
- **sentence-transformers/all-mpnet-base-v2**: Apache-2.0
- **sentence-transformers/paraphrase-multilingual-mpnet-base-v2**: Apache-2.0
- **pkshatech/GLuCoSE-base-ja**: Apache-2.0

### 商用利用に関する重要事項
⚠️ **商用利用を検討される場合は、以下の点にご注意ください：**

1. **Hugging Face**: 商用利用可能なライセンスのモデルを選択しています
2. **法的アドバイス**: 商用利用前は専門の法律家に相談することを強く推奨します

詳細は `LICENSE.md` と `THIRD_PARTY_LICENSES.txt` ファイルを参照してください。

## 🆘 サポート

問題や質問がある場合は、GitHubのIssuesページでお知らせください。

---

**Tag Manager** - AI画像生成のための効率的なタグ管理ツール

## 🗂️ ドキュメント・アーカイブ整理ルール

- `archive/` 配下は「廃止・参考」資料専用。現役で使う設計・仕様は必ずプロジェクトルートやdocs/に置く。
- 設計メモや運用ルールは「現役：プロジェクトルート」「参考：archive/」「廃止：archive/内で明示」
- READMEやAI_REFERENCE_GUIDE.mdから現役/参考/廃止の区分を明記し、リンクを整理

## 🛠️ スクリプト用途・運用区分

- `scripts/performance_monitor.py` … アプリケーションのパフォーマンス監視・分析用（現役・必要に応じて利用）
- その他のスクリプトも用途・現役/参考/廃止区分をファイル先頭コメントやREADMEで明示

## 🆕 カテゴリ自動拡充機能

- `scripts/auto_expand_categories.py` を実行することで、Stable Diffusionプロンプト等の外部データから頻出キーワードを自動抽出し、最適なカテゴリへ自動分類・追加できます。
- 既存カテゴリ構造は維持され、タグ自体は増やさずキーワードのみが追加されます。
- 外部データセットは `backup/external_datasets/` に保存され、差分バックアップも `backup/` に自動生成されます。
- 実行ログは `logs/auto_expand_categories.log` に記録されます。

### 使い方
1. `python scripts/auto_expand_categories.py` を実行
2. 外部データセットが自動ダウンロード・保存されます
3. 新規キーワードが最適なカテゴリに自動追加されます
4. 追加前後の `category_keywords.json` は `backup/` にバックアップされます

### 注意点
- カテゴリ構造は変更されません。
- 外部データセットは再利用可能な形で保存されます
- 既存キーワードと重複するものは追加されません

## 🔧 最新機能・改善点

### v1.0.0 (2025/01/27)
- **AI機能強化**: Hugging Face Transformers統合
- **ローカルAI**: オフライン処理対応
- **品質保証**: 包括的な自動チェックシステム
- **パフォーマンス**: モジュール分離による軽量化
- **商用利用**: ライセンス情報の明確化
- **個人データ保護**: Git除外設定の強化

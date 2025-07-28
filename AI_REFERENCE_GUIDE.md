# AI開発者向け参照ガイド

## 🚨 重要：コード変更前の必須チェック

**このファイルは、AIがコードを変更する前に必ず参照すべきガイドラインです。**

---

## 📋 変更前の必須確認事項

### 1. 技術仕様書の確認
- **必須ファイル**: `技術仕様書_関数・ファイルパス一覧.md` を必ず参照
- **確認内容**:
  - 変更対象の関数・クラスが仕様書に記載されているか
  - ファイルパスが正しいか
  - 依存関係が明確か

### 2. 変更影響範囲の確認
- 変更する関数が他のモジュールから呼び出されているか
- データベーススキーマに影響がないか
- UIコンポーネントの依存関係は大丈夫か

### 3. テストの確認
- 関連するテストファイルが存在するか
- 変更後にテストが通るか

---

## 🔧 変更時の手順

### Step 1: 技術仕様書の参照
```bash
# 必ず最初にこのファイルを確認
cat 技術仕様書_関数・ファイルパス一覧.md
```

### Step 2: 変更対象の特定
- 変更する関数・クラス名を仕様書で確認
- ファイルパスが正しいことを確認
- 依存関係を把握

### Step 3: 変更の実行
- 仕様書に記載されている構造に従って変更
- 既存の関数シグネチャを維持
- ファイルパスは絶対パスを使用

### Step 4: 変更後の確認
- 技術仕様書の更新が必要かチェック
- 関連するテストの実行
- 動作確認

---

## 📁 重要なファイル一覧

### 技術仕様書
- `技術仕様書_関数・ファイルパス一覧.md` - **最重要：必ず参照**

### 主要モジュール
- `modules/ui_main.py` - メインUI
- `modules/tag_manager.py` - データベース操作
- `modules/dialogs.py` - ダイアログ
- `modules/theme_manager.py` - テーマ管理
- `modules/constants.py` - 定数定義

### 設定・ドキュメント
- `ToDoリスト.md` - 進捗管理
- `requirements.txt` - 依存関係
- `mypy.ini` - 型チェック設定

---

## ⚠️ よくある間違いと注意点

### 1. ファイルパスの間違い
- ❌ 相対パスの使用（`'resources/tags.db'`）
- ✅ 絶対パスの使用（`os.path.join(os.path.dirname(__file__), '..', 'resources', 'tags.db')`）

### 2. 関数名の間違い
- ❌ 存在しない関数の呼び出し（`get_tag_info`）
- ✅ 仕様書に記載された関数の使用（`get_all_tags`）

### 3. クラス構造の変更
- ❌ 既存のクラス構造を無視した変更
- ✅ 仕様書に記載された構造の維持

### 4. 重複関数定義（重要）
- ❌ 同じ関数名で複数回定義（`def bulk_reassign_category` が2回出現）
- ✅ 関数は1つのファイル内で1回のみ定義
- ✅ 既存関数の修正時は、重複定義がないか必ず確認
- ✅ 新しい関数追加時は、同名関数が既に存在しないか確認

### 5. 変数スコープの間違い
- ❌ 関数内で未定義変数の使用（`for tag in tags:` で `tags` が未定義）
- ✅ 変数は使用前に必ず定義
- ✅ 関数内の変数は、その関数内で定義されているか確認

---

## 🛡️ 自動チェックルール（新規追加）

### 重複関数定義チェック
```bash
# 重複関数定義を検出するスクリプト
python scripts/check_duplicate_functions.py
```

### 未定義変数チェック
```bash
# 未定義変数の使用を検出
python -m py_compile modules/ui_main.py
mypy modules/ui_main.py --strict
```

### 関数定義前チェックリスト
- [ ] 同じファイル内に同名関数が存在しないか確認
- [ ] 関数内で使用する変数が全て定義されているか確認
- [ ] インポート文が正しく記述されているか確認
- [ ] 関数の引数と戻り値の型が明確か確認

---

## 📝 今回の修正内容（2024年12月）

### 問題
- `modules/ui_main.py` で `bulk_reassign_category` 関数が重複定義されていた
- 2つ目の関数定義で `tags` 変数が未定義だった
- エラー: `NameError: name 'tags' is not defined`

### 修正内容
1. 重複した `bulk_reassign_category` 関数（2206行目以降）を削除
2. 2095行目にある正しい関数定義のみを残す
3. 関数内の変数定義を確認し、`tags = [t["tag"] for t in self.tag_manager.get_tags_by_category(category)]` が正しく定義されていることを確認

### 今後の防止策
- 関数追加・修正時は必ず重複定義チェックを実行
- 変数使用前に定義確認を徹底
- 自動チェックスクリプトの活用

---

## 🔄 変更後の更新義務

### 技術仕様書の更新が必要な場合
- 新しい関数・クラスの追加
- ファイルパスの変更
- データベーススキーマの変更
- 重要な定数の変更

### ToDoリストの更新
- 完了したタスクのマーク
- 新しく発見された問題の追加
- 進捗状況の更新

---

## 📞 エラー時の対処法

### 1. 技術仕様書を再確認
- 関数名・ファイルパスが正しいか
- 依存関係が正しく記載されているか

### 2. 既存の実装を確認
- 同様の機能が既に実装されていないか
- 既存のパターンに従っているか

### 3. テストの実行
- 関連するテストが存在するか
- テストが通るか

---

## 🎯 最終確認チェックリスト

- [ ] 技術仕様書を参照した
- [ ] 変更対象の関数・クラスを特定した
- [ ] ファイルパスが正しいことを確認した
- [ ] 依存関係を把握した
- [ ] 既存の構造に従って変更した
- [ ] 変更後の動作確認をした
- [ ] 必要に応じて技術仕様書を更新した
- [ ] ToDoリストを更新した

---

**このガイドラインに従わない変更は、予期しないバグや不具合を引き起こす可能性があります。必ず参照してください。** 

---

## 🛡️ 自動不具合防止・仕様整合性チェックの運用

### spec_checkerモジュールについて

- `scripts/check_spec_compliance.py` は、AIによるコード変更時の不具合防止・仕様整合性チェックを自動化するためのスクリプトです。
- コアロジックは `modules/spec_checker/` 配下の各モジュールに分割されており、以下の観点で自動チェックを実施します：
  - 関数・クラス名の仕様書突合
  - ファイルパスの仕様書突合
  - インポート文の整合性
  - 差分レポート・仕様書自動更新案の生成

### 運用手順

1. 変更前・変更後に必ず `check_spec.bat` または `python scripts/check_spec_compliance.py` を実行し、
   技術仕様書・実装・インポート等の整合性を自動チェックしてください。
2. エラーや警告が出た場合は、内容を確認し、必要に応じて修正・仕様書更新を行ってください。
3. 各spec_checkerモジュールは `tests/utils/` 配下に単体テストが用意されており、pytestで品質担保が可能です。

### 参考: spec_checkerモジュール構成

- extractor.py … 関数・クラス抽出
- spec_parser.py … 仕様書パース
- comparator.py … 差分検出
- reporter.py … レポート生成
- updater.py … 仕様書自動更新案
- filepath_checker.py … ファイルパス整合性
- import_checker.py … インポート整合性

--- 

## 🆕 カテゴリ自動拡充機能の運用ガイド

### 概要
- `scripts/auto_expand_categories.py` を実行することで、Stable Diffusionプロンプトデータセット等の外部データから頻出キーワードを自動抽出し、最適なカテゴリへ自動分類・追加できます。
- 既存カテゴリ構造は維持され、タグ自体は増やさずキーワードのみが追加されます。
- 外部データセットは `backup/external_datasets/` 配下に保存され、差分バックアップも `backup/` 配下に自動生成されます。

### 手順
1. `python scripts/auto_expand_categories.py` を実行
2. 外部データセットが自動ダウンロード・保存されます
3. 新規キーワードが最適なカテゴリに自動追加されます
4. 追加前後の `category_keywords.json` は `backup/` にバックアップされます
5. 実行ログ・エラーは `logs/auto_expand_categories.log` に記録されます

### 注意事項
- カテゴリ構造は変更されません。新規カテゴリを追加したい場合は手動で編集してください
- 外部データセットは再利用可能な形で保存されます
- 既存キーワードと重複するものは追加されません
- スクリプト実行前に手動バックアップを推奨します

---

## 🚀 Cursorルール自動化強化ガイド

### 自動化チェックの必須実行

**コード変更前・変更後に必ず以下のチェックを実行してください：**

#### 1. 包括的品質チェック（最重要）
```bash
# 包括的コード品質チェック（改良版）
python scripts/check_code_quality.py modules --no-mypy --no-pytest

# 重複関数定義チェック
python scripts/check_duplicate_functions.py modules

# 仕様書整合性チェック
python scripts/check_spec_compliance.py
```

#### 2. 包括的チェック（一括実行）
```bash
# 全チェックを一括実行
.\check_spec.bat
```

#### 3. 個別チェック（必要に応じて）
```bash
# 型チェック
mypy modules/ --strict

# テスト実行
pytest tests/ -v

# 構文チェック
python -m py_compile modules/ui_main.py
```

### 自動化品質保証ルール

#### 必須チェック項目
1. **重複関数定義**: 同じファイル内で同名関数が複数定義されていないか
2. **未定義変数**: 関数内で使用する変数が全て定義されているか
3. **インポート整合性**: インポート文が正しく記述されているか
4. **ファイルパス整合性**: 絶対パスが正しく使用されているか
5. **仕様書整合性**: 実装と技術仕様書が一致しているか

#### 自動化チェックの優先順位
1. **高優先度**: 重複関数定義、未定義変数
2. **中優先度**: インポート整合性、ファイルパス整合性
3. **低優先度**: 型チェック、テスト実行

### エラー時の自動対処手順

#### 重複関数定義エラー
1. `python scripts/check_duplicate_functions.py modules` で詳細確認
2. 重複した関数定義の削除
3. 正しい関数定義のみを残す
4. 再度チェックを実行

#### 未定義変数エラー
1. 変数定義箇所の確認
2. スコープの確認
3. 適切な場所での変数定義
4. エラー処理の追加

#### インポートエラー
1. インポート文の確認
2. ファイルパスの確認
3. 依存関係の確認
4. 循環インポートの回避

### 自動化品質メトリクス

#### 目標値
- **重複関数定義**: 0件（必須）
- **未定義変数**: 0件（必須）
- **インポートエラー**: 0件（必須）
- **型チェックエラー**: 最小化
- **テスト成功率**: 90%以上
- **カバレッジ**: 70%以上

#### 継続的改善
- 月次品質レビュー
- 自動チェックツールの改善
- ドキュメントの更新
- ベストプラクティスの共有

### 自動化チェックの統合

#### CI/CDパイプライン統合
```yaml
# .github/workflows/quality-check.yml の例
name: Quality Check
on: [push, pull_request]
jobs:
  quality-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.8'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run quality checks
        run: |
          python scripts/check_duplicate_functions.py modules
          python scripts/check_code_quality.py modules --no-mypy --no-pytest
          python scripts/check_spec_compliance.py
          mypy modules/ --strict
          pytest tests/ -v
```

#### Git pre-commitフック統合
```bash
# .git/hooks/pre-commit の例
#!/bin/bash
echo "Running quality checks..."
python scripts/check_duplicate_functions.py modules
if [ $? -ne 0 ]; then
    echo "❌ Duplicate function definitions found"
    exit 1
fi

python scripts/check_code_quality.py modules --no-mypy --no-pytest
if [ $? -ne 0 ]; then
    echo "❌ Code quality issues found"
    exit 1
fi

echo "✅ All quality checks passed"
```

### 自動化チェックのカスタマイズ

#### プロジェクト固有の設定
- `scripts/check_code_quality.py` の除外変数リストをカスタマイズ
- `modules/spec_checker/` のチェックルールを調整
- `check_spec.bat` のチェック項目を追加・削除

#### 環境別の設定
- 開発環境: 全チェック実行
- テスト環境: 重要チェックのみ実行
- 本番環境: 必須チェックのみ実行

---

**この自動化ガイドラインに従うことで、コード品質の一貫性と信頼性を確保できます。** 
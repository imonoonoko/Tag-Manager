# タグ管理ツール

[![CI](https://github.com/（あなたのリポジトリURL）/actions/workflows/python-ci.yml/badge.svg?branch=main)](https://github.com/（あなたのリポジトリURL）/actions/workflows/python-ci.yml)

このツールは、プロンプト用のタグを管理するためのシンプルなGUIアプリケーションです。

## 🚨 AI開発者向け重要情報

**コード変更を行う前に、必ず以下のファイルを参照してください：**

- 📋 **[AI_REFERENCE_GUIDE.md](./AI_REFERENCE_GUIDE.md)** - AI開発者向け参照ガイド
- 📖 **[技術仕様書_関数・ファイルパス一覧.md](./技術仕様書_関数・ファイルパス一覧.md)** - 技術仕様書（最重要）
- 📝 **[ToDoリスト.md](./ToDoリスト.md)** - 進捗管理・タスク一覧

これらのファイルを参照せずにコードを変更すると、予期しないバグや不具合が発生する可能性があります。

## 🚀 使い方

1.  `run_app.bat` を実行します。
    初回起動時に必要なライブラリが自動でインストールされ、仮想環境がセットアップされます。

2.  アプリケーションが起動したら、タグの追加、編集、カテゴリ分け、お気に入り設定などが行えます。

### タグのエクスポート・インポート
- 「選択タグをエクスポート」ボタンで**JSONまたはCSVファイル**に保存可能
- 「インポート」ボタンで**JSON/CSVから一括追加**（CSVはtag,jp,category,favorite,is_negativeカラム）

### タグの一括編集
- 複数タグを選択→「一括編集」ボタン→カテゴリ・日本語訳をまとめて変更可能

### 検索・フィルタ機能
- 検索欄でタグ名・カテゴリ・日本語訳・お気に入り状態を横断的に絞り込み
- 一致部分はリスト上でハイライト表示
- 検索欄にプレースホルダー・クリアボタンあり

### UI/UX改善
- 主要なボタン・入力欄にツールチップ（マウスオーバー時の説明）を追加
- メニューバーに「フィードバック」ボタン（GitHub Issues等に誘導）
- 初回起動時に操作ガイドを自動表示

## 🛠️ 開発者向け

### 仮想環境のセットアップ

```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### コードフォーマッターとリンター

コードの品質を保つために、`Black` と `Ruff` を使用しています。

#### インストール

```bash
pip install black ruff
```

#### 使い方

-   **Black (フォーマッター)**: コードのスタイルを自動で整形します。

    ```bash
    black .
    ```

-   **Ruff (リンター)**: コードの潜在的なエラーやスタイル違反をチェックします。

    ```bash
    ruff check .
    ```

    問題を自動修正するには:

    ```bash
    ruff check . --fix
    ```

### ユニットテストの実行

`run_tests.bat` を使用してユニットテストを実行できます。

```bash
run_tests.bat
```

### 型チェック（mypy）

主要な関数・クラスには型アノテーションを付与しています。型安全性を保つため、`mypy`で型チェックを推奨します。

#### インストール

```bash
pip install mypy
```

#### 使い方

```bash
mypy modules/
```

※ 外部ライブラリ（ttkbootstrap, deep_translator等）の型情報不足による警告は無視して問題ありません。

### カバレッジ計測

テストカバレッジを確認するには、以下のコマンドを実行します。

```bash
pytest --cov=modules --cov-report=term --cov-report=html
```

- 詳細なカバレッジレポートは `htmlcov/index.html` で確認できます。

### CI/CD・自動テスト運用例（GitHub Actions）

`.github/workflows/python-app.yml` などで以下のような自動テストを設定できます。

```yaml
name: Python application
on: [push, pull_request]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install mypy black ruff pytest pytest-cov
    - name: Lint with ruff
      run: ruff check .
    - name: Check code format with black
      run: black --check .
    - name: Type check with mypy
      run: mypy modules/
    - name: Run tests with coverage
      run: pytest --cov=modules --cov-report=term
```

### 開発Tips
- テスト・カバレッジ・型チェックは定期的に実行し、品質を維持してください。
- GUIテストはTcl/Tk環境依存のため、Windows環境での動作確認を推奨します。
- 進捗前にはDBバックアップを推奨します。

## 📂 プロジェクト構造

```
Tag-Manager/
├───main.py
├───tags.db
├───プロンプトタグ管理ツール.ico
├───requirements.txt
├───README.md
├───run_app.bat
├───run_tests.bat
├───resources/
│   ├───categories.json
│   ├───negative_tags.json
│   ├───prompts.json
│   ├───tags.json
│   └───translated_tags.json
├───modules/
│   ├───__init__.py
│   ├───constants.py
│   ├───dialogs.py
│   ├───tag_manager.py
│   └───theme_manager.py
└───tests/
    └───test_tag_manager.py
```

## 🚦 CI/CD（自動テスト・型チェック・カバレッジ）

- GitHub Actionsにより、push/pull request時に以下が自動実行されます：
    - mypyによる型チェック
    - pytest + coverageによる自動テスト・カバレッジ計測
    - ログ・カバレッジレポートはアーティファクトとしてダウンロード可能
- ワークフロー定義: `.github/workflows/python-ci.yml`

## 📝 開発運用ルール

- **ブランチ運用**
    - `main`/`master`は常に安定版。新機能・修正は必ずブランチを切ってPR（Pull Request）でマージ
    - ブランチ名例: `feature/xxx`, `fix/xxx`, `docs/xxx`
- **コミットメッセージ**
    - 何を・なぜ変更したかを簡潔に記述（日本語可）
    - 例: `fix: タグ追加時のバリデーション強化`
- **コードレビュー**
    - 原則PRベースでレビュー・承認後にマージ
    - レビュー観点：可読性・テスト・型安全・例外処理・運用性
- **CI/CD**
    - push/PR時にGitHub Actionsで自動テスト・型チェック・カバレッジ計測
    - 失敗時はアーティファクトでログ確認
- **テスト・型チェック**
    - 主要ロジックは必ずpytestでユニットテスト・mypyで型チェック
    - 例外系・エッジケースもカバー
- **ドキュメント整備**
    - 仕様・運用ルール・FAQ・API仕様はREADMEやToDoリスト、別mdで管理
- **バックアップ・リカバリ**
    - DBや設定ファイルは定期的にbackup/配下へ自動/手動バックアップ
- **その他**
    - 進捗・課題・運用メモはToDoリスト.mdに随時記録

## 🗄️ DB・設定ファイルの自動バックアップ・リカバリ手順

### バックアップ運用
- 進捗前や重要な操作前に `resources/tags.db` を `backup/` フォルダへコピー
    - 例: `copy resources\tags.db backup\tags_backup_YYYYMMDD_HHMMSS.db`
- アプリ起動時や定期的に自動バックアップする仕組みも導入可能（スクリプト例は下記）

### 自動バックアップスクリプト例（Windowsバッチ）
```bat
@echo off
set dt=%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set dt=%dt: =0%
copy resources\tags.db backup\tags_backup_%dt%.db
```

### 定期バックアップの自動化例
- **Windowsタスクスケジューラ**：
    - バッチファイル（例: backup_db.bat）を作成し、以下の内容を記述：
      ```bat
      @echo off
      set dt=%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%
      set dt=%dt: =0%
      copy resources\tags.db backup\tags_backup_%dt%.db
      ```
    - タスクスケジューラで「毎日」「毎時」など任意の頻度で実行
- **Linux/Mac（cron）**：
    - crontabに以下のように登録：
      ```cron
      0 2 * * * cp /path/to/resources/tags.db /path/to/backup/tags_backup_$(date +\%Y\%m\%d_\%H\%M\%S).db
      ```
    - 上記は毎日2時にバックアップを取得

### リカバリ手順
- 不具合発生時は `backup/` 内のバックアップDBを `resources/tags.db` に上書きコピー
- 上書き後、アプリを再起動

### 注意点
- バックアップは定期的に/重要操作前に必ず取得
- バックアップファイル名に日付・時刻を含めて世代管理
- 設定ファイル（theme_settings.json等）も同様にバックアップ推奨

## ❓ FAQ（よくある質問）

### Q. 初回セットアップ・依存インストール方法は？
A. `python -m venv venv` → `venv/を有効化` → `pip install -r requirements.txt` でOKです。

### Q. テストはどうやって実行する？
A. `run_tests.bat` または `pytest` コマンドで全テストが実行できます。

### Q. カバレッジや型チェックは？
A. `pytest --cov=modules` でカバレッジ計測、`mypy modules/` で型チェックできます。

### Q. CSVでエクスポート/インポートできますか？
A. はい。エクスポート/インポート時にCSVファイルを選択できます（カラム: tag, jp, category, favorite, is_negative）。

### Q. 複数タグを一括で編集できますか？
A. はい。複数選択→「一括編集」ボタンでカテゴリ・日本語訳をまとめて変更できます。

### Q. 検索はどこまでできますか？
A. タグ名・カテゴリ・日本語訳・お気に入り状態を横断的に絞り込み可能です。

### Q. 初回起動時のガイドや操作説明は？
A. 初回起動時に使い方ガイドが自動表示されます。各ボタンにもツールチップ説明があります。

### Q. フィードバックや不具合報告は？
A. メニューバーの「フィードバック」ボタンやREADME記載のIssuesページからご連絡ください。

### Q. その他のトラブルシュートは？
A. `logs/`配下のログや、CIのアーティファクト（pytest.log, mypy.log等）を参照してください。

## 🖥️ 操作マニュアル

### 1. アプリの起動
- `run_app.bat` をダブルクリック、またはコマンドラインで `python main.py` を実行
- 初回起動時は必要なライブラリが自動インストールされます

### 2. タグの追加
- 「タグ追加」欄に新しいタグ名を入力し、「追加」ボタンを押す
- カテゴリやお気に入りも同時に設定可能

### 3. タグの編集・削除
- タグ一覧から編集・削除したいタグを選択し、右クリックメニューまたはボタンで操作

### 4. カテゴリの切り替え・説明表示
- 画面左のカテゴリタブをクリックすると、該当カテゴリのタグ一覧と説明が表示されます
- 「全カテゴリ」「お気に入り」「最近使った」「未分類」も選択可能

### 5. タグのエクスポート・インポート
- 「選択タグをエクスポート」ボタンでJSONファイルに保存
- 「インポート」ボタンで外部JSONからタグを一括追加

### 6. バックアップ・リカバリ
- `backup/`フォルダに自動/手動でDBバックアップが保存されます
- 不具合時はバックアップDBを `resources/tags.db` に上書きコピーで復元可能

### 7. よくある操作例
- タグのカテゴリ一括変更：タグを複数選択→右クリック→「カテゴリ変更」
- タグのお気に入り切替：タグを選択→右クリック→「お気に入り切替」
- 最近使ったタグの確認：「最近使った」タブを選択

### 8. トラブルシュート
- 起動しない/エラー時は `logs/`配下のログを確認
- テスト・カバレッジ確認は `run_tests.bat` や `pytest --cov=modules` を実行

## 💬 ユーザーフィードバック受付窓口

- 不具合報告・ご要望・ご質問は、GitHubの[Issues](https://github.com/（あなたのリポジトリURL）/issues)からご連絡ください。
- 可能であれば、再現手順・エラーメッセージ・環境情報（OS/バージョン等）もご記載ください。
- メールでのご連絡も受け付けます：`your-contact@example.com`（※必要に応じて修正）
- 今後、アプリUI内にも「フィードバック」ボタン等を設置予定です。

import subprocess
import sys
import os

import shutil

def run_command(command):
    """指定されたコマンドを実行し、エラーがあれば例外を発生させる"""
    try:
        # shell=True を使う場合、コマンドは文字列として渡すのが一般的
        cmd_str = ' '.join(command)
        print(f"実行中: {cmd_str}")
        subprocess.run(cmd_str, check=True, shell=True)
    except subprocess.CalledProcessError as e:
        print(f"エラー: コマンド '{cmd_str}' の実行に失敗しました。リターンコード: {e.returncode}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print(f"エラー: コマンド '{command[0]}' が見つかりません。パスが通っているか確認してください。", file=sys.stderr)
        sys.exit(1)

def main():
    """ビルドプロセスを実行するメイン関数"""
    project_root = os.path.dirname(os.path.abspath(__file__))
    dist_path = os.path.join(project_root, "dist")
    work_path = os.path.join(project_root, "build")

    # --- ビルド関連ファイルのクリーンアップ ---
    print("--- 古いビルドファイルをクリーンアップ ---")
    if os.path.exists(dist_path):
        shutil.rmtree(dist_path)
        print(f"削除しました: {dist_path}")
    if os.path.exists(work_path):
        shutil.rmtree(work_path)
        print(f"削除しました: {work_path}")

    # --- 個人データのクリーンアップ ---
    print("--- 個人データをクリーンアップ ---")
    data_dir = os.path.join(project_root, "data")
    backup_dir = os.path.join(project_root, "backup")
    logs_dir = os.path.join(project_root, "logs")

    for d in [data_dir, backup_dir, logs_dir]:
        if os.path.exists(d):
            try:
                shutil.rmtree(d)
                print(f"削除しました: {d}")
            except OSError as e:
                print(f"エラー: {d} の削除に失敗しました: {e}", file=sys.stderr)
        else:
            print(f"スキップ: {d} は存在しません。")

    # このスクリプトが仮想環境から実行されているか確認
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("エラー: このスクリプトはPythonの仮想環境内から実行する必要があります。", file=sys.stderr)
        print("仮想環境を有効化してから再実行してください。例: .\\.venv\\Scripts\\activate", file=sys.stderr)
        sys.exit(1)

    # PyInstallerのインストール
    print("--- PyInstallerのインストール ---")
    run_command([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # .exeのビルド
    print("--- .exeのビルド開始 (デバッグモード) ---")
    main_script_path = os.path.join(project_root, "src", "main.py")
    icon_path = os.path.join(project_root, "src", "icon.ico")

    # --- パス設定 ---
    # PyInstallerで使うパスの区切り文字を設定 (Windows: ;, Linux/Mac: :)
    sep = os.pathsep

    # --- データファイルの指定 ---
    # アプリケーションが必要とする可能性のあるデータファイルやフォルダを追加
    # 形式: --add-data "source_path{sep}destination_in_exe"
    # 例: "src/resources;resources" -> src/resources フォルダをEXE内の resources フォルダとしてコピー
    add_data_commands = [
        f"--add-data=src/modules{sep}modules",
        f"--add-data=src/resources{sep}resources",
    ]

    pyinstaller_command = [
        sys.executable,
        "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--paths=src",
        f"--icon={icon_path}",
        f"--distpath={dist_path}",
        f"--workpath={work_path}",
    ]
    
    # データ追加コマンドを結合
    pyinstaller_command.extend(add_data_commands)
    
    # メインスクリプトを追加
    pyinstaller_command.append(main_script_path)

    run_command(pyinstaller_command)

    print("--- ビルド成功！ ---")
    print(f"実行可能ファイルは '{dist_path}' フォルダに作成されました。")

if __name__ == "__main__":
    main()

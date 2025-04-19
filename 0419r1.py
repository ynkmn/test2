import os
import argparse


def find_process_folders(directory):
    """
    指定されたディレクトリ内で「process_」で始まるフォルダを検索する関数
    
    Args:
        directory (str): スキャンするディレクトリのパス
        
    Returns:
        dict: プロセスフォルダに関する情報を含む辞書
    """
    # 結果を格納する辞書の初期化
    result = {
        "process_folders": [],      # すべてのprocess_フォルダのリスト
        "required_folders": {       # 必須フォルダの存在状態
            "process_a": {
                "exists": False,
                "required_file": "a.out",
                "file_exists": False
            },
            "process_s": {
                "exists": False,
                "required_file": "s.out",
                "file_exists": False
            }
        },
        "status": {                 # 全体のステータス情報
            "total_process_folders": 0,
            "required_folders_exist": False,
            "required_files_exist": False,
            "all_requirements_met": False
        }
    }
    
    try:
        # ディレクトリが存在するか確認
        if not os.path.exists(directory) or not os.path.isdir(directory):
            raise FileNotFoundError(f"指定されたディレクトリが見つかりません: {directory}")
        
        # ディレクトリ内のすべてのエントリを取得
        entries = os.listdir(directory)
        
        # 「process_」で始まるフォルダをフィルタリング
        process_folders = [entry for entry in entries 
                          if os.path.isdir(os.path.join(directory, entry)) 
                          and entry.startswith("process_")]
        
        # 見つかったすべてのprocess_フォルダをリストに追加
        result["process_folders"] = process_folders
        result["status"]["total_process_folders"] = len(process_folders)
        
        # 必須フォルダの存在を確認
        for folder_name in ["process_a", "process_s"]:
            if folder_name in process_folders:
                result["required_folders"][folder_name]["exists"] = True
                
                # 必須ファイルの存在を確認
                required_file = result["required_folders"][folder_name]["required_file"]
                file_path = os.path.join(directory, folder_name, required_file)
                if os.path.exists(file_path) and os.path.isfile(file_path):
                    result["required_folders"][folder_name]["file_exists"] = True
        
        # 全体のステータスを更新
        req_folders_exist = all(info["exists"] for info in result["required_folders"].values())
        req_files_exist = all(info["file_exists"] for info in result["required_folders"].values())
        
        result["status"]["required_folders_exist"] = req_folders_exist
        result["status"]["required_files_exist"] = req_files_exist
        result["status"]["all_requirements_met"] = req_folders_exist and req_files_exist
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        result["error"] = str(e)
    
    return result


def print_check_results(results):
    """
    フォルダチェック結果を整形して表示する関数
    
    Args:
        results (dict): find_process_folders関数からの結果
    """
    print("\n===== フォルダチェック結果 =====")
    
    # エラーがあれば表示
    if "error" in results:
        print(f"エラー: {results['error']}")
        return
    
    # 必須フォルダと必須ファイルのステータス表示
    print("\n必須フォルダとファイルのステータス:")
    for folder, info in results["required_folders"].items():
        folder_status = "✓ 存在します" if info["exists"] else "✗ 見つかりません"
        print(f"  {folder}: {folder_status}")
        
        if info["exists"]:
            file_status = "✓ 存在します" if info["file_exists"] else "✗ 見つかりません"
            print(f"    - {info['required_file']}: {file_status}")
    
    # 全体のステータス表示
    print("\n全体の状況:")
    print(f"  確認されたprocess_フォルダの総数: {results['status']['total_process_folders']}")
    
    if results["status"]["all_requirements_met"]:
        print("  ✓ すべての要件を満たしています！グラフ作成に進めます。")
    else:
        print("  ✗ すべての要件を満たしていません。以下の問題を修正してください:")
        
        if not results["status"]["required_folders_exist"]:
            print("    - 必須フォルダ(process_a, process_s)が一部または全部見つかりません")
        
        if not results["status"]["required_files_exist"]:
            print("    - 必須ファイル(a.out, s.out)が一部または全部見つかりません")
    
    # すべてのprocess_フォルダのリスト表示
    print("\n検出されたすべてのprocess_フォルダ:")
    if results["process_folders"]:
        for folder in results["process_folders"]:
            print(f"  - {folder}")
    else:
        print("  見つかりませんでした")


def main():
    # コマンドライン引数の設定
    parser = argparse.ArgumentParser(description="指定されたディレクトリ内のprocess_フォルダをチェックするツール")
    parser.add_argument("-d", "--directory", default=".", help="スキャンするディレクトリのパス（デフォルト: カレントディレクトリ）")
    args = parser.parse_args()
    
    # 指定されたディレクトリをスキャン
    print(f"ディレクトリ '{args.directory}' をスキャンしています...")
    results = find_process_folders(args.directory)
    
    # 結果を表示
    print_check_results(results)
    
    # 結果を返す（他のスクリプトから呼び出される場合に便利）
    return results


if __name__ == "__main__":
    main()
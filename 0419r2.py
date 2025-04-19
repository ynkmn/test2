import os
import argparse
import glob
import re


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
            },
            "process_c": {
                "exists": False,
                "required_files_pattern": "def_*.dat",
                "min_required_files": 100,
                "found_files": 0,
                "files_requirement_met": False,
                "file_list": []
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
        for folder_name, folder_info in result["required_folders"].items():
            if folder_name in process_folders:
                result["required_folders"][folder_name]["exists"] = True
                
                # フォルダによって異なるファイルチェックロジックを適用
                if folder_name in ["process_a", "process_s"]:
                    # 単一の必須ファイルをチェック
                    required_file = folder_info["required_file"]
                    file_path = os.path.join(directory, folder_name, required_file)
                    if os.path.exists(file_path) and os.path.isfile(file_path):
                        result["required_folders"][folder_name]["file_exists"] = True
                
                elif folder_name == "process_c":
                    # パターンに一致する連番ファイルをチェック
                    pattern = os.path.join(directory, folder_name, "def_*.dat")
                    matching_files = glob.glob(pattern)
                    
                    # ファイル名をリストに保存
                    result["required_folders"][folder_name]["file_list"] = [os.path.basename(f) for f in matching_files]
                    result["required_folders"][folder_name]["found_files"] = len(matching_files)
                    
                    # 必要な数のファイルが存在するかチェック
                    if len(matching_files) >= folder_info["min_required_files"]:
                        result["required_folders"][folder_name]["files_requirement_met"] = True
                        
                    # 実際のファイル番号の範囲を分析
                    numbers = []
                    for file_path in matching_files:
                        file_name = os.path.basename(file_path)
                        match = re.search(r'def_(\d+)\.dat', file_name)
                        if match:
                            numbers.append(int(match.group(1)))
                    
                    if numbers:
                        result["required_folders"][folder_name]["min_number"] = min(numbers)
                        result["required_folders"][folder_name]["max_number"] = max(numbers)
                        result["required_folders"][folder_name]["total_unique_numbers"] = len(set(numbers))
        
        # 全体のステータスを更新
        # 全ての必須フォルダが存在するか確認
        req_folders_exist = all(info["exists"] for info in result["required_folders"].values())
        result["status"]["required_folders_exist"] = req_folders_exist
        
        # ファイル要件を確認 (フォルダタイプごとに異なる条件)
        files_requirements_met = True
        
        # process_aとprocess_sで必須ファイルが存在するか確認
        for folder_name in ["process_a", "process_s"]:
            if folder_name in result["required_folders"]:
                if not result["required_folders"][folder_name]["file_exists"]:
                    files_requirements_met = False
        
        # process_cで必要な数のファイルが存在するか確認
        if "process_c" in result["required_folders"]:
            if not result["required_folders"]["process_c"]["files_requirement_met"]:
                files_requirements_met = False
        
        result["status"]["required_files_exist"] = files_requirements_met
        result["status"]["all_requirements_met"] = req_folders_exist and files_requirements_met
        
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
            # process_a と process_s のファイルチェック
            if folder in ["process_a", "process_s"]:
                file_status = "✓ 存在します" if info["file_exists"] else "✗ 見つかりません"
                print(f"    - {info['required_file']}: {file_status}")
            
            # process_c の連番ファイルチェック
            elif folder == "process_c":
                files_status = "✓ 必要数のファイルが存在します" if info["files_requirement_met"] else f"✗ 必要なファイル数が不足しています ({info['found_files']}/{info['min_required_files']})"
                print(f"    - {info['required_files_pattern']}: {files_status}")
                
                if info["found_files"] > 0:
                    print(f"      - 検出されたファイル数: {info['found_files']}")
                    if "min_number" in info and "max_number" in info:
                        print(f"      - ファイル番号の範囲: {info['min_number']}～{info['max_number']}")
                    if "total_unique_numbers" in info:
                        print(f"      - ユニークなファイル番号の数: {info['total_unique_numbers']}")
                    
                    # 最初の5ファイルのサンプルを表示
                    file_samples = info["file_list"][:5]
                    if file_samples:
                        print(f"      - サンプルファイル: {', '.join(file_samples)}" + 
                              (" ... など" if len(info["file_list"]) > 5 else ""))
    
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
            print("    - 必須ファイル要件が満たされていません:")
            
            # 個別のファイル問題を表示
            for folder_name, info in results["required_folders"].items():
                if info["exists"]:  # フォルダが存在する場合のみファイルチェック
                    if folder_name in ["process_a", "process_s"] and not info["file_exists"]:
                        print(f"      - {folder_name}内の{info['required_file']}が見つかりません")
                    elif folder_name == "process_c" and not info["files_requirement_met"]:
                        print(f"      - {folder_name}内のdef_*.datファイルが不足しています ({info['found_files']}/{info['min_required_files']}必要)")
    
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
    parser.add_argument("-m", "--min-files", type=int, default=100, 
                        help="process_cフォルダ内に必要な最小ファイル数（デフォルト: 100）")
    parser.add_argument("-q", "--quiet", action="store_true", 
                        help="詳細出力を抑制し、結果のサマリーのみを表示")
    args = parser.parse_args()
    
    # 指定されたディレクトリをスキャン
    if not args.quiet:
        print(f"ディレクトリ '{args.directory}' をスキャンしています...")
    
    # process_cフォルダの必要最小ファイル数を設定
    results = find_process_folders(args.directory)
    if "process_c" in results["required_folders"]:
        results["required_folders"]["process_c"]["min_required_files"] = args.min_files
        
        # ファイル要件が満たされているかを再チェック
        if results["required_folders"]["process_c"]["exists"]:
            found_files = results["required_folders"]["process_c"]["found_files"]
            results["required_folders"]["process_c"]["files_requirement_met"] = found_files >= args.min_files
            
            # 全体のステータスを更新
            files_requirements_met = True
            for folder_name in ["process_a", "process_s"]:
                if not results["required_folders"][folder_name]["file_exists"]:
                    files_requirements_met = False
            
            if not results["required_folders"]["process_c"]["files_requirement_met"]:
                files_requirements_met = False
                
            results["status"]["required_files_exist"] = files_requirements_met
            results["status"]["all_requirements_met"] = results["status"]["required_folders_exist"] and files_requirements_met
    
    # 結果を表示（quiet モードでなければ）
    if not args.quiet:
        print_check_results(results)
    else:
        # quietモードでは簡潔な結果のみ表示
        status = "成功" if results["status"]["all_requirements_met"] else "失敗"
        print(f"チェック結果: {status}")
    
    # 結果を返す（他のスクリプトから呼び出される場合に便利）
    return results


if __name__ == "__main__":
    main()
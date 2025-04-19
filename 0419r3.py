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
                "folder_pattern": "process_a*",
                "matching_folders": [],
                "required_file_patterns": ["*.01d", "*.02d"],
                "found_files": {"*.01d": [], "*.02d": []},
                "files_exist": False
            },
            "process_s": {
                "exists": False,
                "required_file_pattern": "plot_*ms.txt",
                "found_files": [],
                "min_required_files": 2,  # 最低2つのファイルが必要
                "files_requirement_met": False
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
        
        # process_a* パターンに一致するフォルダを検索
        process_a_pattern = "process_a*"
        process_a_folders = [folder for folder in process_folders 
                            if glob.fnmatch.fnmatch(folder, process_a_pattern)]
        
        if process_a_folders:
            result["required_folders"]["process_a"]["exists"] = True
            result["required_folders"]["process_a"]["matching_folders"] = process_a_folders
            
            # 各 process_a* フォルダ内の必須ファイルをチェック
            files_01d = []
            files_02d = []
            
            for folder in process_a_folders:
                # *.01d ファイルのチェック
                pattern_01d = os.path.join(directory, folder, "*.01d")
                matching_files_01d = glob.glob(pattern_01d)
                files_01d.extend([os.path.basename(f) for f in matching_files_01d])
                
                # *.02d ファイルのチェック
                pattern_02d = os.path.join(directory, folder, "*.02d")
                matching_files_02d = glob.glob(pattern_02d)
                files_02d.extend([os.path.basename(f) for f in matching_files_02d])
            
            result["required_folders"]["process_a"]["found_files"]["*.01d"] = files_01d
            result["required_folders"]["process_a"]["found_files"]["*.02d"] = files_02d
            
            # 両方のパターンのファイルが見つかったかチェック
            result["required_folders"]["process_a"]["files_exist"] = (len(files_01d) > 0 and len(files_02d) > 0)
        
        # process_s フォルダのチェック
        if "process_s" in process_folders:
            result["required_folders"]["process_s"]["exists"] = True
            
            # plot_*ms.txt パターンのファイルをチェック
            pattern = os.path.join(directory, "process_s", "plot_*ms.txt")
            matching_files = glob.glob(pattern)
            
            # ファイル名をリストに保存
            result["required_folders"]["process_s"]["found_files"] = [os.path.basename(f) for f in matching_files]
            
            # 必要な数のファイルが存在するかチェック
            min_required = result["required_folders"]["process_s"]["min_required_files"]
            if len(matching_files) >= min_required:
                result["required_folders"]["process_s"]["files_requirement_met"] = True
                
            # ミリ秒値を抽出して分析
            ms_values = []
            for file_path in matching_files:
                file_name = os.path.basename(file_path)
                match = re.search(r'plot_(\d+)ms\.txt', file_name)
                if match:
                    ms_values.append(int(match.group(1)))
            
            if ms_values:
                result["required_folders"]["process_s"]["min_ms"] = min(ms_values)
                result["required_folders"]["process_s"]["max_ms"] = max(ms_values)
                result["required_folders"]["process_s"]["ms_count"] = len(ms_values)
        
        # process_c フォルダのチェック
        if "process_c" in process_folders:
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
        
        # process_aのファイル要件確認
        if not result["required_folders"]["process_a"]["files_exist"]:
            files_requirements_met = False
        
        # process_sのファイル要件確認
        if not result["required_folders"]["process_s"]["files_requirement_met"]:
            files_requirements_met = False
        
        # process_cのファイル要件確認
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
    
    # --- process_a* フォルダのステータス ---
    folder_status = "✓ 存在します" if results["required_folders"]["process_a"]["exists"] else "✗ 見つかりません"
    print(f"  process_a* パターン: {folder_status}")
    
    if results["required_folders"]["process_a"]["exists"]:
        # マッチしたフォルダを表示
        matching_folders = results["required_folders"]["process_a"]["matching_folders"]
        print(f"    - マッチしたフォルダ: {', '.join(matching_folders)}")
        
        # ファイルパターンごとに結果を表示
        for pattern in ["*.01d", "*.02d"]:
            files = results["required_folders"]["process_a"]["found_files"][pattern]
            file_status = "✓ 存在します" if files else "✗ 見つかりません"
            file_count = len(files)
            print(f"    - {pattern}: {file_status} ({file_count}ファイル)")
            
            # サンプルファイルを表示
            if files:
                samples = files[:3]
                print(f"      サンプル: {', '.join(samples)}" + 
                      (" ..." if len(files) > 3 else ""))
    
    # --- process_s フォルダのステータス ---
    folder_status = "✓ 存在します" if results["required_folders"]["process_s"]["exists"] else "✗ 見つかりません"
    print(f"  process_s: {folder_status}")
    
    if results["required_folders"]["process_s"]["exists"]:
        pattern = results["required_folders"]["process_s"]["required_file_pattern"]
        files = results["required_folders"]["process_s"]["found_files"]
        file_count = len(files)
        min_required = results["required_folders"]["process_s"]["min_required_files"]
        
        files_status = "✓ 必要数のファイルが存在します" if results["required_folders"]["process_s"]["files_requirement_met"] else f"✗ 必要なファイル数が不足しています ({file_count}/{min_required}必要)"
        print(f"    - {pattern}: {files_status}")
        
        if file_count > 0:
            print(f"      - 検出されたファイル数: {file_count}")
            if "min_ms" in results["required_folders"]["process_s"] and "max_ms" in results["required_folders"]["process_s"]:
                print(f"      - ミリ秒値の範囲: {results['required_folders']['process_s']['min_ms']}ms～{results['required_folders']['process_s']['max_ms']}ms")
            
            # サンプルファイルを表示
            samples = files[:3]
            print(f"      - サンプルファイル: {', '.join(samples)}" + 
                  (" ..." if file_count > 3 else ""))
    
    # --- process_c フォルダのステータス ---
    folder_status = "✓ 存在します" if results["required_folders"]["process_c"]["exists"] else "✗ 見つかりません"
    print(f"  process_c: {folder_status}")
    
    if results["required_folders"]["process_c"]["exists"]:
        files_status = "✓ 必要数のファイルが存在します" if results["required_folders"]["process_c"]["files_requirement_met"] else f"✗ 必要なファイル数が不足しています ({results['required_folders']['process_c']['found_files']}/{results['required_folders']['process_c']['min_required_files']}必要)"
        print(f"    - {results['required_folders']['process_c']['required_files_pattern']}: {files_status}")
        
        if results["required_folders"]["process_c"]["found_files"] > 0:
            print(f"      - 検出されたファイル数: {results['required_folders']['process_c']['found_files']}")
            if "min_number" in results["required_folders"]["process_c"] and "max_number" in results["required_folders"]["process_c"]:
                print(f"      - ファイル番号の範囲: {results['required_folders']['process_c']['min_number']}～{results['required_folders']['process_c']['max_number']}")
            if "total_unique_numbers" in results["required_folders"]["process_c"]:
                print(f"      - ユニークなファイル番号の数: {results['required_folders']['process_c']['total_unique_numbers']}")
            
            # 最初の3ファイルのサンプルを表示
            file_samples = results["required_folders"]["process_c"]["file_list"][:3]
            if file_samples:
                print(f"      - サンプルファイル: {', '.join(file_samples)}" + 
                      (" ..." if len(results["required_folders"]["process_c"]["file_list"]) > 3 else ""))
    
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
            
            # process_a のファイル問題を表示
            if results["required_folders"]["process_a"]["exists"] and not results["required_folders"]["process_a"]["files_exist"]:
                missing_patterns = []
                for pattern in ["*.01d", "*.02d"]:
                    if not results["required_folders"]["process_a"]["found_files"][pattern]:
                        missing_patterns.append(pattern)
                if missing_patterns:
                    print(f"      - process_a*フォルダ内の {', '.join(missing_patterns)} パターンのファイルが見つかりません")
            
            # process_s のファイル問題を表示
            if results["required_folders"]["process_s"]["exists"] and not results["required_folders"]["process_s"]["files_requirement_met"]:
                found = len(results["required_folders"]["process_s"]["found_files"])
                needed = results["required_folders"]["process_s"]["min_required_files"]
                print(f"      - process_s内のplot_*ms.txtファイルが不足しています ({found}/{needed}必要)")
            
            # process_c のファイル問題を表示
            if results["required_folders"]["process_c"]["exists"] and not results["required_folders"]["process_c"]["files_requirement_met"]:
                found = results["required_folders"]["process_c"]["found_files"]
                needed = results["required_folders"]["process_c"]["min_required_files"]
                print(f"      - process_c内のdef_*.datファイルが不足しています ({found}/{needed}必要)")
    
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
    parser.add_argument("-mc", "--min-files-c", type=int, default=100, 
                        help="process_cフォルダ内に必要な最小ファイル数（デフォルト: 100）")
    parser.add_argument("-ms", "--min-files-s", type=int, default=2, 
                        help="process_sフォルダ内に必要な最小ファイル数（デフォルト: 2）")
    parser.add_argument("-q", "--quiet", action="store_true", 
                        help="詳細出力を抑制し、結果のサマリーのみを表示")
    args = parser.parse_args()
    
    # 指定されたディレクトリをスキャン
    if not args.quiet:
        print(f"ディレクトリ '{args.directory}' をスキャンしています...")
    
    # 各フォルダの必要最小ファイル数を設定してスキャン実行
    results = find_process_folders(args.directory)
    
    # process_cフォルダの必要最小ファイル数を設定
    if "process_c" in results["required_folders"]:
        results["required_folders"]["process_c"]["min_required_files"] = args.min_files_c
        
        # ファイル要件が満たされているかを再チェック
        if results["required_folders"]["process_c"]["exists"]:
            found_files = results["required_folders"]["process_c"]["found_files"]
            results["required_folders"]["process_c"]["files_requirement_met"] = found_files >= args.min_files_c
    
    # process_sフォルダの必要最小ファイル数を設定
    if "process_s" in results["required_folders"]:
        results["required_folders"]["process_s"]["min_required_files"] = args.min_files_s
        
        # ファイル要件が満たされているかを再チェック
        if results["required_folders"]["process_s"]["exists"]:
            found_files = len(results["required_folders"]["process_s"]["found_files"])
            results["required_folders"]["process_s"]["files_requirement_met"] = found_files >= args.min_files_s
    
    # 全体のステータスを更新
    files_requirements_met = True
    
    # process_aのファイル要件確認
    if not results["required_folders"]["process_a"]["files_exist"]:
        files_requirements_met = False
    
    # process_sのファイル要件確認
    if not results["required_folders"]["process_s"]["files_requirement_met"]:
        files_requirements_met = False
    
    # process_cのファイル要件確認
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
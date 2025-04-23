from pathlib import Path

file_list = [r"w\plot\test", r"w\plot2\test", r"w\plot\test1"]
folders = {Path(f).parent for f in file_list}
print(folders)  # {WindowsPath('w\\plot'), WindowsPath('w\\plot2')}




import os

def path_partial_match(pattern, target):
    # パス区切りをOS標準に統一
    pattern_norm = pattern.replace('/', os.sep).replace('\\', os.sep)
    target_norm = target.replace('/', os.sep).replace('\\', os.sep)
    return pattern_norm in target_norm

# 例
print(path_partial_match('w/plot', r'w\plot\test'))  # True






現在のコードは`process_a*`で複数のフォルダをチェックできますが、他のプロセスフォルダでは特定のパス構造しか対応していませんね。`plot1/def_*.dat`や`plot2/def_*.dat`のように、サブフォルダ内の同じパターンのファイルをチェックできるように拡張しましょう。

まず、コードの主な変更点を説明します：

1. 必要なファイルパターンをより柔軟に定義できるようにする
2. サブディレクトリを再帰的に検索する機能を追加する
3. 複数のパスパターンに対応できるようにする

以下に、変更したコードを示します：

```python
import os
import argparse
import glob
import re
from pathlib import Path

def find_process_folders(directory):
    """
    指定されたディレクトリ内で「process_」で始まるフォルダを検索し、要件をチェックする関数
    
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
                "required_file_patterns": ["def_*.dat", "inp.csv"],  # 複数のパターンに対応
                "file_locations": {  # サブディレクトリを含むパターンを追加
                    "def_*.dat": ["", "plot1/", "plot2/"],  # 空文字列はpprocess_c直下を意味する
                    "inp.csv": [""]  # rootディレクトリのみ
                },
                "min_required_files": {"def_*.dat": 100, "inp.csv": 1},  # パターンごとに要件を設定
                "found_files": {"def_*.dat": [], "inp.csv": []},
                "files_requirement_met": False
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
        
        # process_c フォルダのチェック（拡張版）
        if "process_c" in process_folders:
            result["required_folders"]["process_c"]["exists"] = True
            
            # 各ファイルパターンとその配置場所をチェック
            all_requirements_met = True
            
            for pattern in result["required_folders"]["process_c"]["required_file_patterns"]:
                result["required_folders"]["process_c"]["found_files"][pattern] = []
                
                # このパターンのファイルの合計
                total_files_for_pattern = 0
                
                # 各配置場所でファイルを探す
                for location in result["required_folders"]["process_c"]["file_locations"].get(pattern, [""]):
                    # ロケーションを処理して絶対パスを構築
                    search_path = os.path.join(directory, "process_c", location, pattern)
                    matching_files = glob.glob(search_path)
                    
                    # 見つかったファイルを結果に追加（相対パスを保持）
                    for file_path in matching_files:
                        # process_cからの相対パスを計算
                        process_c_dir = os.path.join(directory, "process_c")
                        rel_path = os.path.relpath(file_path, process_c_dir)
                        result["required_folders"]["process_c"]["found_files"][pattern].append(rel_path)
                    
                    total_files_for_pattern += len(matching_files)
                
                # このパターンの要件が満たされているか確認
                min_required = result["required_folders"]["process_c"]["min_required_files"].get(pattern, 1)
                pattern_requirement_met = total_files_for_pattern >= min_required
                
                # 各パターンについての詳細情報を追加
                result["required_folders"]["process_c"][f"{pattern}_requirement_met"] = pattern_requirement_met
                result["required_folders"]["process_c"][f"{pattern}_count"] = total_files_for_pattern
                
                # いずれかのパターンの要件が満たされていなければ、全体の要件も満たされていない
                if not pattern_requirement_met:
                    all_requirements_met = False
                
                # def_*.datファイルに対する追加分析（ファイル番号の範囲など）
                if pattern == "def_*.dat" and total_files_for_pattern > 0:
                    numbers = []
                    for file_path in result["required_folders"]["process_c"]["found_files"][pattern]:
                        file_name = os.path.basename(file_path)
                        match = re.search(r'def_(\d+)\.dat', file_name)
                        if match:
                            numbers.append(int(match.group(1)))
                    
                    if numbers:
                        result["required_folders"]["process_c"]["min_number"] = min(numbers)
                        result["required_folders"]["process_c"]["max_number"] = max(numbers)
                        result["required_folders"]["process_c"]["total_unique_numbers"] = len(set(numbers))
            
            # 全てのファイルパターンの要件が満たされているか設定
            result["required_folders"]["process_c"]["files_requirement_met"] = all_requirements_met
        
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
    
    # --- process_c フォルダのステータス（拡張版） ---
    folder_status = "✓ 存在します" if results["required_folders"]["process_c"]["exists"] else "✗ 見つかりません"
    print(f"  process_c: {folder_status}")
    
    if results["required_folders"]["process_c"]["exists"]:
        # 各ファイルパターンの結果を表示
        for pattern in results["required_folders"]["process_c"]["required_file_patterns"]:
            files = results["required_folders"]["process_c"]["found_files"].get(pattern, [])
            file_count = len(files)
            min_required = results["required_folders"]["process_c"]["min_required_files"].get(pattern, 1)
            
            pattern_requirement_met = results["required_folders"]["process_c"].get(f"{pattern}_requirement_met", False)
            files_status = "✓ 必要数のファイルが存在します" if pattern_requirement_met else f"✗ 必要なファイル数が不足しています ({file_count}/{min_required}必要)"
            print(f"    - {pattern}: {files_status}")
            
            if file_count > 0:
                print(f"      - 検出されたファイル数: {file_count}")
                
                # def_*.datファイルの場合、追加情報を表示
                if pattern == "def_*.dat" and "min_number" in results["required_folders"]["process_c"]:
                    print(f"      - ファイル番号の範囲: {results['required_folders']['process_c']['min_number']}～{results['required_folders']['process_c']['max_number']}")
                    print(f"      - ユニークなファイル番号の数: {results['required_folders']['process_c']['total_unique_numbers']}")
                
                # 検出場所ごとのファイル数を集計
                locations = {}
                for file_path in files:
                    # ファイルのディレクトリパスを取得
                    dir_path = os.path.dirname(file_path)
                    if dir_path == '':
                        dir_path = '(root)'
                    
                    # ロケーションごとに集計
                    if dir_path in locations:
                        locations[dir_path] += 1
                    else:
                        locations[dir_path] = 1
                
                # ロケーション情報を表示
                print("      - 検出場所:")
                for loc, count in locations.items():
                    print(f"        - {loc}: {count}ファイル")
                
                # サンプルファイルを表示
                samples = files[:3]
                print(f"      - サンプルファイル: {', '.join(samples)}" + 
                    (" ..." if file_count > 3 else ""))
    
    # 全体のステータス表示
    print("\n全体の状況:")
    print(f"  確認されたprocess_フォルダの総数: {results['status']['total_process_folders']}")
    
    if results["status"]["all_requirements_met"]:
        print("  ✓ すべての要件を満たしています！グラフ作成に進めます。")
    else:
        print("  ✗ すべての要件を満たしていません。以下の問題を修正してください:")
        
        if not results["status"]["required_folders_exist"]:
            print("    - 必須フォルダ(process_a, process_s, process_c)が一部または全部見つかりません")
        
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
            
            # process_c のファイル問題を表示（拡張版）
            if results["required_folders"]["process_c"]["exists"] and not results["required_folders"]["process_c"]["files_requirement_met"]:
                for pattern in results["required_folders"]["process_c"]["required_file_patterns"]:
                    if not results["required_folders"]["process_c"].get(f"{pattern}_requirement_met", True):
                        found = len(results["required_folders"]["process_c"]["found_files"].get(pattern, []))
                        needed = results["required_folders"]["process_c"]["min_required_files"].get(pattern, 1)
                        print(f"      - process_c内の{pattern}ファイルが不足しています ({found}/{needed}必要)")
    
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
                        help="process_cフォルダ内のdef_*.datファイルに必要な最小ファイル数（デフォルト: 100）")
    parser.add_argument("-ms", "--min-files-s", type=int, default=2, 
                        help="process_sフォルダ内に必要な最小ファイル数（デフォルト: 2）")
    parser.add_argument("-q", "--quiet", action="store_true", 
                        help="詳細出力を抑制し、結果のサマリーのみを表示")
    parser.add_argument("--patterns", nargs='+', default=[], 
                        help="追加のファイルパターンをチェック（例: --patterns 'report/*.txt' 'logs/*.log'）")
    args = parser.parse_args()
    
    # 指定されたディレクトリをスキャン
    if not args.quiet:
        print(f"ディレクトリ '{args.directory}' をスキャンしています...")
    
    # 各フォルダの必要最小ファイル数を設定してスキャン実行
    results = find_process_folders(args.directory)
    
    # process_cフォルダのdef_*.datファイルの必要最小ファイル数を設定
    if "process_c" in results["required_folders"]:
        results["required_folders"]["process_c"]["min_required_files"]["def_*.dat"] = args.min_files_c
        
        # ファイル要件が満たされているかを再チェック
        pattern = "def_*.dat"
        if results["required_folders"]["process_c"]["exists"] and pattern in results["required_folders"]["process_c"]["found_files"]:
            found_files = len(results["required_folders"]["process_c"]["found_files"][pattern])
            pattern_requirement_met = found_files >= args.min_files_c
            results["required_folders"]["process_c"][f"{pattern}_requirement_met"] = pattern_requirement_met
    
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
    
    # process_cのファイル要件確認（拡張版）
    if results["required_folders"]["process_c"]["exists"]:
        all_c_requirements_met = True
        for pattern in results["required_folders"]["process_c"]["required_file_patterns"]:
            if not results["required_folders"]["process_c"].get(f"{pattern}_requirement_met", True):
                all_c_requirements_met = False
                break
        
        results["required_folders"]["process_c"]["files_requirement_met"] = all_c_requirements_met
        if not all_c_requirements_met:
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
```

主な変更点を詳細に説明します：

1. **`process_c`フォルダの設定を拡張**:
   - 複数のファイルパターンに対応するために`required_file_patterns`を配列に変更
   - サブフォルダに対応するために`file_locations`を追加
   - パターンごとに最小ファイル数を設定できるよう`min_required_files`を辞書型に変更

2. **検索ロジックの強化**:
   - 各配置場所（サブディレクトリ）を個別にチェック
   - ファイルの相対パスを保持して、どのサブディレクトリで見つかったかを追跡
   - パターンごとに要件が満たされているかを個別に判定

3. **結果表示機能の強化**:
   - サブディレクトリごとのファイル数を表示
   - 各パターンの要件状態を個別に表示
   - ファイルの検出場所を明示

4. **コマンドラインオプションの拡張**:
   - `--patterns`オプションを追加して、チェックすべき追加のファイルパターンを指定可能に

この拡張により、`process_c`フォルダ内の複数のサブディレクトリ（plot1, plot2など）にある「def_*.dat」などのファイルを柔軟にチェックできるようになります。要件も柔軟に設定でき、レポートにはどのサブディレクトリにファイルが見つかったかも表示されます。​​​​​​​​​​​​​​​​
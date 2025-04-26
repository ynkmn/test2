import os
import glob
import re
import argparse
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional


# 抽象基底クラス - ストラテジーパターンの基盤
class FolderChecker(ABC):
    """フォルダチェッカーの抽象基底クラス"""
    
    def __init__(self, directory: str):
        self.directory = directory
        self.result: Dict[str, Any] = {}
    
    @abstractmethod
    def check(self) -> Dict[str, Any]:
        """フォルダとファイルのチェックを実行し、結果を返す"""
        pass


# 具象クラス - Process_a フォルダのチェッカー
class ProcessAChecker(FolderChecker):
    """process_a* フォルダのチェックを担当するクラス"""
    
    def check(self) -> Dict[str, Any]:
        """process_a* フォルダとそのファイルをチェック"""
        self.result = {
            "exists": False,
            "folder_pattern": "process_a*",
            "matching_folders": [],
            "required_file_patterns": ["*.01d", "*.02d"],
            "found_files": {"*.01d": [], "*.02d": []},
            "files_exist": False
        }
        
        # すべてのプロセスフォルダを取得
        entries = os.listdir(self.directory)
        process_folders = [entry for entry in entries 
                         if os.path.isdir(os.path.join(self.directory, entry)) 
                         and entry.startswith("process_")]
        
        # process_a* パターンに一致するフォルダを検索
        process_a_folders = [folder for folder in process_folders 
                           if glob.fnmatch.fnmatch(folder, "process_a*")]
        
        if process_a_folders:
            self.result["exists"] = True
            self.result["matching_folders"] = process_a_folders
            
            # 各 process_a* フォルダ内の必須ファイルをチェック
            files_01d = []
            files_02d = []
            
            for folder in process_a_folders:
                # *.01d ファイルのチェック
                pattern_01d = os.path.join(self.directory, folder, "*.01d")
                matching_files_01d = glob.glob(pattern_01d)
                files_01d.extend([os.path.basename(f) for f in matching_files_01d])
                
                # *.02d ファイルのチェック
                pattern_02d = os.path.join(self.directory, folder, "*.02d")
                matching_files_02d = glob.glob(pattern_02d)
                files_02d.extend([os.path.basename(f) for f in matching_files_02d])
            
            self.result["found_files"]["*.01d"] = files_01d
            self.result["found_files"]["*.02d"] = files_02d
            
            # 両方のパターンのファイルが見つかったかチェック
            self.result["files_exist"] = (len(files_01d) > 0 and len(files_02d) > 0)
            
        return self.result


# 具象クラス - Process_s フォルダのチェッカー
class ProcessSChecker(FolderChecker):
    """process_s フォルダのチェックを担当するクラス"""
    
    def __init__(self, directory: str, min_required_files: int = 2):
        super().__init__(directory)
        self.min_required_files = min_required_files
    
    def check(self) -> Dict[str, Any]:
        """process_s フォルダとそのファイルをチェック"""
        self.result = {
            "exists": False,
            "required_file_pattern": "plot_*ms.txt",
            "found_files": [],
            "min_required_files": self.min_required_files,
            "files_requirement_met": False
        }
        
        # process_s フォルダが存在するかチェック
        process_s_path = os.path.join(self.directory, "process_s")
        if os.path.exists(process_s_path) and os.path.isdir(process_s_path):
            self.result["exists"] = True
            
            # plot_*ms.txt パターンのファイルをチェック
            pattern = os.path.join(process_s_path, "plot_*ms.txt")
            matching_files = glob.glob(pattern)
            
            # ファイル名をリストに保存
            self.result["found_files"] = [os.path.basename(f) for f in matching_files]
            
            # 必要な数のファイルが存在するかチェック
            if len(matching_files) >= self.min_required_files:
                self.result["files_requirement_met"] = True
                
            # ミリ秒値を抽出して分析
            ms_values = []
            for file_path in matching_files:
                file_name = os.path.basename(file_path)
                match = re.search(r'plot_(\d+)ms\.txt', file_name)
                if match:
                    ms_values.append(int(match.group(1)))
            
            if ms_values:
                self.result["min_ms"] = min(ms_values)
                self.result["max_ms"] = max(ms_values)
                self.result["ms_count"] = len(ms_values)
        
        return self.result


# 具象クラス - Process_c フォルダのチェッカー
class ProcessCChecker(FolderChecker):
    """process_c フォルダのチェックを担当するクラス"""
    
    def __init__(self, directory: str, min_required_files: int = 100):
        super().__init__(directory)
        self.min_required_files = min_required_files
    
    def check(self) -> Dict[str, Any]:
        """process_c フォルダとそのファイルをチェック"""
        self.result = {
            "exists": False,
            "required_files_pattern": "def_*.dat",
            "min_required_files": self.min_required_files,
            "found_files": 0,
            "files_requirement_met": False,
            "file_list": []
        }
        
        # process_c フォルダが存在するかチェック
        process_c_path = os.path.join(self.directory, "process_c")
        if os.path.exists(process_c_path) and os.path.isdir(process_c_path):
            self.result["exists"] = True
            
            # def_*.dat パターンのファイルをチェック
            pattern = os.path.join(process_c_path, "def_*.dat")
            matching_files = glob.glob(pattern)
            
            # ファイル名をリストに保存
            self.result["file_list"] = [os.path.basename(f) for f in matching_files]
            self.result["found_files"] = len(matching_files)
            
            # 必要な数のファイルが存在するかチェック
            if len(matching_files) >= self.min_required_files:
                self.result["files_requirement_met"] = True
            
            # 実際のファイル番号の範囲を分析
            numbers = []
            for file_path in matching_files:
                file_name = os.path.basename(file_path)
                match = re.search(r'def_(\d+)\.dat', file_name)
                if match:
                    numbers.append(int(match.group(1)))
            
            if numbers:
                self.result["min_number"] = min(numbers)
                self.result["max_number"] = max(numbers)
                self.result["total_unique_numbers"] = len(set(numbers))
        
        return self.result


# コンポジットパターン - 複数のチェッカーを組み合わせて使用
class CompositeFolderChecker:
    """複数のチェッカーを組み合わせて総合的なチェックを行うクラス"""
    
    def __init__(self, directory: str):
        self.directory = directory
        self.checkers: Dict[str, FolderChecker] = {}
        self.result: Dict[str, Any] = {
            "process_folders": [],
            "required_folders": {},
            "status": {
                "total_process_folders": 0,
                "required_folders_exist": False,
                "required_files_exist": False,
                "all_requirements_met": False
            }
        }
    
    def add_checker(self, name: str, checker: FolderChecker) -> None:
        """チェッカーを追加"""
        self.checkers[name] = checker
    
    def check(self) -> Dict[str, Any]:
        """全てのチェッカーを実行して結果をまとめる"""
        try:
            # ディレクトリが存在するか確認
            if not os.path.exists(self.directory) or not os.path.isdir(self.directory):
                raise FileNotFoundError(f"指定されたディレクトリが見つかりません: {self.directory}")
            
            # ディレクトリ内のすべてのプロセスフォルダを検索
            entries = os.listdir(self.directory)
            process_folders = [entry for entry in entries 
                             if os.path.isdir(os.path.join(self.directory, entry)) 
                             and entry.startswith("process_")]
            
            self.result["process_folders"] = process_folders
            self.result["status"]["total_process_folders"] = len(process_folders)
            
            # 各チェッカーを実行
            for name, checker in self.checkers.items():
                self.result["required_folders"][name] = checker.check()
            
            # 全体のステータスを更新
            self._update_overall_status()
            
        except Exception as e:
            self.result["error"] = str(e)
        
        return self.result
    
    def _update_overall_status(self) -> None:
        """全体のステータスを更新"""
        # 全ての必須フォルダが存在するか確認
        req_folders_exist = all(info["exists"] for info in self.result["required_folders"].values())
        self.result["status"]["required_folders_exist"] = req_folders_exist
        
        # ファイル要件を確認
        files_requirements_met = True
        
        # process_aのファイル要件確認
        if not self.result["required_folders"]["process_a"]["files_exist"]:
            files_requirements_met = False
        
        # process_sのファイル要件確認
        if not self.result["required_folders"]["process_s"]["files_requirement_met"]:
            files_requirements_met = False
        
        # process_cのファイル要件確認
        if not self.result["required_folders"]["process_c"]["files_requirement_met"]:
            files_requirements_met = False
        
        self.result["status"]["required_files_exist"] = files_requirements_met
        self.result["status"]["all_requirements_met"] = req_folders_exist and files_requirements_met


# ファクトリークラス - チェッカーの生成を担当
class FolderCheckerFactory:
    """チェッカーを生成するファクトリークラス"""
    
    @staticmethod
    def create_checkers(directory: str, min_files_s: int = 2, min_files_c: int = 100) -> CompositeFolderChecker:
        """指定されたディレクトリ用のコンポジットチェッカーを生成"""
        composite_checker = CompositeFolderChecker(directory)
        
        # 各タイプのチェッカーを作成して追加
        composite_checker.add_checker("process_a", ProcessAChecker(directory))
        composite_checker.add_checker("process_s", ProcessSChecker(directory, min_files_s))
        composite_checker.add_checker("process_c", ProcessCChecker(directory, min_files_c))
        
        return composite_checker


# オブザーバーパターン - 結果の通知と表示
class ResultObserver(ABC):
    """結果オブザーバーの抽象基底クラス"""
    
    @abstractmethod
    def update(self, results: Dict[str, Any]) -> None:
        """結果が更新されたときに呼び出されるメソッド"""
        pass


# 詳細表示用のオブザーバー
class DetailedResultPrinter(ResultObserver):
    """チェック結果を詳細に表示するオブザーバー"""
    
    def update(self, results: Dict[str, Any]) -> None:
        """結果を詳細に表示"""
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


# 簡易表示用のオブザーバー
class SummaryResultPrinter(ResultObserver):
    """チェック結果を簡潔に表示するオブザーバー"""
    
    def update(self, results: Dict[str, Any]) -> None:
        """結果の要約を表示"""
        if "error" in results:
            print(f"エラー: {results['error']}")
            return
        
        status = "成功" if results["status"]["all_requirements_met"] else "失敗"
        print(f"チェック結果: {status}")


# メイン関数
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
    
    # 適切なオブザーバーを選択
    observer: ResultObserver
    if args.quiet:
        observer = SummaryResultPrinter()
    else:
        observer = DetailedResultPrinter()
        print(f"ディレクトリ '{args.directory}' をスキャンしています...")
    
    # ファクトリーを使用してチェッカーを作成
    composite_checker = FolderCheckerFactory.create_checkers(
        args.directory, 
        args.min_files_s, 
        args.min_files_c
    )
    
    # チェックを実行して結果を取得
    results = composite_checker.check()
    
    # オブザーバーに結果を通知
    observer.update(results)
    
    # 結果を返す（他のスクリプトから呼び出される場合に便利）
    return results


if __name__ == "__main__":
    main()
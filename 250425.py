import os
import glob
import re
import argparse
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional


class FolderChecker(ABC):
    """フォルダの要件チェックを行う抽象基底クラス"""
    
    def __init__(self, base_directory: str):
        self.base_directory = base_directory
        self.exists = False
        self.result_data = {}
    
    @abstractmethod
    def check(self) -> Dict[str, Any]:
        """フォルダチェックを実行して結果を返す"""
        pass
    
    def get_status(self) -> bool:
        """すべての要件を満たしているかどうかを返す"""
        pass


class ProcessAChecker(FolderChecker):
    """process_a* パターンのフォルダチェック用クラス"""
    
    def __init__(self, base_directory: str):
        super().__init__(base_directory)
        self.folder_pattern = "process_a*"
        self.matching_folders = []
        self.required_file_patterns = ["*.01d", "*.02d"]
        self.found_files = {"*.01d": [], "*.02d": []}
        self.files_exist = False
    
    def check(self) -> Dict[str, Any]:
        # プロセスフォルダのリストから pattern_a* に一致するものを検索
        process_folders = self._get_process_folders()
        self.matching_folders = [folder for folder in process_folders 
                                if glob.fnmatch.fnmatch(folder, self.folder_pattern)]
        
        self.exists = len(self.matching_folders) > 0
        
        if self.exists:
            # 各 process_a* フォルダ内の必須ファイルをチェック
            for pattern in self.required_file_patterns:
                self.found_files[pattern] = []
                
                for folder in self.matching_folders:
                    pattern_path = os.path.join(self.base_directory, folder, pattern)
                    matching_files = glob.glob(pattern_path)
                    self.found_files[pattern].extend([os.path.basename(f) for f in matching_files])
            
            # 両方のパターンのファイルが見つかったかチェック
            self.files_exist = all(len(files) > 0 for files in self.found_files.values())
        
        # 結果を辞書形式で返す
        self.result_data = {
            "exists": self.exists,
            "folder_pattern": self.folder_pattern,
            "matching_folders": self.matching_folders,
            "required_file_patterns": self.required_file_patterns,
            "found_files": self.found_files,
            "files_exist": self.files_exist
        }
        
        return self.result_data
    
    def get_status(self) -> bool:
        return self.exists and self.files_exist
    
    def _get_process_folders(self) -> List[str]:
        """base_directory内のprocess_で始まるフォルダを返す"""
        try:
            entries = os.listdir(self.base_directory)
            return [entry for entry in entries 
                   if os.path.isdir(os.path.join(self.base_directory, entry)) 
                   and entry.startswith("process_")]
        except Exception:
            return []


class ProcessSChecker(FolderChecker):
    """process_s フォルダチェック用クラス"""
    
    def __init__(self, base_directory: str, min_required_files: int = 2):
        super().__init__(base_directory)
        self.folder_name = "process_s"
        self.required_file_pattern = "plot_*ms.txt"
        self.found_files = []
        self.min_required_files = min_required_files
        self.files_requirement_met = False
        self.metadata = {}
    
    def check(self) -> Dict[str, Any]:
        # フォルダの存在チェック
        folder_path = os.path.join(self.base_directory, self.folder_name)
        self.exists = os.path.exists(folder_path) and os.path.isdir(folder_path)
        
        if self.exists:
            # 必要なファイルパターンをチェック
            pattern = os.path.join(folder_path, self.required_file_pattern)
            matching_files = glob.glob(pattern)
            
            # ファイル名をリストに保存
            self.found_files = [os.path.basename(f) for f in matching_files]
            
            # 必要な数のファイルが存在するかチェック
            self.files_requirement_met = len(matching_files) >= self.min_required_files
            
            # ミリ秒値を抽出して分析
            ms_values = []
            for file_path in matching_files:
                file_name = os.path.basename(file_path)
                match = re.search(r'plot_(\d+)ms\.txt', file_name)
                if match:
                    ms_values.append(int(match.group(1)))
            
            if ms_values:
                self.metadata = {
                    "min_ms": min(ms_values),
                    "max_ms": max(ms_values),
                    "ms_count": len(ms_values)
                }
        
        # 結果を辞書形式で返す
        self.result_data = {
            "exists": self.exists,
            "required_file_pattern": self.required_file_pattern,
            "found_files": self.found_files,
            "min_required_files": self.min_required_files,
            "files_requirement_met": self.files_requirement_met
        }
        
        # メタデータを追加
        if self.metadata:
            self.result_data.update(self.metadata)
        
        return self.result_data
    
    def get_status(self) -> bool:
        return self.exists and self.files_requirement_met


class ProcessCChecker(FolderChecker):
    """process_c フォルダチェック用クラス"""
    
    def __init__(self, base_directory: str, min_required_files: int = 100):
        super().__init__(base_directory)
        self.folder_name = "process_c"
        self.required_files_pattern = "def_*.dat"
        self.min_required_files = min_required_files
        self.found_files = 0
        self.files_requirement_met = False
        self.file_list = []
        self.metadata = {}
    
    def check(self) -> Dict[str, Any]:
        # フォルダの存在チェック
        folder_path = os.path.join(self.base_directory, self.folder_name)
        self.exists = os.path.exists(folder_path) and os.path.isdir(folder_path)
        
        if self.exists:
            # 必要なファイルパターンをチェック
            pattern = os.path.join(folder_path, self.required_files_pattern)
            matching_files = glob.glob(pattern)
            
            # ファイル名をリストに保存
            self.file_list = [os.path.basename(f) for f in matching_files]
            self.found_files = len(matching_files)
            
            # 必要な数のファイルが存在するかチェック
            self.files_requirement_met = self.found_files >= self.min_required_files
            
            # ファイル番号の範囲を分析
            numbers = []
            for file_path in matching_files:
                file_name = os.path.basename(file_path)
                match = re.search(r'def_(\d+)\.dat', file_name)
                if match:
                    numbers.append(int(match.group(1)))
            
            if numbers:
                self.metadata = {
                    "min_number": min(numbers),
                    "max_number": max(numbers),
                    "total_unique_numbers": len(set(numbers))
                }
        
        # 結果を辞書形式で返す
        self.result_data = {
            "exists": self.exists,
            "required_files_pattern": self.required_files_pattern,
            "min_required_files": self.min_required_files,
            "found_files": self.found_files,
            "files_requirement_met": self.files_requirement_met,
            "file_list": self.file_list
        }
        
        # メタデータを追加
        if self.metadata:
            self.result_data.update(self.metadata)
        
        return self.result_data
    
    def get_status(self) -> bool:
        return self.exists and self.files_requirement_met


class ProcessFolderFacade:
    """フォルダチェックを管理するファサードクラス"""
    
    def __init__(self, directory: str, min_files_c: int = 100, min_files_s: int = 2):
        self.directory = directory
        self.process_a_checker = ProcessAChecker(directory)
        self.process_s_checker = ProcessSChecker(directory, min_files_s)
        self.process_c_checker = ProcessCChecker(directory, min_files_c)
        
        # 個別のチェッカー
        self.checkers = {
            "process_a": self.process_a_checker,
            "process_s": self.process_s_checker,
            "process_c": self.process_c_checker
        }
        
        # 結果を格納する辞書
        self.result = {
            "process_folders": [],
            "required_folders": {},
            "status": {
                "total_process_folders": 0,
                "required_folders_exist": False,
                "required_files_exist": False,
                "all_requirements_met": False
            }
        }
    
    def run_check(self) -> Dict[str, Any]:
        """すべてのチェックを実行して結果を返す"""
        try:
            # ディレクトリが存在するか確認
            if not os.path.exists(self.directory) or not os.path.isdir(self.directory):
                raise FileNotFoundError(f"指定されたディレクトリが見つかりません: {self.directory}")
            
            # すべてのprocess_フォルダを収集
            all_process_folders = self._get_all_process_folders()
            self.result["process_folders"] = all_process_folders
            self.result["status"]["total_process_folders"] = len(all_process_folders)
            
            # 各チェッカーを実行
            self.result["required_folders"] = {}
            for name, checker in self.checkers.items():
                self.result["required_folders"][name] = checker.check()
            
            # 全体のステータスを更新
            self._update_overall_status()
            
        except Exception as e:
            self.result["error"] = str(e)
        
        return self.result
    
    def _get_all_process_folders(self) -> List[str]:
        """ディレクトリ内のすべてのprocess_フォルダを返す"""
        try:
            entries = os.listdir(self.directory)
            return [entry for entry in entries 
                   if os.path.isdir(os.path.join(self.directory, entry)) 
                   and entry.startswith("process_")]
        except Exception:
            return []
    
    def _update_overall_status(self) -> None:
        """全体のステータスを更新する"""
        # すべての必須フォルダが存在するか確認
        req_folders_exist = all(checker.exists for checker in self.checkers.values())
        self.result["status"]["required_folders_exist"] = req_folders_exist
        
        # すべてのファイル要件が満たされているか確認
        files_requirements_met = all(checker.get_status() for checker in self.checkers.values())
        self.result["status"]["required_files_exist"] = files_requirements_met
        
        # すべての要件が満たされているか確認
        self.result["status"]["all_requirements_met"] = req_folders_exist and files_requirements_met


class ResultFormatter:
    """検査結果のフォーマットを担当するクラス"""
    
    @staticmethod
    def format_results(results: Dict[str, Any], quiet: bool = False) -> str:
        """結果を整形された文字列として返す"""
        if quiet:
            status = "成功" if results["status"]["all_requirements_met"] else "失敗"
            return f"チェック結果: {status}"
        
        output = []
        output.append("\n===== フォルダチェック結果 =====")
        
        # エラーがあれば表示
        if "error" in results:
            output.append(f"エラー: {results['error']}")
            return "\n".join(output)
        
        # 必須フォルダと必須ファイルのステータス表示
        output.append("\n必須フォルダとファイルのステータス:")
        
        # --- process_a* フォルダのステータス ---
        process_a = results["required_folders"]["process_a"]
        folder_status = "✓ 存在します" if process_a["exists"] else "✗ 見つかりません"
        output.append(f"  process_a* パターン: {folder_status}")
        
        if process_a["exists"]:
            # マッチしたフォルダを表示
            matching_folders = process_a["matching_folders"]
            output.append(f"    - マッチしたフォルダ: {', '.join(matching_folders)}")
            
            # ファイルパターンごとに結果を表示
            for pattern in ["*.01d", "*.02d"]:
                files = process_a["found_files"][pattern]
                file_status = "✓ 存在します" if files else "✗ 見つかりません"
                file_count = len(files)
                output.append(f"    - {pattern}: {file_status} ({file_count}ファイル)")
                
                # サンプルファイルを表示
                if files:
                    samples = files[:3]
                    output.append(f"      サンプル: {', '.join(samples)}" + 
                          (" ..." if len(files) > 3 else ""))
        
        # --- process_s フォルダのステータス ---
        process_s = results["required_folders"]["process_s"]
        folder_status = "✓ 存在します" if process_s["exists"] else "✗ 見つかりません"
        output.append(f"  process_s: {folder_status}")
        
        if process_s["exists"]:
            pattern = process_s["required_file_pattern"]
            files = process_s["found_files"]
            file_count = len(files)
            min_required = process_s["min_required_files"]
            
            files_status = "✓ 必要数のファイルが存在します" if process_s["files_requirement_met"] else f"✗ 必要なファイル数が不足しています ({file_count}/{min_required}必要)"
            output.append(f"    - {pattern}: {files_status}")
            
            if file_count > 0:
                output.append(f"      - 検出されたファイル数: {file_count}")
                if "min_ms" in process_s and "max_ms" in process_s:
                    output.append(f"      - ミリ秒値の範囲: {process_s['min_ms']}ms～{process_s['max_ms']}ms")
                
                # サンプルファイルを表示
                samples = files[:3]
                output.append(f"      - サンプルファイル: {', '.join(samples)}" + 
                      (" ..." if file_count > 3 else ""))
        
        # --- process_c フォルダのステータス ---
        process_c = results["required_folders"]["process_c"]
        folder_status = "✓ 存在します" if process_c["exists"] else "✗ 見つかりません"
        output.append(f"  process_c: {folder_status}")
        
        if process_c["exists"]:
            files_status = "✓ 必要数のファイルが存在します" if process_c["files_requirement_met"] else f"✗ 必要なファイル数が不足しています ({process_c['found_files']}/{process_c['min_required_files']}必要)"
            output.append(f"    - {process_c['required_files_pattern']}: {files_status}")
            
            if process_c["found_files"] > 0:
                output.append(f"      - 検出されたファイル数: {process_c['found_files']}")
                if "min_number" in process_c and "max_number" in process_c:
                    output.append(f"      - ファイル番号の範囲: {process_c['min_number']}～{process_c['max_number']}")
                if "total_unique_numbers" in process_c:
                    output.append(f"      - ユニークなファイル番号の数: {process_c['total_unique_numbers']}")
                
                # 最初の3ファイルのサンプルを表示
                file_samples = process_c["file_list"][:3]
                if file_samples:
                    output.append(f"      - サンプルファイル: {', '.join(file_samples)}" + 
                          (" ..." if len(process_c["file_list"]) > 3 else ""))
        
        # 全体のステータス表示
        output.append("\n全体の状況:")
        output.append(f"  確認されたprocess_フォルダの総数: {results['status']['total_process_folders']}")
        
        if results["status"]["all_requirements_met"]:
            output.append("  ✓ すべての要件を満たしています！グラフ作成に進めます。")
        else:
            output.append("  ✗ すべての要件を満たしていません。以下の問題を修正してください:")
            
            if not results["status"]["required_folders_exist"]:
                output.append("    - 必須フォルダ(process_a, process_s, process_c)が一部または全部見つかりません")
            
            if not results["status"]["required_files_exist"]:
                output.append("    - 必須ファイル要件が満たされていません:")
                
                # process_a のファイル問題を表示
                process_a = results["required_folders"]["process_a"]
                if process_a["exists"] and not process_a["files_exist"]:
                    missing_patterns = []
                    for pattern in ["*.01d", "*.02d"]:
                        if not process_a["found_files"][pattern]:
                            missing_patterns.append(pattern)
                    if missing_patterns:
                        output.append(f"      - process_a*フォルダ内の {', '.join(missing_patterns)} パターンのファイルが見つかりません")
                
                # process_s のファイル問題を表示
                process_s = results["required_folders"]["process_s"]
                if process_s["exists"] and not process_s["files_requirement_met"]:
                    found = len(process_s["found_files"])
                    needed = process_s["min_required_files"]
                    output.append(f"      - process_s内のplot_*ms.txtファイルが不足しています ({found}/{needed}必要)")
                
                # process_c のファイル問題を表示
                process_c = results["required_folders"]["process_c"]
                if process_c["exists"] and not process_c["files_requirement_met"]:
                    found = process_c["found_files"]
                    needed = process_c["min_required_files"]
                    output.append(f"      - process_c内のdef_*.datファイルが不足しています ({found}/{needed}必要)")
        
        # すべてのprocess_フォルダのリスト表示
        output.append("\n検出されたすべてのprocess_フォルダ:")
        if results["process_folders"]:
            for folder in results["process_folders"]:
                output.append(f"  - {folder}")
        else:
            output.append("  見つかりませんでした")
        
        return "\n".join(output)


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
    
    # ファサードを使用してチェックを実行
    checker = ProcessFolderFacade(args.directory, args.min_files_c, args.min_files_s)
    results = checker.run_check()
    
    # 結果をフォーマット
    formatted_results = ResultFormatter.format_results(results, args.quiet)
    print(formatted_results)
    
    return results


if __name__ == "__main__":
    main()
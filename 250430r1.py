import os
import glob
import re
import argparse
import pickle
import hashlib
from datetime import datetime
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple, Set


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
    
    def pickle_files(self, output_dir: str = "pickled_data") -> Dict[str, Any]:
        """ファイルをpickle化する（サブクラスでオーバーライド）"""
        return {"pickled": False, "reason": "このチェッカーはpickle機能を実装していません"}


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
                files_01d.extend(matching_files_01d)  # フルパスを保存
                
                # *.02d ファイルのチェック
                pattern_02d = os.path.join(self.directory, folder, "*.02d")
                matching_files_02d = glob.glob(pattern_02d)
                files_02d.extend(matching_files_02d)  # フルパスを保存
            
            # 結果にファイル名のみを保存（表示用）
            self.result["found_files"]["*.01d"] = [os.path.basename(f) for f in files_01d]
            self.result["found_files"]["*.02d"] = [os.path.basename(f) for f in files_02d]
            
            # フルパスのリストも保存（pickle用）
            self.result["full_paths"] = {"*.01d": files_01d, "*.02d": files_02d}
            
            # 両方のパターンのファイルが見つかったかチェック
            self.result["files_exist"] = (len(files_01d) > 0 and len(files_02d) > 0)
            
        return self.result
    
    def pickle_files(self, output_dir: str = "pickled_data") -> Dict[str, Any]:
        """process_aフォルダ内のファイルをpickle化する"""
        pickle_result = {
            "pickled": False,
            "patterns_processed": {},
            "output_dir": output_dir
        }
        
        # チェックが実行されていなければ実行
        if not self.result:
            self.check()
        
        # 出力ディレクトリが存在しなければ作成
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 各ファイルパターンに対してpickle化
        if "full_paths" in self.result:
            pickle_result["patterns_processed"] = {}
            
            for pattern, file_paths in self.result["full_paths"].items():
                if not file_paths:
                    pickle_result["patterns_processed"][pattern] = {
                        "success": False,
                        "reason": "マッチするファイルがありません",
                        "file_count": 0
                    }
                    continue
                
                # パターンに基づいたpickleファイル名を生成
                pickle_filename = f"process_a_{pattern.replace('*.', '').replace('*', '')}.pkl"
                pickle_path = os.path.join(output_dir, pickle_filename)
                
                # pickle化の必要性を確認
                if os.path.exists(pickle_path):
                    pickle_result["patterns_processed"][pattern] = {
                        "success": True,
                        "reason": "既にpickleファイルが存在します",
                        "file_count": len(file_paths),
                        "pickle_path": pickle_path,
                        "skipped": True
                    }
                    continue
                
                try:
                    # ファイルの内容を読み込み
                    data = {}
                    for file_path in file_paths:
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                file_data = f.read()
                                data[os.path.basename(file_path)] = file_data
                        except Exception as e:
                            print(f"警告: ファイル読み込みエラー {file_path}: {str(e)}")
                    
                    # pickle化して保存
                    with open(pickle_path, 'wb') as f:
                        pickle.dump(data, f)
                    
                    pickle_result["patterns_processed"][pattern] = {
                        "success": True,
                        "file_count": len(file_paths),
                        "pickle_path": pickle_path,
                        "skipped": False
                    }
                    
                except Exception as e:
                    pickle_result["patterns_processed"][pattern] = {
                        "success": False,
                        "reason": f"エラー: {str(e)}",
                        "file_count": len(file_paths)
                    }
            
            # 少なくとも1つのパターンが成功したら全体を成功とする
            success_count = sum(1 for result in pickle_result["patterns_processed"].values() if result["success"])
            pickle_result["pickled"] = success_count > 0
            
        return pickle_result


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
            
            # フルパスを保存
            self.result["full_paths"] = matching_files
            
            # ファイル名のみをリストに保存（表示用）
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
    
    def pickle_files(self, output_dir: str = "pickled_data") -> Dict[str, Any]:
        """process_sフォルダ内のファイルをpickle化する"""
        pickle_result = {
            "pickled": False,
            "pattern": "plot_*ms.txt",
            "output_dir": output_dir
        }
        
        # チェックが実行されていなければ実行
        if not self.result:
            self.check()
        
        # 出力ディレクトリが存在しなければ作成
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # ファイルが見つからない場合
        if not self.result["exists"] or not self.result.get("full_paths"):
            pickle_result["reason"] = "マッチするファイルがありません"
            return pickle_result
        
        # pickle化するファイルパスのリスト
        file_paths = self.result.get("full_paths", [])
        
        # パターンに基づいたpickleファイル名を生成
        pickle_filename = "process_s_plot_ms.pkl"
        pickle_path = os.path.join(output_dir, pickle_filename)
        
        # pickle化の必要性を確認
        if os.path.exists(pickle_path):
            pickle_result.update({
                "pickled": True,
                "reason": "既にpickleファイルが存在します",
                "file_count": len(file_paths),
                "pickle_path": pickle_path,
                "skipped": True
            })
            return pickle_result
        
        try:
            # ファイルの内容を読み込む
            data = {}
            for file_path in file_paths:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        file_data = f.read()
                        data[os.path.basename(file_path)] = file_data
                except Exception as e:
                    print(f"警告: ファイル読み込みエラー {file_path}: {str(e)}")
            
            # pickle化して保存
            with open(pickle_path, 'wb') as f:
                pickle.dump(data, f)
            
            pickle_result.update({
                "pickled": True,
                "file_count": len(file_paths),
                "pickle_path": pickle_path,
                "skipped": False
            })
            
        except Exception as e:
            pickle_result.update({
                "reason": f"エラー: {str(e)}",
                "file_count": len(file_paths)
            })
        
        return pickle_result


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
            
            # フルパスを保存
            self.result["full_paths"] = matching_files
            
            # ファイル名をリストに保存（表示用）
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
    
    def pickle_files(self, output_dir: str = "pickled_data") -> Dict[str, Any]:
        """process_cフォルダ内のファイルをpickle化する"""
        pickle_result = {
            "pickled": False,
            "pattern": "def_*.dat",
            "output_dir": output_dir
        }
        
        # チェックが実行されていなければ実行
        if not self.result:
            self.check()
        
        # 出力ディレクトリが存在しなければ作成
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # ファイルが見つからない場合
        if not self.result["exists"] or not self.result.get("full_paths"):
            pickle_result["reason"] = "マッチするファイルがありません"
            return pickle_result
        
        # pickle化するファイルパスのリスト
        file_paths = self.result.get("full_paths", [])
        
        # パターンに基づいたpickleファイル名を生成
        pickle_filename = "process_c_def.pkl"
        pickle_path = os.path.join(output_dir, pickle_filename)
        
        # pickle化の必要性を確認
        if os.path.exists(pickle_path):
            pickle_result.update({
                "pickled": True,
                "reason": "既にpickleファイルが存在します",
                "file_count": len(file_paths),
                "pickle_path": pickle_path,
                "skipped": True
            })
            return pickle_result
        
        try:
            # ファイルが多い場合を考慮して、バッチ処理
            data = {}
            batch_size = 500  # 一度に処理するファイル数
            
            for i in range(0, len(file_paths), batch_size):
                batch = file_paths[i:i+batch_size]
                for file_path in batch:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            file_data = f.read()
                            data[os.path.basename(file_path)] = file_data
                    except Exception as e:
                        print(f"警告: ファイル読み込みエラー {file_path}: {str(e)}")
            
            # pickle化して保存
            with open(pickle_path, 'wb') as f:
                pickle.dump(data, f)
            
            pickle_result.update({
                "pickled": True,
                "file_count": len(file_paths),
                "pickle_path": pickle_path,
                "skipped": False
            })
            
        except Exception as e:
            pickle_result.update({
                "reason": f"エラー: {str(e)}",
                "file_count": len(file_paths)
            })
        
        return pickle_result


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
    
    def pickle_all_files(self, output_dir: str = "pickled_data") -> Dict[str, Any]:
        """すべてのチェッカーに対してpickle化を実行"""
        pickle_results = {}
        
        # チェックが実行されていなければ実行
        if not self.result or "required_folders" not in self.result:
            self.check()
        
        # エラーがあれば中止
        if "error" in self.result:
            return {"error": self.result["error"]}
        
        # 各チェッカーに対してpickle化を実行
        for name, checker in self.checkers.items():
            pickle_results[name] = checker.pickle_files(output_dir)
        
        return pickle_results
    
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


# pickle結果表示用のオブザーバー
class PickleResultPrinter(ResultObserver):
    """pickle化結果を表示するオブザーバー"""
    
    def update(self, results: Dict[str, Any]) -> None:
        """pickle化結果を表示"""
        print("\n===== Pickle化の結果 =====")
        
        if "error" in results:
            print(f"エラー: {results['error']}")
            return
        
        for folder_name, pickle_result in results.items():
            print(f"\n> {folder_name} フォルダのpickle化結果:")
            
            if not pickle_result.get("pickled", False):
                reason = pickle_result.get("reason", "不明なエラー")
                print(f"  - ステータス: 失敗 ({reason})")
                continue
            
            # Process_aの場合
            if folder_name == "process_a" and "patterns_processed" in pickle_result:
                for pattern, pattern_result in pickle_result["patterns_processed"].items():
                    if pattern_result.get("success", False):
                        status = "スキップ" if pattern_result.get("skipped", False) else "成功"
                        print(f"  - {pattern}: {status} ({pattern_result.get('file_count', 0)} ファイル)")
                        if "pickle_path" in pattern_result:
                            print(f"    pickle保存先: {pattern_result['pickle_path']}")
                    else:
                        reason = pattern_result.get("reason", "不明なエラー")
                        print(f"  - {pattern}: 失敗 ({reason})")
            else:
                # その他のフォルダ
                status = "スキップ" if pickle_result.get("skipped", False) else "成功"
                print(f"  - ステータス: {status}")
                print(f"  - パターン: {pickle_result.get('pattern', '不明')}")
                print(f"  - 処理ファイル数: {pickle_result.get('file_count', 0)}")
                if "pickle_path" in pickle_result:
                    print(f"  - pickle保存先: {pickle_result['pickle_path']}")


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
            files_status = "✓
import os
import glob
import re
import argparse
import pickle
import hashlib
import multiprocessing
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
    
    def pickle_files(self, output_dir: str = "pickled_data", use_multiprocessing: bool = False, max_workers: int = None) -> Dict[str, Any]:
        """ファイルをpickle化する（サブクラスでオーバーライド）"""
        return {"pickled": False, "reason": "このチェッカーはpickle機能を実装していません"}
    
    def _split_into_chunks(self, file_paths: List[str], num_chunks: int) -> List[List[str]]:
        """ファイルパスのリストを指定された数のチャンクに分割する"""
        chunk_size = max(1, len(file_paths) // num_chunks)
        return [file_paths[i:i+chunk_size] for i in range(0, len(file_paths), chunk_size)]
    
    def _process_file_chunk(self, file_paths: List[str]) -> Dict[str, str]:
        """ファイルパスのチャンクを処理してデータを返す"""
        result = {}
        for file_path in file_paths:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_data = f.read()
                    result[os.path.basename(file_path)] = file_data
            except Exception as e:
                print(f"警告: ファイル読み込みエラー {file_path}: {str(e)}")
        return result


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
    
    def pickle_files(self, output_dir: str = "pickled_data", use_multiprocessing: bool = False, max_workers: int = None) -> Dict[str, Any]:
        """process_aフォルダ内のファイルをpickle化する
        
        Args:
            output_dir: pickle化したファイルの出力先ディレクトリ
            use_multiprocessing: マルチプロセッシングを使用するかどうか
            max_workers: 使用するワーカープロセスの最大数（Noneの場合はCPUコア数を使用）
            
        Returns:
            pickle化の結果を含む辞書
        """
        pickle_result = {
            "pickled": False,
            "patterns_processed": {},
            "output_dir": output_dir,
            "multiprocessing_used": use_multiprocessing
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
                    
                    if use_multiprocessing and len(file_paths) > 50:  # 50以上のファイルがある場合にマルチプロセッシングを使用
                        # ワーカー数を決定（指定がない場合はCPUコア数を使用）
                        if max_workers is None:
                            max_workers = multiprocessing.cpu_count()
                        
                        # タスクを分割
                        chunks = self._split_into_chunks(file_paths, max_workers)
                        
                        # 進捗状況を表示
                        print(f"{pattern}: マルチプロセッシングを使用: {max_workers}個のプロセスで{len(file_paths)}ファイルを処理します")
                        
                        # プロセスプールを作成して処理を実行
                        with multiprocessing.Pool(processes=max_workers) as pool:
                            # 各チャンクを並列処理
                            results = pool.map(self._process_file_chunk, chunks)
                            
                            # 結果を結合
                            for result in results:
                                data.update(result)
                        
                        pickle_result["patterns_processed"][pattern]["multiprocessing_details"] = {
                            "workers_used": max_workers,
                            "chunks_processed": len(chunks)
                        }
                    else:
                        # 従来の処理（シングルプロセス）
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
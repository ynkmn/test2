#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
フォルダ確認ツール
指定されたディレクトリ内の「process_」で始まるフォルダを検索し、
必須フォルダの存在と必須ファイルの有無を確認します。
"""

import os
import argparse
from typing import Dict, List, Any


def find_process_folders(directory: str) -> List[str]:
    """
    指定されたディレクトリ内で「process_」で始まるフォルダを検索します。
    
    Args:
        directory: 検索対象のディレクトリパス
        
    Returns:
        「process_」で始まるフォルダのリスト
    """
    process_folders = []
    
    # ディレクトリが存在するか確認
    if not os.path.exists(directory) or not os.path.isdir(directory):
        return process_folders
    
    # ディレクトリ内の全要素を取得
    for item in os.listdir(directory):
        item_path = os.path.join(directory, item)
        # フォルダであり、「process_」で始まるものを追加
        if os.path.isdir(item_path) and item.startswith("process_"):
            process_folders.append(item)
    
    return sorted(process_folders)


def check_required_files(directory: str, folder: str, required_files: List[str]) -> Dict[str, bool]:
    """
    指定されたフォルダ内の必須ファイルが存在するか確認します。
    
    Args:
        directory: 親ディレクトリパス
        folder: 確認対象のフォルダ名
        required_files: 必須ファイルのリスト
        
    Returns:
        各必須ファイルの存在状態を示す辞書
    """
    result = {}
    folder_path = os.path.join(directory, folder)
    
    for req_file in required_files:
        file_path = os.path.join(folder_path, req_file)
        result[req_file] = os.path.exists(file_path) and os.path.isfile(file_path)
    
    return result


def check_directory(directory: str) -> Dict[str, Any]:
    """
    指定されたディレクトリで必須フォルダの存在状態とすべてのprocess_フォルダを確認します。
    
    Args:
        directory: 検索対象のディレクトリパス
        
    Returns:
        検索結果を格納した辞書
    """
    # 検索結果を格納する辞書
    result = {
        "directory": directory,
        "directory_exists": os.path.exists(directory) and os.path.isdir(directory),
        "process_folders": [],
        "required_folders": {
            "process_a": {
                "exists": False,
                "required_files": {}
            },
            "process_s": {
                "exists": False,
                "required_files": {}
            }
        }
    }
    
    # ディレクトリが存在しない場合は早期に返す
    if not result["directory_exists"]:
        return result
    
    # すべてのprocess_フォルダを検索
    process_folders = find_process_folders(directory)
    result["process_folders"] = process_folders
    
    # 必須フォルダの存在状態を確認
    if "process_a" in process_folders:
        result["required_folders"]["process_a"]["exists"] = True
        result["required_folders"]["process_a"]["required_files"] = check_required_files(
            directory, "process_a", ["a.out"]
        )
    
    if "process_s" in process_folders:
        result["required_folders"]["process_s"]["exists"] = True
        result["required_folders"]["process_s"]["required_files"] = check_required_files(
            directory, "process_s", ["s.out"]
        )
    
    return result


def display_results(result: Dict[str, Any]) -> None:
    """
    検索結果を整形して出力します。
    
    Args:
        result: check_directory関数からの検索結果
    """
    print(f"\n===== フォルダ確認結果 =====")
    print(f"検索ディレクトリ: {result['directory']}")
    
    if not result["directory_exists"]:
        print("エラー: 指定されたディレクトリが存在しません。")
        return
    
    # process_フォルダの一覧
    print("\n[process_フォルダ一覧]")
    if result["process_folders"]:
        for folder in result["process_folders"]:
            print(f"  - {folder}")
    else:
        print("  process_で始まるフォルダは見つかりませんでした。")
    
    # 必須フォルダの状態
    print("\n[必須フォルダの状態]")
    
    # process_a フォルダ
    folder_info = result["required_folders"]["process_a"]
    print(f"  process_a: {'✓' if folder_info['exists'] else '✗'}")
    if folder_info["exists"]:
        file_info = folder_info["required_files"]
        print(f"    a.out: {'✓' if file_info.get('a.out', False) else '✗'}")
    
    # process_s フォルダ
    folder_info = result["required_folders"]["process_s"]
    print(f"  process_s: {'✓' if folder_info['exists'] else '✗'}")
    if folder_info["exists"]:
        file_info = folder_info["required_files"]
        print(f"    s.out: {'✓' if file_info.get('s.out', False) else '✗'}")
    
    # 総合結果
    all_required_exist = (
        result["required_folders"]["process_a"]["exists"] and 
        result["required_folders"]["process_a"]["required_files"].get("a.out", False) and
        result["required_folders"]["process_s"]["exists"] and 
        result["required_folders"]["process_s"]["required_files"].get("s.out", False)
    )
    
    print("\n[総合結果]")
    if all_required_exist:
        print("  すべての必須フォルダとファイルが存在します。")
    else:
        print("  一部の必須フォルダまたはファイルが見つかりません。")


def main():
    """
    メイン処理：引数を解析し、指定されたディレクトリの確認を実行します。
    """
    parser = argparse.ArgumentParser(description='指定ディレクトリ内のフォルダ確認ツール')
    parser.add_argument('directory', nargs='?', default=os.getcwd(),
                      help='検索対象のディレクトリパス (指定しない場合は現在のディレクトリ)')
    
    args = parser.parse_args()
    directory = args.directory
    
    # ディレクトリの確認を実行
    result = check_directory(directory)
    
    # 結果の表示
    display_results(result)
    
    return result


if __name__ == "__main__":
    main()
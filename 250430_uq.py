"""
原子炉反応度解析におけるインバースUQのためのPythonツール

このパッケージは、原子炉の反応度解析におけるインバース不確かさ定量化（UQ）のために
設計されたツールセットを提供します。異なる最適化アルゴリズムを柔軟に組み込み、
実験データに基づいて反応度パラメータを推定できます。
"""

import abc
import csv
import logging
import os
import time
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import optuna

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DataLoader:
    """実験データを読み込むためのクラス"""
    
    @staticmethod
    def load_csv(file_path: str, time_column: str = "time", **kwargs) -> pd.DataFrame:
        """CSVファイルからデータを読み込む

        Args:
            file_path: データファイルのパス
            time_column: 時間列の名前
            **kwargs: pandas.read_csvに渡す追加のパラメータ

        Returns:
            読み込まれたデータのDataFrame
        """
        try:
            df = pd.read_csv(file_path, **kwargs)
            if time_column not in df.columns:
                logger.warning(f"時間列 '{time_column}' がデータに存在しません")
            return df
        except Exception as e:
            logger.error(f"CSVファイルの読み込み中にエラーが発生しました: {e}")
            raise

    @staticmethod
    def load_numpy(file_path: str) -> Dict[str, np.ndarray]:
        """NumPy配列からデータを読み込む

        Args:
            file_path: npzファイルのパス

        Returns:
            読み込まれたデータの辞書
        """
        try:
            return dict(np.load(file_path))
        except Exception as e:
            logger.error(f"NumPy配列の読み込み中にエラーが発生しました: {e}")
            raise

    @staticmethod
    def load_text(file_path: str, delimiter: str = None, skiprows: int = 0) -> np.ndarray:
        """テキストファイルからデータを読み込む

        Args:
            file_path: テキストファイルのパス
            delimiter: データの区切り文字
            skiprows: スキップする行数

        Returns:
            読み込まれたデータの2D配列
        """
        try:
            return np.loadtxt(file_path, delimiter=delimiter, skiprows=skiprows)
        except Exception as e:
            logger.error(f"テキストファイルの読み込み中にエラーが発生しました: {e}")
            raise


class Parameter:
    """最適化するパラメータを表すクラス"""
    
    def __init__(self, name: str, lower_bound: float, upper_bound: float, initial_value: Optional[float] = None):
        """
        Args:
            name: パラメータの名前
            lower_bound: パラメータの下限値
            upper_bound: パラメータの上限値
            initial_value: パラメータの初期値（最適化の初期推測値）
        """
        if lower_bound >= upper_bound:
            raise ValueError(f"下限値({lower_bound})は上限値({upper_bound})より小さくなければなりません")
            
        self.name = name
        self.lower_bound = lower_bound
        self.upper_bound = upper_bound
        self.initial_value = initial_value if initial_value is not None else (lower_bound + upper_bound) / 2


class ErrorMetric(abc.ABC):
    """誤差評価のための抽象基底クラス"""
    
    @abc.abstractmethod
    def calculate(self, observed: np.ndarray, predicted: np.ndarray) -> float:
        """観測値と予測値の間の誤差を計算する

        Args:
            observed: 観測データ配列
            predicted: 予測データ配列

        Returns:
            計算された誤差値
        """
        pass


class MSE(ErrorMetric):
    """平均二乗誤差"""
    
    def calculate(self, observed: np.ndarray, predicted: np.ndarray) -> float:
        """平均二乗誤差を計算する"""
        return np.mean((observed - predicted) ** 2)


class MAE(ErrorMetric):
    """平均絶対誤差"""
    
    def calculate(self, observed: np.ndarray, predicted: np.ndarray) -> float:
        """平均絶対誤差を計算する"""
        return np.mean(np.abs(observed - predicted))


class RMSE(ErrorMetric):
    """二乗平均平方根誤差"""
    
    def calculate(self, observed: np.ndarray, predicted: np.ndarray) -> float:
        """二乗平均平方根誤差を計算する"""
        return np.sqrt(np.mean((observed - predicted) ** 2))


class ReactivityModel(abc.ABC):
    """反応度モデルの抽象基底クラス"""
    
    @abc.abstractmethod
    def calculate_reactivity(self, time: np.ndarray, params: Dict[str, float], **kwargs) -> np.ndarray:
        """パラメータを用いて時間に対する反応度を計算する

        Args:
            time: 時間点の配列
            params: パラメータの辞書 {パラメータ名: 値}
            **kwargs: 追加の入力データ（温度など）

        Returns:
            計算された反応度の配列
        """
        pass


class LinearReactivityModel(ReactivityModel):
    """線形反応度モデル (例: 全反応度 = a*燃料温度変化 + b*冷却材温度変化 + ...)"""
    
    def calculate_reactivity(self, time: np.ndarray, params: Dict[str, float], **kwargs) -> np.ndarray:
        """
        線形モデルを用いて反応度を計算する
        
        Args:
            time: 時間点の配列
            params: {
                'fuel_temp_coef': 燃料温度係数,
                'coolant_temp_coef': 冷却材温度係数,
                ...
            }
            **kwargs: {
                'fuel_temp': 燃料温度の配列,
                'coolant_temp': 冷却材温度の配列,
                ...
            }
            
        Returns:
            計算された反応度の配列
        """
        reactivity = np.zeros_like(time, dtype=float)
        
        # 燃料温度による寄与
        if 'fuel_temp_coef' in params and 'fuel_temp' in kwargs:
            reactivity += params['fuel_temp_coef'] * kwargs['fuel_temp']
            
        # 冷却材温度による寄与
        if 'coolant_temp_coef' in params and 'coolant_temp' in kwargs:
            reactivity += params['coolant_temp_coef'] * kwargs['coolant_temp']
            
        # その他のパラメータがあれば追加
        
        return reactivity


class Optimizer(abc.ABC):
    """最適化アルゴリズムのための抽象基底クラス"""
    
    @abc.abstractmethod
    def optimize(self, 
                objective_func: Callable[[Dict[str, float]], float], 
                parameters: List[Parameter], 
                **kwargs) -> Tuple[Dict[str, float], float]:
        """パラメータを最適化する

        Args:
            objective_func: 目的関数 (パラメータから評価値を計算)
            parameters: 最適化するパラメータのリスト
            **kwargs: 最適化アルゴリズムの追加設定

        Returns:
            (最適パラメータの辞書, 最適評価値)
        """
        pass


class OptunaOptimizer(Optimizer):
    """Optunaを使用したベイズ最適化"""
    
    def __init__(self, 
                n_trials: int = 100, 
                timeout: Optional[int] = None,
                study_name: str = "reactivity_study",
                direction: str = "minimize",
                sampler: Optional[optuna.samplers.BaseSampler] = None,
                sampler_kwargs: Optional[Dict[str, Any]] = None,
                show_progress_bar: bool = True):
        """
        Args:
            n_trials: デフォルトの試行回数
            timeout: デフォルトのタイムアウト（秒）
            study_name: Optunaのstudy名
            direction: 最適化の方向 ("minimize" または "maximize")
            sampler: 使用するサンプラー（デフォルトではTPESampler）
            sampler_kwargs: サンプラーに渡す追加パラメータ
            show_progress_bar: 進捗バーを表示するかどうか
        """
        self.n_trials = n_trials
        self.timeout = timeout
        self.study_name = study_name
        self.direction = direction
        self.sampler = sampler
        self.sampler_kwargs = sampler_kwargs or {}
        self.show_progress_bar = show_progress_bar
    
    def optimize(self, 
                objective_func: Callable[[Dict[str, float]], float], 
                parameters: List[Parameter], 
                n_trials: Optional[int] = None, 
                timeout: Optional[int] = None,
                study_name: Optional[str] = None,
                direction: Optional[str] = None,
                show_progress_bar: Optional[bool] = None,
                **kwargs) -> Tuple[Dict[str, float], float]:
        """
        Optunaを使用してパラメータを最適化する
        
        Args:
            objective_func: 目的関数
            parameters: 最適化するパラメータのリスト
            n_trials: 試行回数（コンストラクタで設定した値より優先）
            timeout: タイムアウト（秒）（コンストラクタで設定した値より優先）
            study_name: Optunaのstudy名（コンストラクタで設定した値より優先）
            direction: 最適化の方向 ("minimize" または "maximize")（コンストラクタで設定した値より優先）
            show_progress_bar: 進捗バーを表示するかどうか（コンストラクタで設定した値より優先）
            **kwargs: Optunaの追加設定
            
        Returns:
            (最適パラメータの辞書, 最適評価値)
        """
        # コンストラクタの値とメソッド引数の値をマージ
        n_trials = n_trials if n_trials is not None else self.n_trials
        timeout = timeout if timeout is not None else self.timeout
        study_name = study_name if study_name is not None else self.study_name
        direction = direction if direction is not None else self.direction
        show_progress_bar = show_progress_bar if show_progress_bar is not None else self.show_progress_bar
        param_names = [p.name for p in parameters]
        
        def _objective(trial):
            # 試行ごとにパラメータを提案
            params = {}
            for param in parameters:
                params[param.name] = trial.suggest_float(
                    param.name, 
                    param.lower_bound, 
                    param.upper_bound
                )
            
            # 目的関数を評価
            return objective_func(params)
        
        # サンプラーの設定
        sampler_kwargs = kwargs.get("sampler_kwargs", self.sampler_kwargs)
        sampler = self.sampler or optuna.samplers.TPESampler(**sampler_kwargs)

        # Optunaのstudyを作成して最適化を実行
        study = optuna.create_study(
            study_name=study_name,
            direction=direction,
            sampler=sampler
        )
        
        study.optimize(
            _objective, 
            n_trials=n_trials, 
            timeout=timeout,
            show_progress_bar=show_progress_bar
        )
        
        # 最適なパラメータと評価値を取得
        best_params = study.best_params
        best_value = study.best_value
        
        logger.info(f"最適化完了: 最適値 = {best_value}、パラメータ = {best_params}")
        
        return best_params, best_value


class GridSearchOptimizer(Optimizer):
    """グリッドサーチによる最適化（単純だが直感的）"""
    
    def __init__(self, n_points: int = 10):
        """
        Args:
            n_points: 各パラメータの分割数のデフォルト値
        """
        self.n_points = n_points
    
    def optimize(self, 
                objective_func: Callable[[Dict[str, float]], float], 
                parameters: List[Parameter], 
                n_points: Optional[int] = None,
                **kwargs) -> Tuple[Dict[str, float], float]:
        """
        グリッドサーチでパラメータを最適化する
        
        Args:
            objective_func: 目的関数
            parameters: 最適化するパラメータのリスト
            n_points: 各パラメータの分割数（コンストラクタで設定した値より優先）
            **kwargs: 追加設定
            
        Returns:
            (最適パラメータの辞書, 最適評価値)
        """
        # コンストラクタの値とメソッド引数の値をマージ
        n_points = n_points if n_points is not None else self.n_points
        # 各パラメータの探索範囲を生成
        param_grids = {}
        for param in parameters:
            param_grids[param.name] = np.linspace(
                param.lower_bound, 
                param.upper_bound, 
                n_points
            )
        
        # グリッドポイントを生成
        param_names = [p.name for p in parameters]
        grid_points = np.meshgrid(*[param_grids[name] for name in param_names])
        
        best_params = None
        best_value = float('inf')  # 最小化問題を想定
        
        total_points = n_points ** len(parameters)
        logger.info(f"グリッドサーチ: 総探索ポイント数 = {total_points}")
        
        # すべてのグリッドポイントを評価
        for i in range(total_points):
            # インデックスから多次元インデックスを計算
            indices = np.unravel_index(i, [n_points] * len(parameters))
            
            # パラメータ値を取得
            params = {
                param_names[j]: grid_points[j][indices]
                for j in range(len(parameters))
            }
            
            # 目的関数を評価
            value = objective_func(params)
            
            # 最良値を更新
            if value < best_value:
                best_value = value
                best_params = params.copy()
                
            if i % max(1, total_points // 100) == 0:
                logger.info(f"進捗: {i}/{total_points} ({i/total_points*100:.1f}%)")
                
        logger.info(f"グリッドサーチ完了: 最適値 = {best_value}、パラメータ = {best_params}")
        
        return best_params, best_value


class RandomSearchOptimizer(Optimizer):
    """ランダムサーチによる最適化"""
    
    def __init__(self, n_samples: int = 100, random_seed: Optional[int] = None):
        """
        Args:
            n_samples: サンプル数のデフォルト値
            random_seed: 乱数シード（再現性のため）
        """
        self.n_samples = n_samples
        self.random_seed = random_seed
        
        # 乱数シードが指定されていればセット
        if random_seed is not None:
            np.random.seed(random_seed)
    
    def optimize(self, 
                objective_func: Callable[[Dict[str, float]], float], 
                parameters: List[Parameter], 
                n_samples: Optional[int] = None,
                random_seed: Optional[int] = None,
                **kwargs) -> Tuple[Dict[str, float], float]:
        """
        ランダムサーチでパラメータを最適化する
        
        Args:
            objective_func: 目的関数
            parameters: 最適化するパラメータのリスト
            n_samples: サンプル数（コンストラクタで設定した値より優先）
            random_seed: 乱数シード（コンストラクタで設定した値より優先）
            **kwargs: 追加設定
            
        Returns:
            (最適パラメータの辞書, 最適評価値)
        """
        # コンストラクタの値とメソッド引数の値をマージ
        n_samples = n_samples if n_samples is not None else self.n_samples
        
        # 乱数シードが指定されていて、コンストラクタと異なる場合はセット
        if random_seed is not None and random_seed != self.random_seed:
            np.random.seed(random_seed)
            temp_seed = random_seed
        else:
            temp_seed = self.random_seed
        best_params = None
        best_value = float('inf')  # 最小化問題を想定
        
        logger.info(f"ランダムサーチ: サンプル数 = {n_samples}")
        
        # ランダムサンプリングして評価
        for i in range(n_samples):
            # ランダムにパラメータを生成
            params = {
                param.name: np.random.uniform(param.lower_bound, param.upper_bound)
                for param in parameters
            }
            
            # 目的関数を評価
            value = objective_func(params)
            
            # 最良値を更新
            if value < best_value:
                best_value = value
                best_params = params.copy()
                
            if i % max(1, n_samples // 20) == 0:
                logger.info(f"進捗: {i}/{n_samples} ({i/n_samples*100:.1f}%)")
                
        logger.info(f"ランダムサーチ完了: 最適値 = {best_value}、パラメータ = {best_params}")
        
        return best_params, best_value


class SurrogateModel(abc.ABC):
    """サロゲートモデルのための抽象基底クラス"""
    
    @abc.abstractmethod
    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        """サロゲートモデルを訓練する
        
        Args:
            X: 入力特徴量 (パラメータ値の配列)
            y: 目標値 (対応する評価値)
        """
        pass
    
    @abc.abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        """サロゲートモデルで予測する
        
        Args:
            X: 入力特徴量 (パラメータ値の配列)
            
        Returns:
            予測された評価値
        """
        pass


class ReactivityUQ:
    """原子炉反応度解析のためのインバースUQクラス"""
    
    def __init__(self, 
                reactivity_model: ReactivityModel, 
                error_metric: ErrorMetric = None):
        """
        Args:
            reactivity_model: 反応度計算モデル
            error_metric: 誤差評価メトリック（デフォルトはMSE）
        """
        self.reactivity_model = reactivity_model
        self.error_metric = error_metric if error_metric is not None else MSE()
        self.parameters = []
        self.optimizer = None
        self.best_params = None
        self.best_value = None
        self.optimization_history = {
            'params': [],
            'values': []
        }
    
    def add_parameter(self, name: str, lower_bound: float, upper_bound: float, initial_value: Optional[float] = None) -> None:
        """最適化するパラメータを追加する
        
        Args:
            name: パラメータの名前
            lower_bound: パラメータの下限値
            upper_bound: パラメータの上限値
            initial_value: パラメータの初期値
        """
        self.parameters.append(Parameter(name, lower_bound, upper_bound, initial_value))
        logger.info(f"パラメータ '{name}' を追加しました (範囲: [{lower_bound}, {upper_bound}])")
    
    def set_optimizer(self, optimizer: Optimizer) -> None:
        """使用する最適化アルゴリズムを設定する
        
        Args:
            optimizer: 最適化アルゴリズムのインスタンス
        """
        self.optimizer = optimizer
        logger.info(f"最適化アルゴリズムを {optimizer.__class__.__name__} に設定しました")
    
    def create_objective_function(self, 
                                time_data: np.ndarray, 
                                observed_reactivity: np.ndarray, 
                                **model_inputs) -> Callable[[Dict[str, float]], float]:
        """目的関数を作成する
        
        Args:
            time_data: 時間点の配列
            observed_reactivity: 観測された反応度の配列
            **model_inputs: モデルへの追加入力（温度データなど）
            
        Returns:
            パラメータを受け取り評価値を返す目的関数
        """
        def objective_func(params: Dict[str, float]) -> float:
            # モデルによる反応度の予測
            predicted_reactivity = self.reactivity_model.calculate_reactivity(
                time_data, 
                params, 
                **model_inputs
            )
            
            # 誤差の計算
            error = self.error_metric.calculate(observed_reactivity, predicted_reactivity)
            
            # 最適化の履歴を記録
            self.optimization_history['params'].append(params.copy())
            self.optimization_history['values'].append(error)
            
            return error
        
        return objective_func
    
    def run_optimization(self, 
                       time_data: np.ndarray, 
                       observed_reactivity: np.ndarray, 
                       **kwargs) -> Tuple[Dict[str, float], float]:
        """最適化を実行する
        
        Args:
            time_data: 時間点の配列
            observed_reactivity: 観測された反応度の配列
            **kwargs: その他の入力データ（温度データなど）と最適化の設定
            
        Returns:
            (最適パラメータの辞書, 最適評価値)
        """
        if not self.parameters:
            raise ValueError("パラメータが設定されていません。add_parameter()を使用してパラメータを追加してください。")
            
        if self.optimizer is None:
            raise ValueError("最適化アルゴリズムが設定されていません。set_optimizer()を使用して設定してください。")
        
        # 最適化のパラメータと設定を分離
        model_inputs = {}
        optimizer_kwargs = {}
        
        for key, value in kwargs.items():
            if key.startswith('opt_'):
                # opt_で始まるキーは最適化設定とみなす
                optimizer_kwargs[key[4:]] = value
            else:
                # それ以外はモデル入力とみなす
                model_inputs[key] = value
        
        # 目的関数を作成
        objective_func = self.create_objective_function(
            time_data, 
            observed_reactivity, 
            **model_inputs
        )
        
        # 最適化履歴をリセット
        self.optimization_history = {
            'params': [],
            'values': []
        }
        
        logger.info(f"最適化を開始します...")
        start_time = time.time()
        
        # 最適化の実行
        self.best_params, self.best_value = self.optimizer.optimize(
            objective_func, 
            self.parameters, 
            **optimizer_kwargs
        )
        
        elapsed_time = time.time() - start_time
        logger.info(f"最適化完了（{elapsed_time:.2f}秒）")
        logger.info(f"最適パラメータ: {self.best_params}")
        logger.info(f"最適評価値: {self.best_value}")
        
        return self.best_params, self.best_value
    
    def predict_with_best_params(self, time_data: np.ndarray, **model_inputs) -> np.ndarray:
        """最適パラメータを使用して反応度を予測する
        
        Args:
            time_data: 時間点の配列
            **model_inputs: モデルへの追加入力（温度データなど）
            
        Returns:
            予測された反応度の配列
        """
        if self.best_params is None:
            raise ValueError("最適化が実行されていません。run_optimization()を先に実行してください。")
            
        return self.reactivity_model.calculate_reactivity(
            time_data, 
            self.best_params, 
            **model_inputs
        )
    
    def plot_optimization_history(self, log_scale: bool = True) -> None:
        """最適化の履歴をプロットする
        
        Args:
            log_scale: y軸を対数スケールにするかどうか
        """
        if not self.optimization_history['values']:
            raise ValueError("最適化履歴がありません。run_optimization()を先に実行してください。")
            
        plt.figure(figsize=(10, 6))
        iterations = range(1, len(self.optimization_history['values']) + 1)
        values = self.optimization_history['values']
        
        plt.plot(iterations, values, 'b-')
        plt.scatter(iterations, values, c='b', alpha=0.5)
        
        plt.xlabel('反復回数')
        plt.ylabel('誤差値')
        plt.title('最適化の履歴')
        plt.grid(True)
        
        if log_scale and min(values) > 0:
            plt.yscale('log')
            
        plt.tight_layout()
        plt.show()
    
    def plot_comparison(self, 
                      time_data: np.ndarray, 
                      observed_reactivity: np.ndarray, 
                      **model_inputs) -> None:
        """観測値と予測値を比較プロットする
        
        Args:
            time_data: 時間点の配列
            observed_reactivity: 観測された反応度の配列
            **model_inputs: モデルへの追加入力（温度データなど）
        """
        if self.best_params is None:
            raise ValueError("最適化が実行されていません。run_optimization()を先に実行してください。")
            
        predicted_reactivity = self.predict_with_best_params(time_data, **model_inputs)
        
        plt.figure(figsize=(12, 6))
        plt.plot(time_data, observed_reactivity, 'bo-', label='観測値', alpha=0.7)
        plt.plot(time_data, predicted_reactivity, 'r-', label='予測値', alpha=0.7)
        
        plt.xlabel('時間 [s]')
        plt.ylabel('反応度 [pcm]')
        plt.title('反応度の観測値と予測値の比較')
        plt.legend()
        plt.grid(True)
        
        plt.tight_layout()
        plt.show()
    
    def export_results(self, file_path: str) -> None:
        """最適化結果をCSVファイルにエクスポートする
        
        Args:
            file_path: 出力ファイルのパス
        """
        if self.best_params is None:
            raise ValueError("最適化が実行されていません。run_optimization()を先に実行してください。")
            
        # 結果をDataFrameに変換
        results = pd.DataFrame([self.best_params])
        results['error'] = self.best_value
        
        # CSVに保存
        results.to_csv(file_path, index=False)
        logger.info(f"結果を {file_path} に保存しました")
    
    def export_history(self, file_path: str) -> None:
        """最適化履歴をCSVファイルにエクスポートする
        
        Args:
            file_path: 出力ファイルのパス
        """
        if not self.optimization_history['values']:
            raise ValueError("最適化履歴がありません。run_optimization()を先に実行してください。")
            
        # 履歴をDataFrameに変換
        history_df = pd.DataFrame()
        
        # パラメータの履歴
        for i, params in enumerate(self.optimization_history['params']):
            for name, value in params.items():
                history_df.loc[i, name] = value
                
        # 評価値の履歴
        history_df['error'] = self.optimization_history['values']
        
        # CSVに保存
        history_df.to_csv(file_path, index=False)
        logger.info(f"最適化履歴を {file_path} に保存しました")


# 使用例
def example_usage():
    """ツールの使用例"""
    # 1. 実測データの読み込み（ここでは仮想データを生成）
    time_data = np.linspace(0, 100, 101)
    fuel_temp = 300 + 50 * (1 - np.exp(-time_data / 20))
    coolant_temp = 290 + 30 * (1 - np.exp(-time_data / 30))
    
    # 真のパラメータ値（通常は未知）
    true_fuel_temp_coef = -2.0  # pcm/K
    true_coolant_temp_coef = -1.5  # pcm/K
    
    # 真の反応度を計算（ノイズを追加）
    true_reactivity = true_fuel_temp_coef * fuel_temp + true_coolant_temp_coef * coolant_temp
    observed_reactivity = true_reactivity + np.random.normal(0, 10, len(time_data))
    
    # 2. UQツールの初期化
    reactivity_model = LinearReactivityModel()
    uq_tool = ReactivityUQ(reactivity_model)
    
    # 3. パラメータの追加
    uq_tool.add_parameter("fuel_temp_coef", -5.0, 0.0)
    uq_tool.add_parameter("coolant_temp_coef", -3.0, 0.0)
    
    # 4. 最適化アルゴリズムの設定
    # コンストラクタで設定を指定する方法
    optimizer = OptunaOptimizer(
        n_trials=100,
        study_name="reactor_reactivity_study",
        direction="minimize",
        show_progress_bar=True
    )
    uq_tool.set_optimizer(optimizer)
    
    # 5. 最適化の実行
    best_params, best_value = uq_tool.run_optimization(
        time_data,
        observed_reactivity,
        fuel_temp=fuel_temp,
        coolant_temp=coolant_temp
    )
    
    # もしくは、別の最適化アルゴリズムを試す
    # グリッドサーチの使用例
    # grid_optimizer = GridSearchOptimizer(n_points=5)  # 計算コスト削減のため粗いグリッド
    # uq_tool.set_optimizer(grid_optimizer)
    # best_params_grid, best_value_grid = uq_tool.run_optimization(
    #     time_data,
    #     observed_reactivity,
    #     fuel_temp=fuel_temp,
    #     coolant_temp=coolant_temp
    # )
    
    # 6. 結果の表示
    print(f"最適パラメータ: {best_params}")
    print(f"真のパラメータ: fuel_temp_coef={true_fuel_temp_coef}, coolant_temp_coef={true_coolant_temp_coef}")
    
    # 7. 結果の可視化
    uq_tool.plot_optimization_history()
    uq_tool.plot_comparison(time_data, observed_reactivity, fuel_temp=fuel_temp, coolant_temp=coolant_temp)
    
    # 8. 結果のエクスポート
    uq_tool.export_results("optimization_results.csv")
    uq_tool.export_history("optimization_history.csv")


if __name__ == "__main__":
    # 使用例の実行
    example_usage()

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler

class DataManager:
    def __init__(self, df: pd.DataFrame):
        self.df: pd.DataFrame = df
        self.df_scaled = None
        self.df['pct_change'] = self.df['Close'].pct_change()
        self.df = self.df.iloc[1:].copy()
        self.df.reset_index(drop=True, inplace=True)

    def get_info(self):
        print("Primeiras linhas do DataFrame:")
        print(self.df.head())
        print("\nInformações gerais do DataFrame:")
        print(self.df.info())
        print("\nEstatísticas descritivas detalhadas:")
        print(self.df.describe(include='all'))
        print("\nValores ausentes por coluna:")
        print(self.df.isnull().sum())

    def show_price_over_time(self):
        plt.figure(figsize=(12,6))
        plt.plot(self.df["Open time"], self.df["Close"], label="Close", color="red")
        plt.title("Price Over Time")
        plt.xlabel("Date")
        plt.ylabel("Price")
        plt.legend()
        plt.show()

    def show_volume_distribution(self):
        plt.figure(figsize=(12,6))
        plt.plot(self.df['Open time'], self.df['Volume'], label="Volume", color="purple")
        plt.title("Volume Over Time")
        plt.xlabel("Date")
        plt.ylabel("Volume")
        plt.legend()
        plt.show()

    def show_distributions(self):
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            plt.figure(figsize=(12, 4))

            # Histograma
            plt.subplot(1, 2, 1)
            sns.histplot(self.df[col], kde=True, color='blue')
            plt.title(f'Distribuição de {col}')
            plt.xlabel(col)
            plt.ylabel('Frequência')

            # Boxplot
            plt.subplot(1, 2, 2)
            sns.boxplot(y=self.df[col], color='green')
            plt.title(f'Boxplot de {col}')

            plt.tight_layout()
            plt.show()

    def preprocess_data(self):
        df = self.df.copy()
        scaler = StandardScaler()
        self.df_scaled = pd.DataFrame(scaler.fit_transform(df.select_dtypes(include=[np.number])),
                                     columns=df.select_dtypes(include=[np.number]).columns,
                                     index=df.index)

    def check_correlation_data(self):
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns
        plt.figure(figsize=(14, 10))
        sns.heatmap(self.df[numeric_cols].corr(), annot=True, cmap='coolwarm', fmt='.2f', annot_kws={"size": 8})
        plt.title("Matriz de Correlação")
        plt.tight_layout()
        plt.show()

    def load_indicators(self):
        # Indicadores existentes
        self.df['MA5'] = self.df['Close'].rolling(window=5).mean()
        self.df['MA10'] = self.df['Close'].rolling(window=10).mean()
        self.df['MA20'] = self.df['Close'].rolling(window=20).mean()
        self.df['BB_Middle'] = self.df['Close'].rolling(window=20).mean()
        self.df['BB_Std'] = self.df['Close'].rolling(window=20).std()
        self.df['BB_Upper'] = self.df['BB_Middle'] + (self.df['BB_Std'] * 2)
        self.df['BB_Lower'] = self.df['BB_Middle'] - (self.df['BB_Std'] * 2)
        self.df['BB_Width'] = (self.df['BB_Upper'] - self.df['BB_Lower']) / self.df['BB_Middle']
        self.df['ATR'] = np.maximum(
            self.df['High'] - self.df['Low'],
            np.maximum(
                abs(self.df['High'] - self.df['Close'].shift(1)),
                abs(self.df['Low'] - self.df['Close'].shift(1))
            )
        ).rolling(window=14).mean()

        # Níveis de Fibonacci
        self.fib_levels = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]

        # Fibnc_1: Fibonacci com base na máxima e mínima do dia atual
        for level in self.fib_levels:
            self.df[f'Fibnc_1_{level}'] = self.df['Low'] + (self.df['High'] - self.df['Low']) * level

        # Fibnc_2: Fibonacci com base na máxima e mínima do dia anterior
        for level in self.fib_levels:
            self.df[f'Fibnc_2_{level}'] = self.df['Low'].shift(1) + (self.df['High'].shift(1) - self.df['Low'].shift(1)) * level
        
        # Fibnc_3: Fibonacci com base na máxima e mínima do dia anterior ao dia anterior
        for level in self.fib_levels:
            self.df[f'Fibnc_3_{level}'] = self.df['Low'].shift(2) + (self.df['High'].shift(2) - self.df['Low'].shift(2)) * level



# ==========================================
# 1. CLASSE DE PROCESSAMENTO DE DADOS
# ==========================================
class DataProcessor:
    def __init__(self, sequence_length=60):
        self.sequence_length = sequence_length
        self.scaler = MinMaxScaler(feature_range=(0, 1))

    def prepare_data(self, df, price_col='Close'):
        # Cria a variação percentual
        df['Return'] = df[price_col].pct_change()

        # Remove a primeira linha estritamente via iloc (evita dropna)
        df = df.iloc[1:].copy()
        df.reset_index(drop=True, inplace=True)

        returns_data = df[['Return']].values

        # Escala apenas os retornos
        scaled_returns = self.scaler.fit_transform(returns_data)

        X, y = [], []
        for i in range(self.sequence_length, len(scaled_returns)):
            X.append(scaled_returns[i-self.sequence_length:i, 0])
            y.append(scaled_returns[i, 0])

        X, y = np.array(X), np.array(y)
        X = np.reshape(X, (X.shape[0], X.shape[1], 1))

        return X, y, df


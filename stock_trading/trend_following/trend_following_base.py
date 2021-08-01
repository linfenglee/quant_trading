from enum import Enum
from dataclasses import dataclass
import numpy as np


class State(Enum):
    """"""

    Bull = "bull"
    Bear = "bear"
    Constant = "constant"


@dataclass
class BaseData:
    """
    Any data object needs a vt_symbol as source
    and should inherit base data.
    """

    vt_symbol: str = ""


@dataclass
class MarketData(BaseData):
    """
    Market Data for Trend Following
    """

    rho: float = 0.0679
    alpha: float = 0.001
    theta: float = 0.001

    def __post_init__(self):
        """"""

        self.upper_boundary = np.log(1 + self.theta)
        self.lower_boundary = np.log(1 - self.alpha)


@dataclass
class ModelData(BaseData):
    """
    Basic Setting for FDM
    """

    T: float = 1
    I: int = 2_000
    N: int = 1_000

    def __post_init__(self):
        """"""
        self.dt = self.T / self.N
        self.dp = 1 / self.I

    epsilon: float = 1.0e-6
    omega: float = 1.6      # relax parameter
    beta: float = 1.0e7     # penalty method


@dataclass
class ParameterData(BaseData):
    """
    Parameter Data for Trend Following
    """

    bull_mu: float = 0.18
    bear_mu: float = -0.77

    bull_sigma: float = 0.184
    bear_sigma: float = 0.184
    constant_sigma: float = 0.184

    bull_lambda: float = 0.36
    bear_lambda: float = 2.53


@dataclass
class BoundaryData(BaseData):
    """
    Buy & Sell Boundary for Trend Following
    """

    sell_boundary: float = 0
    buy_boundary: float = 0


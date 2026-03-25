"""
BUE Ultimate 10/10 - Complete Business Underwriting Engine
Version: 2.0.0
Category-Defining Platform for Aetherion CGI
"""

__version__ = "2.0.0"
__author__ = "Aetherion"
__status__ = "Production"

from bue.core.engine import (
    BUEngine,
    AnalysisOptions,
    AnalysisResult,
    AnalysisMode,
    ForecastModel,
    StreamUpdate,
    analyze
)

__all__ = [
    'BUEngine',
    'AnalysisOptions',
    'AnalysisResult',
    'AnalysisMode',
    'ForecastModel',
    'StreamUpdate',
    'analyze'
]

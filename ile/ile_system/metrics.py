"""
ILE Core Metrics Engine

Comprehensive metrics computation for learning performance including:
- Accuracy, precision, recall, F1
- Mean Absolute Error (MAE), Brier score
- Calibration analysis
- Confusion matrices
- Learning signal analysis

Author: Aetherion Development Team
Date: November 15, 2025
"""

import logging
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


# ============================================================================
# CORE METRICS FUNCTIONS
# ============================================================================

def compute_accuracy(predictions: List[bool], actuals: List[bool]) -> float:
    """
    Compute classification accuracy.
    
    Args:
        predictions: List of predicted boolean values
        actuals: List of actual boolean values
    
    Returns:
        Accuracy score (0.0 to 1.0)
    """
    if not predictions or len(predictions) != len(actuals):
        return 0.0
    
    correct = sum(p == a for p, a in zip(predictions, actuals))
    return correct / len(predictions)


def compute_mae(predictions: List[float], actuals: List[float]) -> float:
    """
    Compute Mean Absolute Error for regression tasks.
    
    Args:
        predictions: List of predicted values
        actuals: List of actual values
    
    Returns:
        MAE score (lower is better)
    """
    if not predictions or len(predictions) != len(actuals):
        return float('inf')
    
    errors = [abs(p - a) for p, a in zip(predictions, actuals)]
    return sum(errors) / len(errors)


def compute_brier_score(probabilities: List[float], actuals: List[bool]) -> float:
    """
    Compute Brier score for probability calibration.
    Measures the mean squared difference between predicted probabilities
    and actual outcomes.
    
    Args:
        probabilities: List of predicted probabilities (0.0 to 1.0)
        actuals: List of actual boolean outcomes
    
    Returns:
        Brier score (0.0 = perfect, 1.0 = worst)
    """
    if not probabilities or len(probabilities) != len(actuals):
        return 1.0
    
    score = sum((p - float(a)) ** 2 for p, a in zip(probabilities, actuals))
    return score / len(probabilities)


def compute_confusion_matrix(
    predictions: List[bool],
    actuals: List[bool]
) -> Dict[str, int]:
    """
    Compute confusion matrix for binary classification.
    
    Args:
        predictions: List of predicted boolean values
        actuals: List of actual boolean values
    
    Returns:
        Dictionary with keys: 'tp', 'tn', 'fp', 'fn'
    """
    if not predictions or len(predictions) != len(actuals):
        return {'tp': 0, 'tn': 0, 'fp': 0, 'fn': 0}
    
    tp = sum(p and a for p, a in zip(predictions, actuals))
    tn = sum(not p and not a for p, a in zip(predictions, actuals))
    fp = sum(p and not a for p, a in zip(predictions, actuals))
    fn = sum(not p and a for p, a in zip(predictions, actuals))
    
    return {
        'tp': tp,  # True positives
        'tn': tn,  # True negatives
        'fp': fp,  # False positives
        'fn': fn   # False negatives
    }


def compute_precision_recall_f1(confusion: Dict[str, int]) -> Tuple[float, float, float]:
    """
    Compute precision, recall, and F1 score from confusion matrix.
    
    Args:
        confusion: Confusion matrix dictionary
    
    Returns:
        Tuple of (precision, recall, f1_score)
    """
    tp = confusion['tp']
    fp = confusion['fp']
    fn = confusion['fn']
    
    # Precision = TP / (TP + FP)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    
    # Recall = TP / (TP + FN)
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    
    # F1 = 2 * (Precision * Recall) / (Precision + Recall)
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0 else 0.0
    )
    
    return precision, recall, f1


def compute_calibration_curve(
    probabilities: List[float],
    actuals: List[bool],
    num_bins: int = 10
) -> Dict[str, List[float]]:
    """
    Compute calibration curve for probability predictions.
    Bins predictions into groups and compares predicted vs actual rates.
    
    Args:
        probabilities: List of predicted probabilities
        actuals: List of actual outcomes
        num_bins: Number of calibration bins
    
    Returns:
        Dictionary with 'bin_centers', 'predicted_rates', 'actual_rates'
    """
    if not probabilities or len(probabilities) != len(actuals):
        return {
            'bin_centers': [],
            'predicted_rates': [],
            'actual_rates': []
        }
    
    # Create bins
    bins = np.linspace(0, 1, num_bins + 1)
    bin_centers = (bins[:-1] + bins[1:]) / 2
    
    predicted_rates = []
    actual_rates = []
    
    for i in range(num_bins):
        # Find predictions in this bin
        lower = bins[i]
        upper = bins[i + 1]
        
        in_bin = [
            (p, a) for p, a in zip(probabilities, actuals)
            if lower <= p < upper or (i == num_bins - 1 and p == upper)
        ]
        
        if in_bin:
            # Average predicted probability in bin
            predicted_rate = sum(p for p, _ in in_bin) / len(in_bin)
            
            # Actual positive rate in bin
            actual_rate = sum(a for _, a in in_bin) / len(in_bin)
            
            predicted_rates.append(predicted_rate)
            actual_rates.append(actual_rate)
        else:
            # Empty bin
            predicted_rates.append(bin_centers[i])
            actual_rates.append(bin_centers[i])
    
    return {
        'bin_centers': bin_centers.tolist(),
        'predicted_rates': predicted_rates,
        'actual_rates': actual_rates
    }


def compute_calibration_error(
    probabilities: List[float],
    actuals: List[bool],
    num_bins: int = 10
) -> float:
    """
    Compute Expected Calibration Error (ECE).
    
    Args:
        probabilities: List of predicted probabilities
        actuals: List of actual outcomes
        num_bins: Number of calibration bins
    
    Returns:
        ECE score (lower is better)
    """
    calibration = compute_calibration_curve(probabilities, actuals, num_bins)
    
    if not calibration['predicted_rates']:
        return 1.0
    
    # Weighted average of |predicted - actual| in each bin
    errors = [
        abs(pred - actual)
        for pred, actual in zip(
            calibration['predicted_rates'],
            calibration['actual_rates']
        )
    ]
    
    return sum(errors) / len(errors)


# ============================================================================
# LEARNING SIGNAL ANALYSIS
# ============================================================================

def analyze_learning_signals(signals: List[float]) -> Dict[str, float]:
    """
    Analyze distribution of learning signals.
    
    Args:
        signals: List of learning signals (-1.0 to 1.0)
    
    Returns:
        Dictionary with statistics
    """
    if not signals:
        return {
            'mean': 0.0,
            'median': 0.0,
            'std': 0.0,
            'min': 0.0,
            'max': 0.0,
            'positive_rate': 0.0
        }
    
    signals_array = np.array(signals)
    
    return {
        'mean': float(np.mean(signals_array)),
        'median': float(np.median(signals_array)),
        'std': float(np.std(signals_array)),
        'min': float(np.min(signals_array)),
        'max': float(np.max(signals_array)),
        'positive_rate': float(np.mean(signals_array > 0))
    }


# ============================================================================
# AGGREGATE METRICS FROM LEARNING EVENTS
# ============================================================================

def compute_metrics_from_events(
    events: List[Dict],
    metric_type: str = "classification"
) -> Dict[str, float]:
    """
    Compute comprehensive metrics from learning events.
    
    Args:
        events: List of learning events with 'predicted' and 'actual' fields
        metric_type: Type of metrics ('classification', 'regression', 'probability')
    
    Returns:
        Dictionary of computed metrics
    """
    if not events:
        return {}
    
    metrics = {}
    
    if metric_type == "classification":
        # Binary classification metrics
        predictions = [e.get('predicted', {}).get('class', False) for e in events]
        actuals = [e.get('actual', {}).get('class', False) for e in events]
        
        # Remove None values
        valid_pairs = [(p, a) for p, a in zip(predictions, actuals) if p is not None and a is not None]
        if valid_pairs:
            predictions, actuals = zip(*valid_pairs)
            
            # Accuracy
            metrics['accuracy'] = compute_accuracy(list(predictions), list(actuals))
            
            # Confusion matrix
            confusion = compute_confusion_matrix(list(predictions), list(actuals))
            metrics.update(confusion)
            
            # Precision, Recall, F1
            precision, recall, f1 = compute_precision_recall_f1(confusion)
            metrics['precision'] = precision
            metrics['recall'] = recall
            metrics['f1_score'] = f1
    
    elif metric_type == "regression":
        # Regression metrics
        predictions = [e.get('predicted', {}).get('value', 0.0) for e in events]
        actuals = [e.get('actual', {}).get('value', 0.0) for e in events]
        
        # MAE
        metrics['mae'] = compute_mae(predictions, actuals)
        
        # RMSE
        if predictions and len(predictions) == len(actuals):
            errors = [(p - a) ** 2 for p, a in zip(predictions, actuals)]
            metrics['rmse'] = (sum(errors) / len(errors)) ** 0.5
    
    elif metric_type == "probability":
        # Probability calibration metrics
        probabilities = [e.get('predicted', {}).get('probability', 0.5) for e in events]
        actuals = [e.get('actual', {}).get('outcome', False) for e in events]
        
        # Remove invalid values
        valid_pairs = [
            (p, a) for p, a in zip(probabilities, actuals)
            if p is not None and a is not None and 0 <= p <= 1
        ]
        
        if valid_pairs:
            probabilities, actuals = zip(*valid_pairs)
            
            # Brier score
            metrics['brier_score'] = compute_brier_score(list(probabilities), list(actuals))
            
            # Calibration error
            metrics['calibration_error'] = compute_calibration_error(
                list(probabilities),
                list(actuals)
            )
    
    # Learning signal analysis
    signals = [e.get('learning_signal', 0.0) for e in events if e.get('learning_signal') is not None]
    if signals:
        signal_stats = analyze_learning_signals(signals)
        metrics.update({f'signal_{k}': v for k, v in signal_stats.items()})
    
    return metrics


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    # Test accuracy
    preds = [True, False, True, True, False]
    acts = [True, False, False, True, False]
    print(f"Accuracy: {compute_accuracy(preds, acts):.2f}")
    
    # Test confusion matrix
    confusion = compute_confusion_matrix(preds, acts)
    print(f"Confusion: {confusion}")
    
    # Test precision/recall/F1
    p, r, f1 = compute_precision_recall_f1(confusion)
    print(f"Precision: {p:.2f}, Recall: {r:.2f}, F1: {f1:.2f}")
    
    # Test Brier score
    probs = [0.9, 0.1, 0.7, 0.8, 0.2]
    print(f"Brier: {compute_brier_score(probs, acts):.3f}")
    
    # Test calibration
    cal = compute_calibration_curve(probs, acts, num_bins=3)
    print(f"Calibration: {cal}")
    
    print("\n✅ Metrics module test completed!")

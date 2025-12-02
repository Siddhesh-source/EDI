#include "indicators.h"
#include <numeric>
#include <cmath>

namespace indicators {

// Extract close prices from OHLC bars
std::vector<double> TechnicalIndicatorEngine::extract_closes(const std::vector<OHLC>& bars) {
    std::vector<double> closes;
    closes.reserve(bars.size());
    for (const auto& bar : bars) {
        closes.push_back(bar.close);
    }
    return closes;
}

// Compute standard deviation
double TechnicalIndicatorEngine::compute_std_dev(const std::vector<double>& values, double mean) {
    double sum_sq_diff = 0.0;
    for (double val : values) {
        double diff = val - mean;
        sum_sq_diff += diff * diff;
    }
    return std::sqrt(sum_sq_diff / values.size());
}

// Simple Moving Average
double TechnicalIndicatorEngine::compute_sma(const std::vector<double>& prices, int period) {
    if (prices.size() < static_cast<size_t>(period)) {
        throw std::invalid_argument("Insufficient data for SMA calculation");
    }
    
    double sum = 0.0;
    for (size_t i = prices.size() - period; i < prices.size(); ++i) {
        sum += prices[i];
    }
    return sum / period;
}

// Exponential Moving Average
double TechnicalIndicatorEngine::compute_ema(const std::vector<double>& prices, int period) {
    if (prices.size() < static_cast<size_t>(period)) {
        throw std::invalid_argument("Insufficient data for EMA calculation");
    }
    
    // Calculate initial SMA as starting point
    double ema = 0.0;
    for (size_t i = 0; i < static_cast<size_t>(period); ++i) {
        ema += prices[i];
    }
    ema /= period;
    
    // Calculate EMA using smoothing factor
    double multiplier = 2.0 / (period + 1.0);
    for (size_t i = period; i < prices.size(); ++i) {
        ema = (prices[i] - ema) * multiplier + ema;
    }
    
    return ema;
}

// Relative Strength Index
double TechnicalIndicatorEngine::compute_rsi(const std::vector<double>& prices, int period) {
    if (prices.size() < static_cast<size_t>(period + 1)) {
        throw std::invalid_argument("Insufficient data for RSI calculation");
    }
    
    double avg_gain = 0.0;
    double avg_loss = 0.0;
    
    // Calculate initial average gain and loss
    for (size_t i = 1; i <= static_cast<size_t>(period); ++i) {
        double change = prices[i] - prices[i - 1];
        if (change > 0) {
            avg_gain += change;
        } else {
            avg_loss += std::abs(change);
        }
    }
    avg_gain /= period;
    avg_loss /= period;
    
    // Calculate RSI using smoothed averages
    for (size_t i = period + 1; i < prices.size(); ++i) {
        double change = prices[i] - prices[i - 1];
        double gain = (change > 0) ? change : 0.0;
        double loss = (change < 0) ? std::abs(change) : 0.0;
        
        avg_gain = (avg_gain * (period - 1) + gain) / period;
        avg_loss = (avg_loss * (period - 1) + loss) / period;
    }
    
    if (avg_loss == 0.0) {
        return 100.0;
    }
    
    double rs = avg_gain / avg_loss;
    return 100.0 - (100.0 / (1.0 + rs));
}

// MACD (Moving Average Convergence Divergence)
MACDResult TechnicalIndicatorEngine::compute_macd(const std::vector<double>& prices,
                                                  int fast_period,
                                                  int slow_period,
                                                  int signal_period) {
    if (prices.size() < static_cast<size_t>(slow_period + signal_period)) {
        throw std::invalid_argument("Insufficient data for MACD calculation");
    }
    
    // Calculate fast and slow EMAs
    double fast_ema = compute_ema(prices, fast_period);
    double slow_ema = compute_ema(prices, slow_period);
    
    // MACD line is the difference
    double macd_line = fast_ema - slow_ema;
    
    // Calculate signal line (EMA of MACD line)
    // For simplicity, we'll use a simple approximation
    // In production, you'd maintain a history of MACD values
    std::vector<double> macd_history;
    
    // Build MACD history for signal line calculation
    size_t start_idx = slow_period;
    for (size_t i = start_idx; i < prices.size(); ++i) {
        std::vector<double> subset(prices.begin(), prices.begin() + i + 1);
        double f_ema = compute_ema(subset, fast_period);
        double s_ema = compute_ema(subset, slow_period);
        macd_history.push_back(f_ema - s_ema);
    }
    
    double signal_line = 0.0;
    if (macd_history.size() >= static_cast<size_t>(signal_period)) {
        signal_line = compute_ema(macd_history, signal_period);
    } else {
        signal_line = macd_line;
    }
    
    double histogram = macd_line - signal_line;
    
    return MACDResult{macd_line, signal_line, histogram};
}

// Bollinger Bands
BollingerBands TechnicalIndicatorEngine::compute_bollinger_bands(const std::vector<double>& prices,
                                                                 int period,
                                                                 double std_dev) {
    if (prices.size() < static_cast<size_t>(period)) {
        throw std::invalid_argument("Insufficient data for Bollinger Bands calculation");
    }
    
    // Calculate middle band (SMA)
    double middle = compute_sma(prices, period);
    
    // Calculate standard deviation of recent prices
    std::vector<double> recent_prices(prices.end() - period, prices.end());
    double std = compute_std_dev(recent_prices, middle);
    
    // Calculate upper and lower bands
    double upper = middle + (std_dev * std);
    double lower = middle - (std_dev * std);
    
    return BollingerBands{upper, middle, lower};
}

// Average True Range
double TechnicalIndicatorEngine::compute_atr(const std::vector<OHLC>& bars, int period) {
    if (bars.size() < static_cast<size_t>(period + 1)) {
        throw std::invalid_argument("Insufficient data for ATR calculation");
    }
    
    std::vector<double> true_ranges;
    true_ranges.reserve(bars.size() - 1);
    
    for (size_t i = 1; i < bars.size(); ++i) {
        double high_low = bars[i].high - bars[i].low;
        double high_close = std::abs(bars[i].high - bars[i - 1].close);
        double low_close = std::abs(bars[i].low - bars[i - 1].close);
        
        double tr = std::max({high_low, high_close, low_close});
        true_ranges.push_back(tr);
    }
    
    // Calculate ATR as SMA of true ranges
    return compute_sma(true_ranges, period);
}

// Main computation method
IndicatorResults TechnicalIndicatorEngine::compute_indicators(const PriceData& prices) {
    if (prices.bars.empty()) {
        throw std::invalid_argument("Empty price data");
    }
    
    if (prices.bars.size() < 50) {
        throw std::invalid_argument("Insufficient data: need at least 50 bars");
    }
    
    std::vector<double> closes = extract_closes(prices.bars);
    
    IndicatorResults results;
    
    try {
        results.rsi = compute_rsi(closes, 14);
        results.macd = compute_macd(closes, 12, 26, 9);
        results.bollinger = compute_bollinger_bands(closes, 20, 2.0);
        results.sma_20 = compute_sma(closes, 20);
        results.sma_50 = compute_sma(closes, 50);
        results.ema_12 = compute_ema(closes, 12);
        results.ema_26 = compute_ema(closes, 26);
        results.atr = compute_atr(prices.bars, 14);
    } catch (const std::exception& e) {
        throw std::runtime_error(std::string("Indicator computation failed: ") + e.what());
    }
    
    return results;
}

// Generate trading signals based on indicators
TechnicalSignals TechnicalIndicatorEngine::generate_signals(const IndicatorResults& indicators,
                                                           double current_price) {
    TechnicalSignals signals;
    
    // RSI signals
    if (indicators.rsi > 70.0) {
        signals.rsi_signal = SignalType::OVERBOUGHT;
    } else if (indicators.rsi < 30.0) {
        signals.rsi_signal = SignalType::OVERSOLD;
    } else {
        signals.rsi_signal = SignalType::NEUTRAL;
    }
    
    // MACD signals (crossover detection)
    if (indicators.macd.histogram > 0.0) {
        signals.macd_signal = SignalType::BULLISH_CROSS;
    } else if (indicators.macd.histogram < 0.0) {
        signals.macd_signal = SignalType::BEARISH_CROSS;
    } else {
        signals.macd_signal = SignalType::NEUTRAL;
    }
    
    // Bollinger Bands signals
    if (current_price > indicators.bollinger.upper) {
        signals.bb_signal = SignalType::UPPER_BREACH;
    } else if (current_price < indicators.bollinger.lower) {
        signals.bb_signal = SignalType::LOWER_BREACH;
    } else {
        signals.bb_signal = SignalType::NEUTRAL;
    }
    
    return signals;
}

} // namespace indicators

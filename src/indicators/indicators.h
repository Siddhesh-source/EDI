#pragma once

#include <vector>
#include <string>
#include <cmath>
#include <algorithm>
#include <stdexcept>

namespace indicators {

// Data structures matching Python models
struct OHLC {
    double open;
    double high;
    double low;
    double close;
    int64_t volume;
    int64_t timestamp;
};

struct PriceData {
    std::string symbol;
    std::vector<OHLC> bars;
    int64_t timestamp;
};

struct MACDResult {
    double macd_line;
    double signal_line;
    double histogram;
};

struct BollingerBands {
    double upper;
    double middle;
    double lower;
};

struct IndicatorResults {
    double rsi;
    MACDResult macd;
    BollingerBands bollinger;
    double sma_20;
    double sma_50;
    double ema_12;
    double ema_26;
    double atr;
};

enum class SignalType {
    OVERBOUGHT,
    OVERSOLD,
    BULLISH_CROSS,
    BEARISH_CROSS,
    UPPER_BREACH,
    LOWER_BREACH,
    NEUTRAL
};

struct TechnicalSignals {
    SignalType rsi_signal;
    SignalType macd_signal;
    SignalType bb_signal;
};

// Technical Indicator Engine class
class TechnicalIndicatorEngine {
public:
    TechnicalIndicatorEngine() = default;
    
    // Main computation methods
    IndicatorResults compute_indicators(const PriceData& prices);
    TechnicalSignals generate_signals(const IndicatorResults& indicators, double current_price);
    
    // Individual indicator calculations
    double compute_rsi(const std::vector<double>& prices, int period = 14);
    MACDResult compute_macd(const std::vector<double>& prices, 
                           int fast_period = 12, 
                           int slow_period = 26, 
                           int signal_period = 9);
    BollingerBands compute_bollinger_bands(const std::vector<double>& prices, 
                                          int period = 20, 
                                          double std_dev = 2.0);
    double compute_sma(const std::vector<double>& prices, int period);
    double compute_ema(const std::vector<double>& prices, int period);
    double compute_atr(const std::vector<OHLC>& bars, int period = 14);
    
private:
    // Helper methods
    std::vector<double> extract_closes(const std::vector<OHLC>& bars);
    double compute_std_dev(const std::vector<double>& values, double mean);
};

} // namespace indicators

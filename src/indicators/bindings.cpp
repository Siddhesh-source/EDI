#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "indicators.h"

namespace py = pybind11;

PYBIND11_MODULE(indicators_engine, m) {
    m.doc() = "C++ Technical Indicator Engine for high-performance computation";
    
    // OHLC structure
    py::class_<indicators::OHLC>(m, "OHLC")
        .def(py::init<>())
        .def_readwrite("open", &indicators::OHLC::open)
        .def_readwrite("high", &indicators::OHLC::high)
        .def_readwrite("low", &indicators::OHLC::low)
        .def_readwrite("close", &indicators::OHLC::close)
        .def_readwrite("volume", &indicators::OHLC::volume)
        .def_readwrite("timestamp", &indicators::OHLC::timestamp);
    
    // PriceData structure
    py::class_<indicators::PriceData>(m, "PriceData")
        .def(py::init<>())
        .def_readwrite("symbol", &indicators::PriceData::symbol)
        .def_readwrite("bars", &indicators::PriceData::bars)
        .def_readwrite("timestamp", &indicators::PriceData::timestamp);
    
    // MACDResult structure
    py::class_<indicators::MACDResult>(m, "MACDResult")
        .def(py::init<>())
        .def_readwrite("macd_line", &indicators::MACDResult::macd_line)
        .def_readwrite("signal_line", &indicators::MACDResult::signal_line)
        .def_readwrite("histogram", &indicators::MACDResult::histogram);
    
    // BollingerBands structure
    py::class_<indicators::BollingerBands>(m, "BollingerBands")
        .def(py::init<>())
        .def_readwrite("upper", &indicators::BollingerBands::upper)
        .def_readwrite("middle", &indicators::BollingerBands::middle)
        .def_readwrite("lower", &indicators::BollingerBands::lower);
    
    // IndicatorResults structure
    py::class_<indicators::IndicatorResults>(m, "IndicatorResults")
        .def(py::init<>())
        .def_readwrite("rsi", &indicators::IndicatorResults::rsi)
        .def_readwrite("macd", &indicators::IndicatorResults::macd)
        .def_readwrite("bollinger", &indicators::IndicatorResults::bollinger)
        .def_readwrite("sma_20", &indicators::IndicatorResults::sma_20)
        .def_readwrite("sma_50", &indicators::IndicatorResults::sma_50)
        .def_readwrite("ema_12", &indicators::IndicatorResults::ema_12)
        .def_readwrite("ema_26", &indicators::IndicatorResults::ema_26)
        .def_readwrite("atr", &indicators::IndicatorResults::atr);
    
    // SignalType enum
    py::enum_<indicators::SignalType>(m, "SignalType")
        .value("OVERBOUGHT", indicators::SignalType::OVERBOUGHT)
        .value("OVERSOLD", indicators::SignalType::OVERSOLD)
        .value("BULLISH_CROSS", indicators::SignalType::BULLISH_CROSS)
        .value("BEARISH_CROSS", indicators::SignalType::BEARISH_CROSS)
        .value("UPPER_BREACH", indicators::SignalType::UPPER_BREACH)
        .value("LOWER_BREACH", indicators::SignalType::LOWER_BREACH)
        .value("NEUTRAL", indicators::SignalType::NEUTRAL)
        .export_values();
    
    // TechnicalSignals structure
    py::class_<indicators::TechnicalSignals>(m, "TechnicalSignals")
        .def(py::init<>())
        .def_readwrite("rsi_signal", &indicators::TechnicalSignals::rsi_signal)
        .def_readwrite("macd_signal", &indicators::TechnicalSignals::macd_signal)
        .def_readwrite("bb_signal", &indicators::TechnicalSignals::bb_signal);
    
    // TechnicalIndicatorEngine class
    py::class_<indicators::TechnicalIndicatorEngine>(m, "TechnicalIndicatorEngine")
        .def(py::init<>())
        .def("compute_indicators", &indicators::TechnicalIndicatorEngine::compute_indicators,
             "Compute all technical indicators for given price data")
        .def("generate_signals", &indicators::TechnicalIndicatorEngine::generate_signals,
             "Generate trading signals based on indicator values")
        .def("compute_rsi", &indicators::TechnicalIndicatorEngine::compute_rsi,
             "Compute Relative Strength Index",
             py::arg("prices"), py::arg("period") = 14)
        .def("compute_macd", &indicators::TechnicalIndicatorEngine::compute_macd,
             "Compute MACD indicator",
             py::arg("prices"), py::arg("fast_period") = 12, 
             py::arg("slow_period") = 26, py::arg("signal_period") = 9)
        .def("compute_bollinger_bands", &indicators::TechnicalIndicatorEngine::compute_bollinger_bands,
             "Compute Bollinger Bands",
             py::arg("prices"), py::arg("period") = 20, py::arg("std_dev") = 2.0)
        .def("compute_sma", &indicators::TechnicalIndicatorEngine::compute_sma,
             "Compute Simple Moving Average",
             py::arg("prices"), py::arg("period"))
        .def("compute_ema", &indicators::TechnicalIndicatorEngine::compute_ema,
             "Compute Exponential Moving Average",
             py::arg("prices"), py::arg("period"))
        .def("compute_atr", &indicators::TechnicalIndicatorEngine::compute_atr,
             "Compute Average True Range",
             py::arg("bars"), py::arg("period") = 14);
}

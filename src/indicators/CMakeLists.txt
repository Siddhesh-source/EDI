cmake_minimum_required(VERSION 3.12)
project(technical_indicators)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find Python and pybind11
find_package(Python COMPONENTS Interpreter Development REQUIRED)
find_package(pybind11 CONFIG REQUIRED)

# Create the C++ library
add_library(indicators_core STATIC
    indicators.cpp
)

target_include_directories(indicators_core PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})

# Create Python module
pybind11_add_module(indicators_engine
    bindings.cpp
)

target_link_libraries(indicators_engine PRIVATE indicators_core)

# Set output directory
set_target_properties(indicators_engine PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
)

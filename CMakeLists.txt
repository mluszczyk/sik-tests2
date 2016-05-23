cmake_minimum_required(VERSION 3.5)
project(tests2)

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")

set(SOURCE_FILES
    test_master.py)

add_executable(tests2 ${SOURCE_FILES})
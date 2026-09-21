# Optional C++ interactive menu (thin wrapper around the Python CLI).
# Primary entry point: python climate_modeler.py --temp 70
#
# No Boost. Build from the repo root so relative script paths resolve.

CXX ?= g++
CXXFLAGS ?= --std=c++11 -Wall -Werror -pedantic -g

.PHONY: all clean run-python

all: main.exe

main.exe: main.cpp
	$(CXX) $(CXXFLAGS) $^ -o $@

run-python:
	python3 climate_modeler.py --temp 60

clean:
	rm -rvf *.exe *.out.txt *.dSYM *.stackdump output_*.csv

.SUFFIXES:

CXX = g++
CXXFLAGS = -O3 -march=native -pthread

all: mt_brute rand_brute java_crack

mt_brute: mt_brute.cpp
	$(CXX) $(CXXFLAGS) -o $@ $<

rand_brute: rand_brute.cpp
	$(CXX) $(CXXFLAGS) -o $@ $<

java_crack: java_crack.cpp
	$(CXX) $(CXXFLAGS) -o $@ $<

clean:
	rm -f mt_brute rand_brute java_crack

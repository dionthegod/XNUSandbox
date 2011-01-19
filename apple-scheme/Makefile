as: as.c syms.h
	gcc -m32 as.c -o as

syms.h: find-symbols.py
	./find-symbols.py > syms.h

clean:
	rm as

CC=gcc

LDIR =/usr/local/lib

LIBS=-lm -lbcm2835

OBJ = bp_test_pi.o 

CFLAGS = -std=gnu11


%.o: %.c $(DEPS)
	$(CC) -c -o $@ $< $(CFLAGS)

bp_test_pi: $(OBJ)
	$(CC) -o $@ $^ $(CFLAGS) $(LIBS)

.PHONY: clean

clean:
	rm -f $(OBJ)

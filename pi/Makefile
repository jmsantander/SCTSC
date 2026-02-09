CC=/usr/bin/gcc

bp_test_pi: bp_test_pi.c
	$(CC) -Wall  -g -o $@ $@.c -l bcm2835
	
hodo_chamber:	hodo_chamber.c
	$(CC) -Wall  -g -o $@ $@.c -lm
	
c_tp:	c_tp.c
	$(CC) -Wall  -g -o $@ $@.c -lm
	
scint_tp:	scint_tp.c
	$(CC) -Wall  -g -o $@ $@.c -lm
	
urbana:	urbana.c
	$(CC) -Wall  -g -o $@ $@.c -lm
	
urbana_tp:	urbana_tp.c
	$(CC) -Wall  -g -o $@ $@.c -lm
	
st_io_library:	st_io_library.c
	$(CC) -Wall  -g -o $@ $@.c -lm
	
trim_tp:	trim_tp.c
	$(CC) -L. -g -o $@ $@.c -lsthw
	
vac_tp:	vac_tp.c
	$(CC) -L. -g -o $@ $@.c -lsthw

clean:
	rm -f *.o st_io2 hodo_chamber


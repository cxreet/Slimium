default: shm_create shm_read shm_clear shm_decode

shm_create: shm_create.c defs.h
	gcc shm_create.c defs.h -o shm_create

shm_read: shm_read.c defs.h
	gcc shm_read.c defs.h -o shm_read

shm_clear: shm_clear.c defs.h
	gcc shm_clear.c defs.h -o shm_clear
	#clang -c -emit-llvm shm_clear.c defs.h
	#llvm-dis shm_clear.bc -o shm_clear.ll

shm_decode: shm_decode.c defs.h
	gcc shm_decode.c defs.h -o shm_decode

clean:
	rm shm_create shm_read shm_clear shm_decode *.bc *.ll

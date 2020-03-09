#include <stdio.h>
#include <sys/ipc.h>
#include <sys/shm.h>
#include <sys/stat.h>
#include "defs.h"

int main ()

{
	int segment_id;
	char* shared_memory;
	const int int_size = TOTAL_FUNCTION_NUM/(sizeof(int) * 8) + 1;
	const int shared_segment_size = int_size * sizeof(int);
	key_t key = SHM_KEY;

	segment_id = shmget(key, shared_segment_size, S_IRUSR | S_IRGRP);

	shared_memory = (char*) shmat (segment_id, 0, 0);

	printf ("The contents (non-zero) of the shared memory is:\n");
	int* vals = (int*) shared_memory;
	for (int i = 0; i < int_size; i++)
	{
		if (vals[i] != 0)
			printf("%d: %x\n", i, vals[i]);
	}
	shmdt (shared_memory);

	return 0;

}

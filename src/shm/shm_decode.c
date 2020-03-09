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

	int executed_func_num = 0;

	int* vals = (int*) shared_memory;
	for (int i = 0; i < int_size; i++){
		if (vals[i] == 0) 
			continue;

		for (int j = 0; j < sizeof(int) * 8; j++) {
			int bit = (vals[i] >> j) & 0x1;
			if (bit == 1) {
				executed_func_num++;
				int function_idx = i * (sizeof(int) * 8) + j;
				printf("%d\n", function_idx);
			}
		}
	}

	printf("In total, %d (%f) out of %d functions are executed!\n", 
			executed_func_num, (float)executed_func_num/(float)TOTAL_FUNCTION_NUM, TOTAL_FUNCTION_NUM);

	shmdt (shared_memory);

	return 0;

}

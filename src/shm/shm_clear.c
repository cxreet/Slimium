#include <stdio.h>
#include <sys/ipc.h>
#include <sys/shm.h>
#include <sys/stat.h>
#include "defs.h"

int* shared_memory = NULL;

void foo()
{
	int idx;

	int segment_id;
	const int int_size = TOTAL_FUNCTION_NUM/(sizeof(int) * 8) + 1;
	const int shared_segment_size = int_size * sizeof(int);
	key_t key = SHM_KEY;

	segment_id = shmget(key, shared_segment_size, S_IWUSR | S_IWGRP);
	
	if (shared_memory == NULL)
		shared_memory = (int*) shmat (segment_id, 0, 0);

	int which_int = idx / (sizeof(int) * 8);
	int which_bit = idx % (sizeof(int) * 8);
	shared_memory[which_int] |= 1 << which_bit;	

	shmdt(shared_memory);
}

int main ()

{
	int segment_id;
	int* shared_memory;
	const int int_size = TOTAL_FUNCTION_NUM/(sizeof(int) * 8) + 1;
	const int shared_segment_size = int_size * sizeof(int);
	key_t key = SHM_KEY;

	segment_id = shmget(key, shared_segment_size, S_IWUSR | S_IWGRP);

	shared_memory = (int*) shmat (segment_id, 0, 0);

	for (int i = 0; i < int_size; i++)
	{
		shared_memory[i] = 0x00;
	}

	shmdt (shared_memory);

	return 0;

}

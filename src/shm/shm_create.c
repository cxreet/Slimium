#include <stdio.h>
#include <sys/ipc.h>
#include <sys/shm.h>
#include <sys/stat.h>
#include "defs.h"

int main()
{
	int segment_id;
	char* shared_memory;
	const int int_size = TOTAL_FUNCTION_NUM/(sizeof(int) * 8) + 1;
	const int shared_segment_size = int_size * sizeof(int);
	key_t key = SHM_KEY;

	segment_id = shmget(key, shared_segment_size, IPC_CREAT | IPC_EXCL | S_IRUSR | S_IWUSR | S_IRGRP | S_IWGRP);
	shared_memory = (char*) shmat(segment_id, 0, 0);

	//sprintf(shared_memory, "Hello, world.");
	shmdt(shared_memory);

	return (0);
}

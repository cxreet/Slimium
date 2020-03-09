#Using shared memory for coverage

- Create shared memory and check.
	-	`./shm_create`
	-	`ipcs -m`

- Read shared memory.
	-	`./shm_read`

- Clean shared memory.
	- `./shm_clean`

- Decode shared memory.
	- `./shm_decode`

- Remove shared memory.
	- `ipcrm -M 0x11080503`

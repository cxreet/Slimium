set (DevirtSourceCodes
	Project.h
	Devirt.h
	Devirt.cpp
	Util.h
	Util.cpp
)

include_directories(${JsonHeader})

# Build executable
set (EXECUTABLE_OUTPUT_PATH ${Devirt_BINARY_DIR})
link_directories (${Devirt_BINARY_DIR}/lib)
add_executable(Devirt ${DevirtSourceCodes})
target_link_libraries(Devirt
  LLVMAsmParser 
  LLVMSupport 
  LLVMCore 
  LLVMAnalysis
  LLVMIRReader
  LLVMBitWriter
  )

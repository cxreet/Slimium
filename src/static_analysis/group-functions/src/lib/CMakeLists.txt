set (GroupFunctionsSourceCodes
	Project.h
	GroupFunctions.h
	GroupFunctions.cpp
	Util.h
	Util.cpp
)

include_directories(${JsonHeader})

# Build executable
set (EXECUTABLE_OUTPUT_PATH ${GroupFunctions_BINARY_DIR})
link_directories (${GroupFunctions_BINARY_DIR}/lib)
add_executable(GroupFunctions ${GroupFunctionsSourceCodes})
target_link_libraries(GroupFunctions
  LLVMAsmParser 
  LLVMSupport 
  LLVMCore 
  LLVMAnalysis
  LLVMIRReader
  LLVMBitWriter
  )

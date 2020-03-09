#ifndef __DEVIRT__
#define __DEVIRT__

#include "Project.h"
#include "Util.h"
#include <cstdio>
#include <cxxabi.h>
#include <functional>

class TypeMDNode
{
	public:
		MDNode *md;
		// the first metadata of md
		uint64_t  offset;
		// if the second metadata is a string, resolve it
		string name;
		// if the second metadata is not a string, keep the metadata
		const Metadata *second_metadata;

		TypeMDNode(MDNode *_md)
		{
			this->md = _md;

			unsigned op_num = md->getNumOperands();
			assert (op_num == 2);

			MDNode::op_iterator it = md->op_begin();
			const MDOperand *md_op1 = it;
			const Metadata *meta_data1 = md_op1->get();
			const ValueAsMetadata *val_metadata = dyn_cast<ValueAsMetadata>(meta_data1);
			const Value *val = val_metadata->getValue();
			const ConstantInt *cnst = dyn_cast<ConstantInt>(val);
			this->offset = cnst->getZExtValue();
			assert (this->offset % 8 == 0);
			it++;
			const MDOperand *md_op2 = it;
			const Metadata *meta_data2 = md_op2->get();
			const MDString *md_str = dyn_cast<MDString>(meta_data2);
			if (md_str)
			{
				this->name = (md_str->getString()).str();
				this->second_metadata = nullptr;
			} else {
				this->second_metadata = meta_data2;
			}
		}
};

class FlatVTable
{
	public:
		GlobalVariable* gv;
		vector<Value*> function_ptrs;
		unsigned function_num = 0;
		bool has_initializer = false;

		FlatVTable(GlobalVariable *_gv)
		{
			this->gv = _gv;
			if (!gv->hasInitializer())
				return;
			has_initializer = true;
			Constant *initializer = gv->getInitializer();
			ConstantStruct *cnst_vec = dyn_cast<ConstantStruct>(initializer);
			assert(cnst_vec);
			for (unsigned i = 0; i < cnst_vec->getNumOperands(); i++)
			{
				Value *operand = cnst_vec->getOperand(i);
				ConstantArray *cnst_array = dyn_cast<ConstantArray>(operand);
				assert (cnst_array);
				for (unsigned j = 0; j < cnst_array->getNumOperands(); j++)
				{
					Value *v = cnst_array->getOperand(j);
					Value *func = nullptr;
					if (BitCastOperator *bitcast_op = dyn_cast<BitCastOperator>(v))
					{
						Value *first_op = bitcast_op->getOperand(0);
						Type *ty = first_op->getType();
						if (ty->isPointerTy())
						{
							PointerType *ptr_ty = dyn_cast<PointerType>(ty);
							if (ptr_ty->getElementType()->isFunctionTy())
								func = first_op;
						}
					} 
					/*	
					else
					{
						Type *ty = v->getType();
						PointerType *ptr_ty = dyn_cast<PointerType>(ty);
						if (ptr_ty && ptr_ty->getElementType()->isFunctionTy())
						{
							func = v;
							errs() << "++++ " << *v << '\n';
						}
					}
					*/
					if (func)
					{
						function_ptrs.push_back(func);
						function_num += 1;
					} else 
					{
						function_ptrs.push_back(nullptr);
					}
				}
			}
		}

		void print()
		{
			for (unsigned i = 0; i < function_ptrs.size(); i++)
			{
				Value *func = function_ptrs[i];
				errs () << i << ' ';
				if (func)
					errs() << func->getName() << '\n';
				else
					errs() << "null\n";

			}
		}
};

#endif

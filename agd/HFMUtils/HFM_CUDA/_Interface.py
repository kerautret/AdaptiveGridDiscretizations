# Copyright 2020 Jean-Marie Mirebeau, University Paris-Sud, CNRS, University Paris-Saclay
# Distributed WITHOUT ANY WARRANTY. Licensed under the Apache License, Version 2.0, see http://www.apache.org/licenses/LICENSE-2.0

import numpy as np
import cupy as cp
import os
import time
from collections import OrderedDict

from . import kernel_traits
from . import misc
from . import cupy_module_helper
from .cupy_module_helper import GetModule,SetModuleConstant

# Deferred implementation of Interface member functions
from . import _Kernel
from . import _solvers 
from . import _GetGeodesics
from . import _PostProcess

from ... import AutomaticDifferentiation as ad
from ... import Metrics
from ... import LinearParallel as lp

class Interface(object):
	"""
	This class carries out the RunGPU function work. 
	It should not be used directly.
	"""
	def __init__(self,hfmIn):

		self.hfmIn = hfmIn
		if hfmIn['arrayOrdering'] != 'RowMajor':
			raise ValueError("Only RowMajor indexing supported")

		# Needed for GetValue
		self.help = hfmIn.get('help',[])
		self.hfmOut = {'keys':{
		'used':['exportValues','origin','arrayOrdering'],
		'defaulted':OrderedDict(),
		'visited':[],
		'help':OrderedDict(),
		'kernelStats':OrderedDict(),
		} }
		self.help_content = self.hfmOut['keys']['help']
		self.verbosity = 1

		self.verbosity = self.GetValue('verbosity',default=1,
			help="Choose the amount of detail displayed on the run")
		self.help = self.GetValue('help',default=[], # help on help...
			help="List of keys for which to display help")
		
		self.model = self.GetValue('model',help='Minimal path model to be solved.')
		# Unified treatment of standard and extended curvature models
		if self.model.endswith("Ext2"): self.model=self.model[:-4]+"2"

		self.ndim = len(hfmIn['dims'])
		
		self.traits = dict()
		self.source = dict()
		self.module = dict()
		self.kernel_argnames = dict()

		
	def HasValue(self,key):
		self.hfmOut['keys']['visited'].append(key)
		return key in self.hfmIn

	def GetValue(self,key,default="_None",verbosity=2,help=None,array_float=False):
		"""
		Get a value from a dictionnary, printing some help if requested.
		"""
		if key in self.help and key not in self.help_content:
			self.help_content[key]=help
			if self.verbosity>=1:
				if help is None: 
					print(f"Sorry : no help for key {key}")
				else:
					print(f"---- Help for key {key} ----")
					print(help)
					if isinstance(default,str) and default=="_None": 
						print("No default value")
					elif isinstance(default,str) and default=="_Dummy":
						print(f"see out['keys']['defaulted'][{key}] for default")
					else:
						print("default value :",default)
					print("-----------------------------")

		if key in self.hfmIn:
			self.hfmOut['keys']['used'].append(key)
			value = self.hfmIn[key]
			return self.caster(value) if array_float else value
		elif isinstance(default,str) and default == "_None":
			raise ValueError(f"Missing value for key {key}")
		else:
			assert key not in self.hfmOut['keys']['defaulted']
			self.hfmOut['keys']['defaulted'][key] = default
			if verbosity<=self.verbosity:
				print(f"key {key} defaults to {default}")
			return default

	def Warn(self,msg):
		if self.verbosity>=-1:
			print("---- Warning ----\n",msg,"\n-----------------\n")

	def Run(self):
		self.block={}

		self.SetKernelTraits()
		self.SetGeometry()
		self.SetValuesArray()
		self.SetKernel()
		self.Solve()
		self.PostProcess()
		self.SolveAD()
		self.GetGeodesics()
		self.FinalCheck()

		return self.hfmOut

	SetGeometry = _PreProcess.SetGeometry
	SetValuesArray = _PreProcess.SetValuesArray
	Metric = _PreProcess.Metric
	SetKernelTraits = _Kernel.SetKernelTraits
	SetKernel = _Kernel.SetKernel
	KernelArgs = _Kernel.KernelArgs
	PostProcess = _PostProcess.PostProcess
	SolveAD = _PostProcess.SolveAD
	GetGeodesics = _GetGeodesics.GetGeodesics


	@property
	def isCurvature(self):
		if any(self.model.startswith(e) for e in ('Isotropic','Riemann','Rander')):
			return False
		if self.model in ['ReedsShepp2','ReedsSheppForward2','Elastica2','Dubins2']:
			return True
		raise ValueError("Unreconized model")


	def Solve(self,kernelName,solver=None):
		if solver is None: solver = self.solver
		verb = self.verbosity>=2 or (self.verbosity==1 and kernelName=='eikonal')
		if verb: print(f"Running the {kernelName} GPU kernel")

		kernel_start = time.time()
		if self.solver=='global_iteration':
			niter_o = _solvers.global_iteration(self,kernelName)
		elif solver in ('AGSI','adaptive_gauss_siedel_iteration'):
			niter_o = _solvers.adaptive_gauss_siedel_iteration(self,kernelName)
		else:
			raise ValueError(f"Unrecognized solver : {solver}")
		kernel_time = time.time() - kernel_start # TODO : use cuda event ...

		if verb: print(f"GPU kernel {kernelName} ran for {kernel_time} seconds, "
			f" and {niter_o} iterations.")

		self.hfmOut['kernelStats'][kernelName] = {
			'niter_o':niter_o,
			'time':kernel_time,
		}

		if niter_o>=self.nitermax_o:
			nonconv_msg = (f"Solver {solver} for kernel {eikonal} did not "
				f"reach convergence after  maximum allowed number {niter_o} of iterations")
			if self.raiseOnNonConvergence: raise ValueError(nonconv_msg)
			else: self.Warn(nonconv_msg)

	
	
	def FinalCheck(self):
		self.hfmOut['keys']['unused'] = list(set(self.hfmIn.keys())-set(self.hfmOut['keys']['used']))
		if self.verbosity>=1 and self.hfmOut['keys']['unused']:
			print(f"!! Warning !! Unused keys from user : {self.hfmOut['keys']['unused']}")





























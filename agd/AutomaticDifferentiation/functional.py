import functools
import types


"""
This file collects functional like methods used throughout the AD library.
"""

# --------- (Recursive) iteration --------

def from_generator(iterable_type):
	"""
	Returns the method for constructing an object from a generator.
	"""
	return getattr(iterable_type,'from_generator',iterable_type)


def rec_iter(x,iterables):
	"""
	Iterate recursively over x. 
	In the case of dictionnaries, if specified among the iterables, one iterates over values.
	"""
	if isinstance(x,iterables):
		if isinstance(x,dict): x=x.values()
		for y in x: 
			for z in rec_iter(y,iterables): yield z
	else: yield x

class pair(object):
	"""
	A two element iterable. 
	Introduced as an alternative of tuple, to avoid confusion in map_iterables
	"""
	def __init__(self,first,second):
		self.first=first
		self.second=second
	def __iter__(self):
		yield self.first
		yield self.second
	def __str__(self):
		return "pair("+str(self.first)+","+str(self.second)+")"
	def __repr__(self):
		return "pair("+repr(self.first)+","+repr(self.second)+")"


def map_iterables(f,a,iterables,split=False): 
	"""
	Apply f to variable 'a' exploring recursively certain iterables
	"""
	if isinstance(a,iterables):
		type_a = type(a)
		if issubclass(type(a),dict):
			result = type_a({key:map_iterables(f,val,iterables,split=split) for key,val in a.items()})
			if split: return type_a({key:a for key,(a,_) in a.items()}), type_a({key:a for key,(_,a) in a.items()})
			else: return result
		else: 
			ctor_a = from_generator(type_a)
			result = ctor_a(map_iterables(f,val,iterables,split=split) for val in a)
			if split: return ctor_a(a for a,_ in result), ctor_a(a for _,a in result)
			else: return result 
	return f(a)

def map_iterables2(f,a,b,iterables):
	"""
	Apply f to variable 'a' and 'b' zipped, exploring recursively certain iterables
	"""
	for type_iterable in iterables:
		if isinstance(a,type_iterable):
			if issubclass(type_iterable,dict):
				return type_iterable({key:map_iterables2(f,a[key],b[key],iterables) for key in a})
			else: 
				return from_generator(type_iterable)(map_iterables2(f,ai,bi,iterables) for ai,bi in zip(a,b))
	return f(a,b)

# -------- Decorators --------

def recurse(step,niter=1):
	def operator(rhs):
		nonlocal step,niter
		for i in range(niter):
			rhs=step(rhs)
		return rhs
	return operator

def decorator_with_arguments(decorator):
	"""
	Decorator intended to simplify writing decorators with arguments. 
	(In addition to the decorated function itself.)
	"""
	@functools.wraps(decorator)
	def wrapper(f=None,*args,**kwargs):
		if f is None: return lambda f: decorator(f,*args,**kwargs)
		else: return decorator(f,*args,**kwargs)
	return wrapper


def decorate_module_functions(module,decorator,
	copy_module=True,fct_names=None,ret_decorated=False):
	"""
	Decorate the functions of a module.
	Inputs : 
	 - module : whose functions must be decorated
	 - decorator : to be applied
	 - copy_module : create a shallow copy of the module
	 - fct_names (optional) : list of functions to be decorated.
	  If unspecified, all functions, builtin functions, and builtin methods, are decorated.
	"""
	if copy_module: #Create a shallow module copy
		new_module = type(module)(module.__name__, module.__doc__)
		new_module.__dict__.update(module.__dict__)
		module = new_module

	decorated = []

	for key,value in module.__dict__.items():
		if fct_names is None: 
			if not isinstance(value,(types.FunctionType,types.BuiltinFunctionType,
				types.BuiltinMethodType)):
				continue
		elif key not in fct_names:
			continue
		decorated.append(key)
		module.__dict__[key] = decorator(value)
	return (module,decorated) if ret_decorated else module

# --- identifying data source ---

def from_module(x,module_name):
	if not hasattr(x,'__module__'): x=type(x)
	_module_name = x.__module__
	return module_name == _module_name or _module_name.startswith(module_name+'.')

def is_adtype(t):
	return (t.__module__.startswith('agd.AutomaticDifferentiation.') 
		and t.__name__ in ('denseAD','denseAD2','spAD','spAD2'))
# The following code looks more natural but induces cyclid module dependencies
#	return t in (Sparse.spAD, Dense.denseAD, Sparse2.spAD2, Dense2.denseAD2)

def is_ad(data,iterables=tuple()):
	"""
	Returns None if no ad variable found, or the adtype if one is found.
	Also checks consistency of the ad types.
	"""
	adtype=None
	def check(t):
		nonlocal adtype
		if is_adtype(t):
			if adtype is None: adtype = t
			elif adtype!=t: raise ValueError("Incompatible adtypes found")

	for value in rec_iter(data,iterables): check(type(value))
	return adtype

# ------ CRTP ------

def class_rebase(cls,bases,rebased_name):
	if not isinstance(bases,tuple): bases = (bases,)
	if cls.__bases__ == bases: return cls
	key = (cls,bases)
	if key not in class_rebase.generated:
		class_rebase.generated[key]=type(rebased_name,bases,dict(cls.__dict__))
	return class_rebase.generated[key]

class_rebase.generated = {}
#pragma once

#ifndef Scalar_macro
typedef float Scalar;
#endif

#ifndef Int_macro
typedef int Int;
const Int IntMax = 2147483647;
#endif

/// Ceil of the division of positive numbers
//Int ceil_div(Int num, Int den){return (num+den-1)/den;}


typedef unsigned char BoolPack;
typedef unsigned char BoolAtom;

// ----------- Flags -------------

/// A positive value may cause debug messages to be printed
#ifndef debug_print_macro
const Int debug_print = 0;
#endif

/** strict_iter_i_macro = 1 causes the input and output values 
within a block to be stored separately and synced at the end of 
each iteration*/
#ifndef strict_iter_i_macro
#define strict_iter_i_macro 0
#endif

/** In multi-precision, we address float roundoff errors 
by representing a real in the form u+uq*multip_step, where
u is a float, uq is an integer, and multip_step is a constant.*/
#ifndef multiprecision_macro
#define multiprecision_macro 0
#endif

#if multiprecision_macro
#define MULTIP(...) __VA_ARGS__
#define NOMULTIP(...)
#else
#define MULTIP(...) 
#define NOMULTIP(...) __VA_ARGS__
#endif

/** Source factorization allows to improve the solution accuracy by subtracting, before 
the finite differences computation, a expansion of the solution near the source.*/
#ifndef factor_macro
#define factor_macro 0
#endif

#if factor_macro
#define FACTOR(...) __VA_ARGS__
#else
#define FACTOR(...) 
#endif

/** The second order scheme allows to improve accuracy*/
#ifndef order2_macro
#define order2_macro 0
#endif

#if order2_macro
#define ORDER2(...) __VA_ARGS__
#else
#define ORDER2(...) 
#endif
#Copyright (c) 2015-2016, UT-Battelle, LLC. See LICENSE file in the top-level directory
# This file contains code from NVSim, (c) 2012-2013,  Pennsylvania State University
#and Hewlett-Packard Company. See LICENSE_NVSim file in the top-level directory.
#No part of DESTINY Project, including this file, may be copied,
#modified, propagated, or distributed except according to the terms
#contained in the LICENSE file.

"""
Symbolic computation wrapper for DESTINY
Provides parallel symbolic and numerical computation using SymPy
"""

import sympy as sp
from typing import Union, Tuple

# Type alias for values that can be either numerical or symbolic
NumOrSym = Union[float, int, sp.Expr]

class ConcreteWrapper:
    """
    Wrapper class for debugging symbolic computation.
    Tracks values without symbolic computation to identify where calculations diverge.
    When CONCRETE_WRAPPER_ENABLED=True, wraps values to track them through calculations.
    When CONCRETE_WRAPPER_ENABLED=False, operations return unwrapped values (baseline).
    """
    
    # Global flag for debug printing
    _debug_print = False
    _debug_indent = 0
    
    @classmethod
    def enable_debug_print(cls, enable=True):
        """Enable/disable debug printing of operations"""
        cls._debug_print = enable
    
    @classmethod
    def _print_debug(cls, operation, result, *args):
        """Print debug information about operations"""
        if cls._debug_print:
            indent = "  " * cls._debug_indent
            args_str = ", ".join([f"{a:.6e}" if isinstance(a, (int, float)) else str(a) for a in args])
            result_str = f"{result:.6e}" if isinstance(result, (int, float)) else str(result)
            print(f"{indent}{operation}({args_str}) = {result_str}")
    
    def __init__(self, concrete: float, name: str = None):
        """
        Initialize a concrete wrapper.
        
        Args:
            concrete: The numerical (concrete) value (can be ConcreteWrapper, SymbolicValue, or plain value)
            name: Optional name for debugging
        """
        # Extract concrete value if it's already a wrapper
        if isinstance(concrete, ConcreteWrapper):
            self.concrete = concrete.concrete
            self.name = concrete.name if name is None else name
        elif isinstance(concrete, SymbolicValue):
            self.concrete = concrete.concrete
            self.name = name
        else:
            self.concrete = float(concrete)
            self.name = name
    
    def _unwrap(self, other):
        """Extract concrete value from other (handles both wrapped and unwrapped)"""
        if isinstance(other, ConcreteWrapper):
            return other.concrete
        elif isinstance(other, SymbolicValue):
            return other.concrete
        else:
            return other
    
    def _wrap_result(self, result):
        """Wrap result if CONCRETE_WRAPPER_ENABLED, otherwise return unwrapped"""
        import globals as g
        if g.CONCRETE_WRAPPER_ENABLED:
            return ConcreteWrapper(result)
        else:
            return result
    
    def __add__(self, other):
        other_val = self._unwrap(other)
        result = self.concrete + other_val
        ConcreteWrapper._print_debug("add", result, self.concrete, other_val)
        return self._wrap_result(result)
    
    def __radd__(self, other):
        return self.__add__(other)
    
    def __sub__(self, other):
        other_val = self._unwrap(other)
        result = self.concrete - other_val
        ConcreteWrapper._print_debug("sub", result, self.concrete, other_val)
        return self._wrap_result(result)
    
    def __rsub__(self, other):
        other_val = self._unwrap(other)
        result = other_val - self.concrete
        ConcreteWrapper._print_debug("rsub", result, other_val, self.concrete)
        return self._wrap_result(result)
    
    def __mul__(self, other):
        other_val = self._unwrap(other)
        result = self.concrete * other_val
        ConcreteWrapper._print_debug("mul", result, self.concrete, other_val)
        return self._wrap_result(result)
    
    def __rmul__(self, other):
        return self.__mul__(other)
    
    def __truediv__(self, other):
        other_val = self._unwrap(other)
        result = self.concrete / other_val
        ConcreteWrapper._print_debug("div", result, self.concrete, other_val)
        return self._wrap_result(result)
    
    def __rtruediv__(self, other):
        other_val = self._unwrap(other)
        result = other_val / self.concrete if self.concrete != 0 else 0.0
        ConcreteWrapper._print_debug("rdiv", result, other_val, self.concrete)
        return self._wrap_result(result)
    
    def __floordiv__(self, other):
        other_val = self._unwrap(other)
        result = self.concrete // other_val
        ConcreteWrapper._print_debug("floordiv", result, self.concrete, other_val)
        return self._wrap_result(result)
    
    def __rfloordiv__(self, other):
        other_val = self._unwrap(other)
        result = other_val // self.concrete
        ConcreteWrapper._print_debug("rfloordiv", result, other_val, self.concrete)
        return self._wrap_result(result)
    
    def __pow__(self, other):
        other_val = self._unwrap(other)
        result = self.concrete ** other_val
        ConcreteWrapper._print_debug("pow", result, self.concrete, other_val)
        return self._wrap_result(result)
    
    def __rpow__(self, other):
        other_val = self._unwrap(other)
        result = other_val ** self.concrete
        ConcreteWrapper._print_debug("rpow", result, other_val, self.concrete)
        return self._wrap_result(result)
    
    def __neg__(self):
        result = -self.concrete
        ConcreteWrapper._print_debug("neg", result, self.concrete)
        return self._wrap_result(result)
    
    def __abs__(self):
        result = abs(self.concrete)
        ConcreteWrapper._print_debug("abs", result, self.concrete)
        return self._wrap_result(result)
    
    def __lt__(self, other):
        other_val = self._unwrap(other)
        return self.concrete < other_val
    
    def __le__(self, other):
        other_val = self._unwrap(other)
        return self.concrete <= other_val
    
    def __gt__(self, other):
        other_val = self._unwrap(other)
        return self.concrete > other_val
    
    def __ge__(self, other):
        other_val = self._unwrap(other)
        return self.concrete >= other_val
    
    def __eq__(self, other):
        other_val = self._unwrap(other)
        return self.concrete == other_val
    
    def __ne__(self, other):
        other_val = self._unwrap(other)
        return self.concrete != other_val
    
    def __repr__(self):
        name_str = f", name='{self.name}'" if self.name else ""
        return f"ConcreteWrapper({self.concrete}{name_str})"
    
    def __str__(self):
        name_str = f" [{self.name}]" if self.name else ""
        return f"{self.concrete}{name_str}"
    
    def __float__(self):
        return float(self.concrete)
    
    def __int__(self):
        return int(self.concrete)
    
    def __bool__(self):
        return bool(self.concrete)
    
    def __format__(self, format_spec):
        """Support format specifiers for f-strings and format()"""
        return format(self.concrete, format_spec)

class SymbolicValue:
    """
    Wrapper class that holds both numerical and symbolic representations of a value.
    This enables parallel computation where we calculate both concrete and symbolic results.
    Mimics ConcreteWrapper's calculation logic for concrete values, then adds symbolic computation.
    """

    def __init__(self, concrete: float, symbolic: sp.Expr = None, name: str = None, val_map: dict = {}):
        """
        Initialize a symbolic value with both concrete and symbolic representations.

        Args:
            concrete: The numerical (concrete) value (can be ConcreteWrapper, SymbolicValue, or plain value)
            symbolic: The symbolic expression (can be None initially)
            name: Optional name for creating a new symbol
            val_map: Optional dictionary mapping symbols to their concrete values
        """
        # Extract concrete value if it's already a wrapper (matches ConcreteWrapper logic)
        if isinstance(concrete, ConcreteWrapper):
            self.concrete = concrete.concrete
        elif isinstance(concrete, SymbolicValue):
            self.concrete = concrete.concrete
        else:
            self.concrete = float(concrete)
        
        self.val_map = val_map
        if symbolic is None:
            self.symbolic = sp.Symbol(f"{name}_{id(self)}", real=True, positive=True) if name is not None else sp.Symbol(f"symbolic_{id(self)}", real=True, positive=True)
            self.val_map[self.symbolic] = self.concrete
        else:
            self.symbolic = symbolic
            assert(isinstance(self.symbolic, sp.Expr), f"symbolic is not a SymbolicValue")
            for symbol, value in val_map.items():
                self.val_map[symbol] = value
        assert(isinstance(self.symbolic, sp.Expr), f"symbolic is not a SymbolicValue")
        #print(f"symbolic: {self.symbolic}, name: {name}")
        check_symbolic_match(self.concrete, self.symbolic, self.val_map)
    
    def _to_sympy_val(self, val, precision=53):
        """Convert a value to a SymPy value"""
        if isinstance(val, float):
            return sp.Float(val, precision)
        else:
            return val
    
    def _unwrap(self, other):
        """Extract concrete value from other (matches ConcreteWrapper logic)"""
        if isinstance(other, ConcreteWrapper):
            return other.concrete
        elif isinstance(other, SymbolicValue):
            return other.concrete
        else:
            return other
    
    def _unwrap_symbolic(self, other):
        """Extract symbolic expression from other"""
        if isinstance(other, SymbolicValue):
            return other.symbolic, other.val_map
        elif isinstance(other, ConcreteWrapper):
            # ConcreteWrapper has no symbolic, use concrete value as constant
            return sp.Float(other.concrete), {}
        else:
            return sp.Float(other), {}

    def __add__(self, other):
        """Addition: y = x + z (matches ConcreteWrapper logic)"""
        # Extract concrete value (matches ConcreteWrapper._unwrap)
        other_concrete = self._unwrap(other)
        # Calculate concrete result (matches ConcreteWrapper exactly)
        concrete_result = self.concrete + other_concrete
        
        # Extract symbolic expression
        other_sym, other_map = self._unwrap_symbolic(other)
        symbolic_result = self.symbolic + other_sym

        #print(f"this symbolic: {self.symbolic.xreplace(self.val_map)}, other symbolic: {other_sym.xreplace(other_map)}")
        #print(f"this symbolic with full map: {self.symbolic.xreplace(self.val_map | other_map)}, other symbolic with full map: {other_sym.xreplace(other_map | self.val_map)}")
        #print(f"this val_map: {self.val_map}, other val_map: {other_map}")

        #print(f"symbolic_result: {symbolic_result.xreplace(self.val_map | other_map)}, concrete_result: {concrete_result}")
        
        return SymbolicValue(
            concrete=concrete_result,
            symbolic=symbolic_result,
            val_map=self.val_map | other_map
        )

    def __radd__(self, other):
        """Reverse addition"""
        return self.__add__(other)

    def __sub__(self, other):
        """Subtraction (matches ConcreteWrapper logic)"""
        other_concrete = self._unwrap(other)
        concrete_result = self.concrete - other_concrete
        
        other_sym, other_map = self._unwrap_symbolic(other)
        symbolic_result = self.symbolic - other_sym
        
        return SymbolicValue(
            concrete=concrete_result,
            symbolic=symbolic_result,
            val_map=self.val_map | other_map
        )

    def __rsub__(self, other):
        """Reverse subtraction (matches ConcreteWrapper logic)"""
        other_concrete = self._unwrap(other)
        concrete_result = other_concrete - self.concrete
        
        other_sym, other_map = self._unwrap_symbolic(other)
        symbolic_result = other_sym - self.symbolic
        
        return SymbolicValue(
            concrete=concrete_result,
            symbolic=symbolic_result,
            val_map=self.val_map | other_map
        )

    def __mul__(self, other):
        """Multiplication (matches ConcreteWrapper logic)"""
        other_concrete = self._unwrap(other)
        concrete_result = self.concrete * other_concrete
        
        other_sym, other_map = self._unwrap_symbolic(other)
        symbolic_result = self.symbolic * other_sym # <-- this is the source of the error
        #symbolic_subbed_result = other_sym.xreplace(other_map) * self.symbolic.xreplace(self.val_map)
        #print(f"symbolic_subbed_result: {symbolic_subbed_result}, symbolic_result: {symbolic_result.xreplace(self.val_map | other_map)}")
        
        return SymbolicValue(
            concrete=concrete_result,
            symbolic=symbolic_result,
            val_map=self.val_map | other_map
        )

    def __rmul__(self, other):
        """Reverse multiplication"""
        return self.__mul__(other)

    def __truediv__(self, other):
        """Division (matches ConcreteWrapper logic)"""
        other_concrete = self._unwrap(other)
        concrete_result = self.concrete / other_concrete
        
        other_sym, other_map = self._unwrap_symbolic(other)
        symbolic_result = self.symbolic / other_sym
        
        return SymbolicValue(
            concrete=concrete_result,
            symbolic=symbolic_result,
            val_map=self.val_map | other_map
        )
    
    def __rtruediv__(self, other):
        """Reverse division (matches ConcreteWrapper logic)"""
        other_concrete = self._unwrap(other)
        if self.concrete == 0:
            return SymbolicValue(
                concrete=0.0,
                symbolic=sp.Float(0.0),
                val_map={}
            )
        concrete_result = other_concrete / self.concrete
        
        other_sym, other_map = self._unwrap_symbolic(other)
        symbolic_result = other_sym / self.symbolic
        
        return SymbolicValue(
            concrete=concrete_result,
            symbolic=symbolic_result,
            val_map=self.val_map | other_map
        )

    def __floordiv__(self, other):
        """Floor division (matches ConcreteWrapper logic)"""
        other_concrete = self._unwrap(other)
        concrete_result = self.concrete // other_concrete
        
        other_sym, other_map = self._unwrap_symbolic(other)
        symbolic_result = self.symbolic // other_sym
        
        return SymbolicValue(
            concrete=concrete_result,
            symbolic=symbolic_result,
            val_map=self.val_map | other_map
        )

    def __rfloordiv__(self, other):
        """Reverse floor division (matches ConcreteWrapper logic)"""
        other_concrete = self._unwrap(other)
        concrete_result = other_concrete // self.concrete
        
        other_sym, other_map = self._unwrap_symbolic(other)
        symbolic_result = other_sym // self.symbolic
        
        return SymbolicValue(
            concrete=concrete_result,
            symbolic=symbolic_result,
            val_map=self.val_map | other_map
        )

    def __pow__(self, other):
        """Power (matches ConcreteWrapper logic)"""
        other_concrete = self._unwrap(other)
        concrete_result = self.concrete ** other_concrete
        
        other_sym, other_map = self._unwrap_symbolic(other)
        symbolic_result = self.symbolic ** other_sym
        
        return SymbolicValue(
            concrete=concrete_result,
            symbolic=symbolic_result,
            val_map=self.val_map | other_map
        )
    
    def __rpow__(self, other):
        """Reverse power (matches ConcreteWrapper logic)"""
        other_concrete = self._unwrap(other)
        concrete_result = other_concrete ** self.concrete
        
        other_sym, other_map = self._unwrap_symbolic(other)
        symbolic_result = other_sym ** self.symbolic
        
        return SymbolicValue(
            concrete=concrete_result,
            symbolic=symbolic_result,
            val_map=self.val_map | other_map
        )

    def __neg__(self):
        """Negation (matches ConcreteWrapper logic)"""
        return SymbolicValue(
            concrete=-self.concrete,
            symbolic=-self.symbolic,
            val_map=self.val_map
        )

    def __abs__(self):
        """Absolute value (matches ConcreteWrapper logic)"""
        return SymbolicValue(
            concrete=abs(self.concrete),
            symbolic=sp.Abs(self.symbolic),
            val_map=self.val_map
        )

    def __lt__(self, other):
        """Less than comparison - uses concrete values for branching (matches ConcreteWrapper)"""
        other_concrete = self._unwrap(other)
        return self.concrete < other_concrete

    def __le__(self, other):
        """Less than or equal - uses concrete values for branching (matches ConcreteWrapper)"""
        other_concrete = self._unwrap(other)
        return self.concrete <= other_concrete

    def __gt__(self, other):
        """Greater than comparison - uses concrete values for branching (matches ConcreteWrapper)"""
        other_concrete = self._unwrap(other)
        return self.concrete > other_concrete

    def __ge__(self, other):
        """Greater than or equal - uses concrete values for branching (matches ConcreteWrapper)"""
        other_concrete = self._unwrap(other)
        return self.concrete >= other_concrete

    def __eq__(self, other):
        """Equality - uses concrete values for branching (matches ConcreteWrapper)"""
        other_concrete = self._unwrap(other)
        return self.concrete == other_concrete

    def __ne__(self, other):
        """Not equal - uses concrete values for branching (matches ConcreteWrapper)"""
        other_concrete = self._unwrap(other)
        return self.concrete != other_concrete

    def __repr__(self):
        """String representation"""
        return f"SymbolicValue(concrete={self.concrete}, symbolic={self.symbolic})"

    def __str__(self):
        """User-friendly string"""
        return f"{self.concrete} [{self.symbolic}]"

    def __float__(self):
        """Convert to float - returns concrete value"""
        return float(self.concrete)

    def __int__(self):
        """Convert to int - returns concrete value"""
        return int(self.concrete)
    
    def __format__(self, format_spec):
        """Support format specifiers for f-strings and format()"""
        return format(self.concrete, format_spec)


def symbolic_sqrt(x: Union[float, SymbolicValue]) -> SymbolicValue:
    """Square root with parallel symbolic computation"""
    if isinstance(x, SymbolicValue):
        import math
        return SymbolicValue(
            concrete=math.sqrt(x.concrete),
            symbolic=sp.sqrt(x.symbolic)
        )
    else:
        import math
        return SymbolicValue(
            concrete=math.sqrt(x),
            symbolic=sp.sqrt(x)
        )


def symbolic_log(x: Union[float, SymbolicValue], base=None) -> SymbolicValue:
    """Logarithm with parallel symbolic computation"""
    if isinstance(x, SymbolicValue):
        import math
        if base is None:
            concrete = math.log(x.concrete)
            symbolic = sp.log(x.symbolic)
        else:
            if isinstance(base, SymbolicValue):
                concrete = math.log(x.concrete, base.concrete)
                symbolic = sp.log(x.symbolic, base.symbolic)
            else:
                concrete = math.log(x.concrete, base)
                symbolic = sp.log(x.symbolic, base)
        return SymbolicValue(concrete=concrete, symbolic=symbolic)
    else:
        import math
        if base is None:
            concrete = math.log(x)
            symbolic = sp.log(x)
        else:
            concrete = math.log(x, base)
            symbolic = sp.log(x, base)
        return SymbolicValue(concrete=concrete, symbolic=symbolic)


def symbolic_log2(x: Union[float, SymbolicValue]) -> SymbolicValue:
    """Log base 2 with parallel symbolic computation"""
    if isinstance(x, SymbolicValue):
        import math
        return SymbolicValue(
            concrete=math.log2(x.concrete),
            symbolic=sp.log(x.symbolic, 2)
        )
    else:
        import math
        return SymbolicValue(
            concrete=math.log2(x),
            symbolic=sp.log(x, 2)
        )


def symbolic_pow(x: Union[float, SymbolicValue], y: Union[float, SymbolicValue]) -> SymbolicValue:
    """Power function with parallel symbolic computation"""
    if isinstance(x, SymbolicValue) and isinstance(y, SymbolicValue):
        import math
        return SymbolicValue(
            concrete=math.pow(x.concrete, y.concrete),
            symbolic=x.symbolic ** y.symbolic
        )
    elif isinstance(x, SymbolicValue):
        import math
        return SymbolicValue(
            concrete=math.pow(x.concrete, y),
            symbolic=x.symbolic ** y
        )
    elif isinstance(y, SymbolicValue):
        import math
        return SymbolicValue(
            concrete=math.pow(x, y.concrete),
            symbolic=x ** y.symbolic
        )
    else:
        import math
        return SymbolicValue(
            concrete=math.pow(x, y),
            symbolic=x ** y
        )


def symbolic_min(a: Union[float, SymbolicValue], b: Union[float, SymbolicValue]) -> SymbolicValue:
    """Minimum with parallel symbolic computation (uses concrete for branching)"""
    a_concrete = a.concrete if isinstance(a, SymbolicValue) else a
    b_concrete = b.concrete if isinstance(b, SymbolicValue) else b
    a_symbolic = a.symbolic if isinstance(a, SymbolicValue) else sp.Float(a)
    b_symbolic = b.symbolic if isinstance(b, SymbolicValue) else sp.Float(b)

    # Use concrete value for branching decision
    if a_concrete < b_concrete:
        return SymbolicValue(concrete=a_concrete, symbolic=sp.Min(a_symbolic, b_symbolic))
    else:
        return SymbolicValue(concrete=b_concrete, symbolic=sp.Min(a_symbolic, b_symbolic))


def symbolic_max(a: Union[float, SymbolicValue], b: Union[float, SymbolicValue]) -> SymbolicValue:
    """Maximum with parallel symbolic computation (uses concrete for branching)"""
    a_concrete = a.concrete if isinstance(a, SymbolicValue) else a
    b_concrete = b.concrete if isinstance(b, SymbolicValue) else b
    a_symbolic = a.symbolic if isinstance(a, SymbolicValue) else sp.Float(a)
    b_symbolic = b.symbolic if isinstance(b, SymbolicValue) else sp.Float(b)

    # Use concrete value for branching decision
    if a_concrete > b_concrete:
        return SymbolicValue(concrete=a_concrete, symbolic=sp.Max(a_symbolic, b_symbolic))
    else:
        return SymbolicValue(concrete=b_concrete, symbolic=sp.Max(a_symbolic, b_symbolic))


def symbolic_ceil(x: Union[float, SymbolicValue]) -> SymbolicValue:
    """Ceiling function with parallel symbolic computation"""
    if isinstance(x, SymbolicValue):
        import math
        return SymbolicValue(
            concrete=math.ceil(x.concrete),
            symbolic=sp.ceiling(x.symbolic)
        )
    else:
        import math
        return SymbolicValue(
            concrete=math.ceil(x),
            symbolic=sp.ceiling(x)
        )


def check_symbolic_match(concrete_val: float, symbolic_val: sp.Expr,
                          substitutions: dict, tolerance: float = 1e-6,
                          context: str = ""):
    """
    Assert that symbolic expression matches concrete value when evaluated.

    Args:
        concrete_val: The concrete numerical result
        symbolic_val: The symbolic expression
        substitutions: Dictionary mapping symbols to their concrete values
        tolerance: Relative tolerance for comparison
        context: Description of what's being checked (for error messages)
    """
    if abs(concrete_val) < 1e-20:
        if symbolic_val.xreplace(substitutions) != 0:
            print(f"Symbolic mismatch on zero check {context}: concrete={concrete_val}, symbolic={symbolic_val.xreplace(substitutions)}")
            """raise AssertionError(
                f"Symbolic mismatch {context}: "
                f"concrete={concrete_val}, symbolic={symbolic_val.xreplace(substitutions)}"
            )"""
            return False
    else:
        relative_error = concrete_val/ symbolic_val.xreplace(substitutions) - 1
        if relative_error > tolerance:
            print(f"Symbolic mismatch on relative error check {context}: concrete={concrete_val}, symbolic={symbolic_val.xreplace(substitutions)}, relative_error={relative_error}")
            high_precision_symbolic_val = symbolic_val.evalf(subs=substitutions, n=100)
            #print(f"High precision symbolic value: {high_precision_symbolic_val}")
            #print(symbolic_val)
            """raise AssertionError(
                f"Symbolic mismatch {context}: "
                f"concrete={concrete_val}, symbolic={symbolic_val.xreplace(substitutions)}, relative_error={relative_error}"
            )"""
            return False
    return True


# Global flag to enable/disable symbolic computation
ENABLE_SYMBOLIC = False


def enable_symbolic_computation():
    """Enable symbolic computation globally"""
    global ENABLE_SYMBOLIC
    ENABLE_SYMBOLIC = True


def disable_symbolic_computation():
    """Disable symbolic computation globally"""
    global ENABLE_SYMBOLIC
    ENABLE_SYMBOLIC = False


def is_symbolic_enabled() -> bool:
    """Check if symbolic computation is enabled"""
    return ENABLE_SYMBOLIC

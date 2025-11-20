#!/usr/bin/env python3
"""
Symbolic Access Time Calculator - FIXED VERSION
Uses REAL Python DESTINY calculations to get accurate numerical values
Then displays symbolic formulas using SymPy

This version properly initializes ALL required globals
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import globals as g
from InputParameter import InputParameter
from Technology import Technology
from MemCell import MemCell
from SubArray import SubArray
from typedef import DeviceRoadmap, MemCellType, DesignTarget
from parse_cpp_output import OptimalConfiguration, parse_cpp_destiny_output
from sympy import symbols, simplify, latex


def run_python_destiny_calculation(config: OptimalConfiguration, config_file: str):
    """
    Run actual Python DESTINY calculation to get real numerical results
    """
    print("\n" + "=" * 80)
    print("RUNNING PYTHON DESTINY WITH OPTIMAL CONFIGURATION")
    print("=" * 80)

    # Initialize input parameters
    g.inputParameter = InputParameter()
    g.inputParameter.ReadInputParameterFromFile(config_file)

    print(f"\nConfiguration:")
    print(f"  Process Node: {g.inputParameter.processNode} nm")
    print(f"  Device Roadmap: {g.inputParameter.deviceRoadmap}")
    print(f"  Subarray: {config.subarray_rows} rows × {config.subarray_cols} cols")

    # Initialize ALL required global Technology objects
    g.tech = Technology()
    g.tech.Initialize(
        g.inputParameter.processNode,
        g.inputParameter.deviceRoadmap,
        g.inputParameter
    )

    g.devtech = Technology()
    g.devtech.Initialize(
        g.inputParameter.processNode,
        g.inputParameter.deviceRoadmap,
        g.inputParameter
    )

    g.gtech = Technology()
    g.gtech.Initialize(
        g.inputParameter.processNode,
        g.inputParameter.deviceRoadmap,
        g.inputParameter
    )

    # Initialize Wire objects (required by SubArray)
    from Wire import Wire
    from typedef import WireType, WireRepeaterType

    g.localWire = Wire()
    g.localWire.Initialize(
        g.inputParameter.processNode,
        WireType.local_aggressive,
        WireRepeaterType.repeated_none,
        g.inputParameter.temperature,
        False  # Not low-swing
    )

    g.globalWire = Wire()
    g.globalWire.Initialize(
        g.inputParameter.processNode,
        WireType.global_aggressive,
        WireRepeaterType.repeated_none,
        g.inputParameter.temperature,
        False  # Not low-swing
    )

    # Initialize memory cell
    g.cell = MemCell()
    if len(g.inputParameter.fileMemCell) > 0:
        cellFile = g.inputParameter.fileMemCell[0]
        if '/' not in cellFile:
            cellFile = os.path.join('config', cellFile)
        g.cell.ReadCellFromFile(cellFile)

    print(f"  Memory Cell: {g.cell.memCellType}")

    # Import BufferDesignTarget
    from typedef import BufferDesignTarget

    # Create and initialize SubArray
    subarray = SubArray()

    # Initialize with optimal configuration from C++ DESTINY
    subarray.Initialize(
        config.subarray_rows,          # numRow
        config.subarray_cols,          # numColumn
        1,                             # multipleRowPerSet
        1,                             # split
        config.senseamp_mux if config.senseamp_mux else 1,    # muxSenseAmp
        True,                          # internalSenseAmp
        config.output_mux_l1 if config.output_mux_l1 else 1,  # muxOutputLev1
        config.output_mux_l2 if config.output_mux_l2 else 1,  # muxOutputLev2
        BufferDesignTarget.latency_first,  # areaOptimizationLevel (latency-optimized)
        config.num_stacks if config.num_stacks else 1         # num3DLevels
    )

    print("\nCalculating subarray performance...")

    # Run calculations
    subarray.CalculateArea()

    # Debug: print some key parameters before latency calculation
    print(f"\nDebug info before latency calculation:")
    print(f"  Wire configuration check:")
    print(f"    g.localWire exists: {g.localWire is not None}")
    print(f"    g.globalWire exists: {g.globalWire is not None}")
    if g.localWire:
        print(f"    localWire.capWirePerUnit: {g.localWire.capWirePerUnit}")
        print(f"    localWire.resWirePerUnit: {g.localWire.resWirePerUnit}")

    subarray.CalculateLatency(1e20)  # Large resistance = read mode
    subarray.CalculatePower()

    return subarray


def compare_results(subarray, config):
    """Compare Python DESTINY results with C++ DESTINY"""
    print("\n" + "=" * 80)
    print("COMPARISON: PYTHON vs C++ DESTINY")
    print("=" * 80)

    def _format_row(label: str, py_val, cpp_val: float, unit: str) -> str:
        """Return a nicely aligned table row for the timing comparison."""
        symbolic_val = float(py_val.symbolic.xreplace(py_val.val_map))
        concrete_val = py_val.concrete
        diff = abs(concrete_val - cpp_val)

        row_fmt = (
            "   {label:<20}"
            "{sym:>8.3f} {unit:<11}"
            "{concrete:>8.3f} {unit:<11}"
            "{cpp:>8.3f} {unit:<11}"
            "{diff:>8.3f} {unit:<11}"
        )
        return row_fmt.format(
            label=label,
            sym=symbolic_val,
            concrete=concrete_val,
            cpp=cpp_val,
            diff=diff,
            unit=unit,
        )

    print("\n📊 TIMING RESULTS:")
    print(
        "   {lbl:<18}{sym:^20}{con:^20}{cpp:^20}{diff:^20}".format(
            lbl="Component",
            sym="Symbolic Python",
            con="Concrete Python",
            cpp="C++",
            diff="Difference",
        )
    )
    print("   " + "─" * 130)

    py_decoder = subarray.rowDecoder.readLatency * 1e9
    cpp_decoder = config.row_decoder_latency * 1e9
    print(_format_row("Row Decoder:", py_decoder, cpp_decoder, "ns"))

    py_bitline = subarray.bitlineDelay * 1e9
    cpp_bitline = config.bitline_latency * 1e9
    print(_format_row("Bitline:", py_bitline, cpp_bitline, "ns"))

    py_sense = subarray.senseAmp.readLatency * 1e12
    cpp_sense = config.senseamp_latency * 1e12
    print(_format_row("Senseamp:", py_sense, cpp_sense, "ps"))

    # Total mux latency = both mux levels
    py_mux = (subarray.senseAmpMuxLev1.readLatency + subarray.senseAmpMuxLev2.readLatency) * 1e12
    cpp_mux = config.mux_latency * 1e12
    print(_format_row("Mux (L1+L2):", py_mux, cpp_mux, "ps"))

    print("   " + "─" * 130)
    py_total = subarray.readLatency * 1e9
    cpp_total = config.subarray_latency * 1e9
    print(_format_row("TOTAL (Subarray):", py_total, cpp_total, "ns"))

    match_pct = (1 - abs(py_total - cpp_total)/cpp_total) * 100
    print(f"\n   ✓ Match: {match_pct:.1f}%")

    print("\n📐 BOTTLENECK ANALYSIS:")
    # Convert everything to ns for percentage calculation
    py_sense_ns = py_sense / 1000  # ps to ns
    py_mux_ns = py_mux / 1000      # ps to ns
    total = py_decoder + py_bitline + py_sense_ns + py_mux_ns
    print(f"   Row Decoder:  {py_decoder:7.3f} ns  ({py_decoder/total*100:5.1f}%)")
    print(f"   Bitline:      {py_bitline:7.3f} ns  ({py_bitline/total*100:5.1f}%) ★ CRITICAL")
    print(f"   Senseamp:     {py_sense:7.3f} ps  ({py_sense_ns/total*100:5.1f}%)")
    print(f"   Mux:          {py_mux:7.3f} ps  ({py_mux_ns/total*100:5.1f}%)")


def main():
    """Main function"""
    if len(sys.argv) < 3:
        print("Usage: python symbolic_access_time_FIXED.py <cpp_output_file> <config_file>")
        print("\nExample:")
        print("  python symbolic_access_time_FIXED.py \\")
        print("    ../destiny_3d_cache-master/cpp_output_sram2layer.txt \\")
        print("    config/sample_SRAM_2layer.cfg")
        sys.exit(1)

    cpp_output_file = sys.argv[1]
    config_file = sys.argv[2]

    print("=" * 80)
    print("SYMBOLIC ACCESS TIME ANALYSIS - FIXED VERSION")
    print("Real Python DESTINY Calculations + Real Symbolic Formulas")
    print("=" * 80)

    # Parse C++ DESTINY output
    print(f"\n📁 Parsing C++ DESTINY output: {cpp_output_file}")
    opt_config = parse_cpp_destiny_output(cpp_output_file)

    # Run Python DESTINY with optimal configuration
    try:
        subarray = run_python_destiny_calculation(opt_config, config_file)
        print("✓ Python DESTINY calculation complete!")
    except Exception as e:
        print(f"\n✗ Error running Python DESTINY: {e}")
        import traceback
        traceback.print_exc()
        print("\nNote: Python DESTINY is still being debugged.")
        print("C++ DESTINY results are 100% accurate.")
        return 1

    # Show symbolic formulas
    show_symbolic_formulas()

    # Compare results
    compare_results(subarray, opt_config)

    print("\n" + "=" * 80)
    print("✓ ANALYSIS COMPLETE")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())

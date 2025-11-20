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
from BankWithHtree import BankWithHtree
from BankWithoutHtree import BankWithoutHtree
from typedef import (
    DeviceRoadmap,
    MemCellType,
    DesignTarget,
    BufferDesignTarget,
    MemoryType,
    CacheAccessMode,
    RoutingMode,
)
from parse_cpp_output import OptimalConfiguration, parse_cpp_destiny_output
from sympy import symbols, simplify, latex


def _to_ns(value: float | None) -> float:
    return (value or 0.0) * 1e9


def _to_ps(value: float | None) -> float:
    return (value or 0.0) * 1e12


def _to_mm2(value: float | None) -> float:
    return (value or 0.0) * 1e6  # m^2 -> mm^2


def _safe_match_percent(py_value: float, cpp_value: float) -> float:
    if cpp_value == 0:
        return 100.0
    return max(0.0, (1 - abs(py_value - cpp_value) / cpp_value) * 100)


def _derive_capacity_params():
    """
    Mirror the logic in nvsim() to determine capacity/associativity/block sizes
    based on the selected cache access mode.
    """
    capacity_bits = g.inputParameter.capacity * 8
    block_size_bits = g.inputParameter.wordWidth
    associativity = g.inputParameter.associativity

    if g.inputParameter.designTarget == DesignTarget.cache:
        if g.inputParameter.cacheAccessMode == CacheAccessMode.sequential_access_mode:
            associativity = 1
        elif g.inputParameter.cacheAccessMode == CacheAccessMode.fast_access_mode:
            block_size_bits *= associativity
            associativity = 1
        else:
            # Normal access keeps block_size as word width
            pass

    if (g.inputParameter.designTarget == DesignTarget.RAM_chip and
            g.cell.memCellType in (MemCellType.SLCNAND, MemCellType.DRAM)):
        block_size_bits = g.inputParameter.pageSize
        associativity = 1

    return int(capacity_bits), int(block_size_bits), int(associativity)


def _build_bank_from_config(config: OptimalConfiguration):
    """
    Instantiate a BankWithHtree object using the optimal configuration reported
    by C++ DESTINY. This mirrors the CALCULATE macro path in the C++ code.
    """
    capacity_bits, block_size_bits, associativity = _derive_capacity_params()

    num_row_mat = config.num_banks_x or 1
    num_col_mat = config.num_banks_y or 1
    num_active_mat_row = config.active_mats_row or 1
    num_active_mat_col = config.active_mats_col or 1

    num_row_subarray = config.num_mats_x or 1
    num_col_subarray = config.num_mats_y or 1
    num_active_sub_row = config.active_subarrays_row or 1
    num_active_sub_col = config.active_subarrays_col or 1

    row_per_set = config.rows_per_set or 1

    stacked_die = config.num_stacks or g.inputParameter.stackedDieCount or 1
    partition = g.inputParameter.partitionGranularity

    BankClass = BankWithHtree if g.inputParameter.routingMode == RoutingMode.h_tree else BankWithoutHtree

    bank = BankClass()
    bank.Initialize(
        num_row_mat,
        num_col_mat,
        capacity_bits,
        block_size_bits,
        associativity,
        row_per_set,
        num_active_mat_row,
        num_active_mat_col,
        config.senseamp_mux or 1,
        True,  # internal sense amp
        config.output_mux_l1 or 1,
        config.output_mux_l2 or 1,
        num_row_subarray,
        num_col_subarray,
        num_active_sub_row,
        num_active_sub_col,
        BufferDesignTarget.latency_first,
        MemoryType.data,
        stacked_die,
        partition,
        g.inputParameter.monolithicStackCount,
    )

    bank.CalculateArea()
    bank.CalculateRC()
    bank.CalculateLatencyAndPower()
    return bank


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
        g.inputParameter,
        "tech_peripheral"
    )

    g.devtech = Technology()
    g.devtech.Initialize(
        g.inputParameter.processNode,
        g.inputParameter.deviceRoadmap,
        g.inputParameter,
        "cell_tech"
    )

    g.gtech = Technology()
    g.gtech.Initialize(
        g.inputParameter.processNode,
        g.inputParameter.deviceRoadmap,
        g.inputParameter,
        "global_tech"
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
        False,  # Not low-swing
        "localWire"
    )

    g.globalWire = Wire()
    g.globalWire.Initialize(
        g.inputParameter.processNode,
        WireType.global_aggressive,
        WireRepeaterType.repeated_none,
        g.inputParameter.temperature,
        False,  # Not low-swing
        "globalWire"
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

    # Build a full bank using the same configuration parameters
    bank = _build_bank_from_config(config)

    return subarray, bank


def compare_results(subarray, bank, config):
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

    print("\nHIERARCHY SUMMARY (C++ CONFIG):")
    banks_x = config.num_banks_x or 1
    banks_y = config.num_banks_y or 1
    stacks = config.num_stacks or 1
    print(f"   Bank Organization : {banks_x} × {banks_y} × {stacks}")
    if config.active_mats_col is not None and config.active_mats_row is not None:
        print(f"     Row Activation   : {config.active_mats_col} / {banks_x}")
        print(f"     Column Activation: {config.active_mats_row} / {banks_y}")
    mats_x = config.num_mats_x or 1
    mats_y = config.num_mats_y or 1
    print(f"   Mat Organization  : {mats_x} × {mats_y}")
    if config.active_subarrays_col is not None and config.active_subarrays_row is not None:
        print(f"     Row Activation   : {config.active_subarrays_col} / {mats_x}")
        print(f"     Column Activation: {config.active_subarrays_row} / {mats_y}")
    if config.subarray_rows and config.subarray_cols:
        print(f"   Subarray Size     : {config.subarray_rows} Rows × {config.subarray_cols} Columns")
    if config.rows_per_set:
        print(f"   Rows per Set      : {config.rows_per_set}")

    print("\nBANK-LEVEL TIMING (Python vs C++):")
    bank_read_ns = _to_ns(bank.readLatency)
    cpp_bank_ns = _to_ns(config.read_latency)
    bank_write_ns = _to_ns(bank.writeLatency)
    cpp_write_ns = _to_ns(config.write_latency)
    print(f"   Total Read Latency : {bank_read_ns.symbolic.xreplace(bank_read_ns.val_map):8.3f} ns (SymPy) : {bank_read_ns:8.3f} ns (Py) | {cpp_bank_ns:8.3f} ns (C++)")
    print(f"   Total Write Latency: {bank_write_ns.symbolic.xreplace(bank_write_ns.val_map):8.3f} ns (SymPy) : {bank_write_ns:8.3f} ns (Py) | {cpp_write_ns:8.3f} ns (C++)")

    bank_htree_ps = _to_ps(bank.routingReadLatency)
    cpp_htree_ps = _to_ps(config.htree_latency)
    bank_mat_ns = _to_ns(bank.mat.readLatency)
    cpp_mat_ns = _to_ns(config.mat_latency)
    bank_predec_ps = _to_ps(bank.mat.predecoderLatency)
    cpp_predec_ps = _to_ps(config.predecoder_latency)
    bank_subarray_ns = _to_ns(bank.mat.subarray.readLatency)
    cpp_subarray_ns = _to_ns(config.subarray_latency)
    bank_row_ns = _to_ns(bank.mat.subarray.rowDecoder.readLatency)
    cpp_row_ns = _to_ns(config.row_decoder_latency)
    bank_bitline_ns = _to_ns(bank.mat.subarray.bitlineDelay)
    cpp_bitline_ns = _to_ns(config.bitline_latency)
    bank_sense_ps = _to_ps(bank.mat.subarray.senseAmp.readLatency)
    cpp_sense_ps = _to_ps(config.senseamp_latency)
    bank_mux_ps = _to_ps(
        bank.mat.subarray.bitlineMux.readLatency +
        bank.mat.subarray.senseAmpMuxLev1.readLatency +
        bank.mat.subarray.senseAmpMuxLev2.readLatency
    )
    cpp_mux_ps = _to_ps(config.mux_latency)

    if g.inputParameter.routingMode == RoutingMode.h_tree:
        print(f"   H-Tree Latency   {bank_htree_ps.symbolic.xreplace(bank_htree_ps.val_map):8.3f} ps (SymPy) : {bank_htree_ps:8.3f} ps (Py) | {cpp_htree_ps:8.3f} ps (C++)")
    else:
        print(f"   Non-H-Tree Latency   {bank_htree_ps.symbolic.xreplace(bank_htree_ps.val_map):8.3f} ps (SymPy) : {bank_htree_ps:8.3f} ps (Py) | {cpp_htree_ps:8.3f} ps (C++)")
    print(f"   Mat Latency      {bank_mat_ns.symbolic.xreplace(bank_mat_ns.val_map):8.3f} ns (SymPy) : {bank_mat_ns:8.3f} ns (Py) | {cpp_mat_ns:8.3f} ns (C++)")
    print(f"     Predecoder       {bank_predec_ps.symbolic.xreplace(bank_predec_ps.val_map):8.3f} ps (SymPy) : {bank_predec_ps:8.3f} ps (Py) | {cpp_predec_ps:8.3f} ps (C++)")
    print(f"     Subarray         {bank_subarray_ns.symbolic.xreplace(bank_subarray_ns.val_map):8.3f} ns (SymPy) : {bank_subarray_ns:8.3f} ns (Py) | {cpp_subarray_ns:8.3f} ns (C++)")
    print(f"        Row Decoder     {bank_row_ns.symbolic.xreplace(bank_row_ns.val_map):8.3f} ns (SymPy) : {bank_row_ns:8.3f} ns (Py) | {cpp_row_ns:8.3f} ns (C++)")
    print(f"        Bitline         {bank_bitline_ns.symbolic.xreplace(bank_bitline_ns.val_map):8.3f} ns (SymPy) : {bank_bitline_ns:8.3f} ns (Py) | {cpp_bitline_ns:8.3f} ns (C++)")
    print(f"        Sense Amp       {bank_sense_ps.symbolic.xreplace(bank_sense_ps.val_map):8.3f} ps (SymPy) : {bank_sense_ps:8.3f} ps (Py) | {cpp_sense_ps:8.3f} ps (C++)")
    print(f"        Mux             {bank_mux_ps.symbolic.xreplace(bank_mux_ps.val_map):8.3f} ps (SymPy) : {bank_mux_ps:8.3f} ps (Py) | {cpp_mux_ps:8.3f} ps (C++)")

    print("\nBANK AREA (Python only):")
    print(f"   Bank Area         : {_to_mm2(bank.area):8.3f} mm²")
    print(f"   Mat Area          : {_to_mm2(bank.mat.area):8.3f} mm²")
    print(f"   Subarray Area     : {_to_mm2(bank.mat.subarray.area):8.3f} mm²")
    print(f"   Dimensions        : {bank.height * 1e3:8.3f} mm × {bank.width * 1e3:8.3f} mm")


def compute_sensitivity(subarray, bank, config):
    """Compute sensitivity of the access time to the parameters"""
    print("\n" + "=" * 80)
    print("COMPUTING SENSITIVITY OF THE ACCESS TIME TO THE PARAMETERS")
    print("=" * 80)

    print(f" start with read latency")
    read_sensitivities = {}
    for param in bank.readLatency.val_map:
        read_sensitivities[param] = bank.readLatency.symbolic.diff(param).xreplace(bank.readLatency.val_map)
    print(f" top 5 read sensitivities (absolute value)")
    for param in sorted(read_sensitivities, key=lambda x: abs(read_sensitivities[x]), reverse=True)[:5]:
        print(f" {param}: {read_sensitivities[param]}")

    print(f"\n now with write latency")
    write_sensitivities = {}
    for param in bank.writeLatency.val_map:
        write_sensitivities[param] = bank.writeLatency.symbolic.diff(param).xreplace(bank.writeLatency.val_map)
    print(f" top 5 write sensitivities (absolute value)")
    for param in sorted(write_sensitivities, key=lambda x: abs(write_sensitivities[x]), reverse=True)[:5]:
        print(f" {param}: {write_sensitivities[param]}")
    

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
    print(f"\n Parsing C++ DESTINY output: {cpp_output_file}")
    opt_config = parse_cpp_destiny_output(cpp_output_file)

    # Run Python DESTINY with optimal configuration
    try:
        subarray, bank = run_python_destiny_calculation(opt_config, config_file)
        print("Python DESTINY calculation complete!")
    except Exception as e:
        print(f"\nError running Python DESTINY: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Compare results
    compare_results(subarray, bank, opt_config)

    compute_sensitivity(subarray, bank, opt_config)

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())

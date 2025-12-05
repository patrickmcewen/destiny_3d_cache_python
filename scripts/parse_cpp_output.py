#!/usr/bin/env python3
"""
Parser for C++ DESTINY output to extract optimal configuration
"""

import re
from typing import Dict, Any


class OptimalConfiguration:
    """Stores the optimal configuration from C++ DESTINY DSE"""

    def __init__(self):
        # Bank organization
        self.num_banks_x = None
        self.num_banks_y = None
        self.num_stacks = None
        self.active_mats_row = None
        self.active_mats_col = None

        # Mat / subarray organization
        self.num_mats_x = None
        self.num_mats_y = None
        self.active_subarrays_row = None
        self.active_subarrays_col = None

        # Subarray size
        self.subarray_rows = None
        self.subarray_cols = None
        self.rows_per_set = None

        # Mux levels
        self.senseamp_mux = None
        self.output_mux_l1 = None
        self.output_mux_l2 = None

        # Timing results from C++
        self.read_latency = None
        self.write_latency = None
        self.tsv_latency = None
        self.htree_latency = None
        self.mat_latency = None
        self.predecoder_latency = None
        self.subarray_latency = None
        self.row_decoder_latency = None
        self.bitline_latency = None
        self.senseamp_latency = None
        self.mux_latency = None
        self.precharge_latency = None

        # Cell parameters
        self.cell_type = None
        self.cell_area = None
        self.cell_aspect_ratio = None
        self.access_transistor_width = None

        # Wire types
        self.local_wire_type = None
        self.global_wire_type = None

        # Power results from C++
        self.read_dynamic_energy = None
        self.write_dynamic_energy = None
        self.leakage_power = None
        self.routing_read_energy = None
        self.routing_write_energy = None
        self.mat_read_energy = None
        self.mat_write_energy = None


def parse_cpp_destiny_output(output_file: str) -> OptimalConfiguration:
    """
    Parse C++ DESTINY output file and extract optimal configuration

    Args:
        output_file: Path to C++ DESTINY output file

    Returns:
        OptimalConfiguration object with all parameters
    """
    config = OptimalConfiguration()

    with open(output_file, 'r') as f:
        content = f.read()

    # Parse CACHE DATA ARRAY section (or main array if not cache)
    data_section = re.search(r'CACHE DATA ARRAY DETAILS.*?(?=CACHE TAG ARRAY|$)',
                             content, re.DOTALL)

    if not data_section:
        # Try non-cache format - include RESULT section which contains timing data
        data_section = re.search(r'CONFIGURATION.*?RESULT.*?(?=Finished!|$)', content, re.DOTALL)

    if data_section:
        section_text = data_section.group(0)

        # Parse Bank Organization: handle either "X x Y" or "X x Y x Z"
        bank_match = re.search(
            r'Bank Organization:\s*(\d+)\s*x\s*(\d+)(?:\s*x\s*(\d+))?',
            section_text
        )
        if bank_match:
            config.num_banks_x = int(bank_match.group(1))
            config.num_banks_y = int(bank_match.group(2))
            if bank_match.group(3):
                config.num_stacks = int(bank_match.group(3))

        # Bank activation (limit search to portion before Mat Organization)
        bank_section = section_text.split('Mat Organization')[0] if 'Mat Organization' in section_text else section_text
        bank_row_act = re.search(r'Row\s+Activation\s*:\s*(\d+)\s*/', bank_section)
        if bank_row_act:
            config.active_mats_row = int(bank_row_act.group(1))
        bank_col_act = re.search(r'Column\s+Activation\s*:\s*(\d+)\s*/', bank_section)
        if bank_col_act:
            config.active_mats_col = int(bank_col_act.group(1))

        # Parse Mat Organization: X x Y
        mat_match = re.search(r'Mat Organization:\s*(\d+)\s*x\s*(\d+)',
                             section_text)
        if mat_match:
            config.num_mats_x = int(mat_match.group(1))
            config.num_mats_y = int(mat_match.group(2))

        # Mat activation info
        mat_section_match = re.search(r'Mat Organization:(.*?)(?:Mux Level:|Local Wire:|Global Wire:|Buffer Design)', section_text, re.DOTALL)
        if mat_section_match:
            mat_section = mat_section_match.group(1)
            mat_row_act = re.search(r'Row\s+Activation\s*:\s*(\d+)\s*/', mat_section)
            if mat_row_act:
                config.active_subarrays_row = int(mat_row_act.group(1))
            mat_col_act = re.search(r'Column\s+Activation\s*:\s*(\d+)\s*/', mat_section)
            if mat_col_act:
                config.active_subarrays_col = int(mat_col_act.group(1))

        # Parse Subarray Size: ROWS Rows x COLS Columns
        subarray_match = re.search(r'Subarray Size\s*:\s*(\d+)\s*Rows\s*x\s*(\d+)\s*Columns',
                                  section_text)
        if subarray_match:
            config.subarray_rows = int(subarray_match.group(1))
            config.subarray_cols = int(subarray_match.group(2))

        # Parse Mux levels
        senseamp_mux = re.search(r'Senseamp Mux\s*:\s*(\d+)', section_text)
        if senseamp_mux:
            config.senseamp_mux = int(senseamp_mux.group(1))

        output_l1 = re.search(r'Output Level-1 Mux:\s*(\d+)', section_text)
        if output_l1:
            config.output_mux_l1 = int(output_l1.group(1))

        output_l2 = re.search(r'Output Level-2 Mux:\s*(\d+)', section_text)
        if output_l2:
            config.output_mux_l2 = int(output_l2.group(1))

        rows_per_set = re.search(r'One\s+set\s+is\s+partitioned\s+into\s+(\d+)\s+rows', section_text)
        if rows_per_set:
            config.rows_per_set = int(rows_per_set.group(1))

        # Parse timing details
        # Allow for leading dashes, pipes, and spaces (e.g., "-  Read Latency" or "|--- H-Tree Latency")
        read_lat = re.search(r'[|\s-]*Read Latency\s*=\s*([\d.]+)([pnmu]?s)', section_text)
        if read_lat:
            config.read_latency = parse_time_value(read_lat.group(1), read_lat.group(2))
        else:
            print(f"Warning: No read latency found in C++ DESTINY output")

        write_lat = re.search(r'[|\s-]*Write Latency\s*=\s*([\d.]+)([pnmu]?s)', section_text)
        if write_lat:
            config.write_latency = parse_time_value(write_lat.group(1), write_lat.group(2))
        else:
            print(f"Warning: No write latency found in C++ DESTINY output")

        # Parse detailed timing breakdown
        tsv_lat = re.search(r'[|\s-]*TSV Latency\s*=\s*([\d.]+)([pnmu]?s)', section_text)
        if tsv_lat:
            config.tsv_latency = parse_time_value(tsv_lat.group(1), tsv_lat.group(2))
        else:
            print(f"Warning: No TSV latency found in C++ DESTINY output")
            
        htree_lat = re.search(r'[|\s-]*H-Tree Latency\s*=\s*([\d.]+)([pnmu]?s)', section_text)
        if htree_lat:
            config.htree_latency = parse_time_value(htree_lat.group(1), htree_lat.group(2))
        else:
            print(f"Warning: No H-Tree latency found in C++ DESTINY output")
            
        mat_lat = re.search(r'[|\s-]*Mat Latency\s*=\s*([\d.]+)([pnmu]?s)', section_text)
        if mat_lat:
            config.mat_latency = parse_time_value(mat_lat.group(1), mat_lat.group(2))
        else:
            print(f"Warning: No Mat latency found in C++ DESTINY output")
            
        predec_lat = re.search(r'[|\s-]*Predecoder Latency\s*=\s*([\d.]+)([pnmu]?s)', section_text)
        if predec_lat:
            config.predecoder_latency = parse_time_value(predec_lat.group(1), predec_lat.group(2))
        else:
            print(f"Warning: No Predecoder latency found in C++ DESTINY output")
            
        subarray_lat = re.search(r'[|\s-]*Subarray Latency\s*=\s*([\d.]+)([pnmu]?s)', section_text)
        if subarray_lat:
            config.subarray_latency = parse_time_value(subarray_lat.group(1), subarray_lat.group(2))
        else:
            print(f"Warning: No Subarray latency found in C++ DESTINY output")
            
        rowdec_lat = re.search(r'[|\s-]*Row Decoder Latency\s*=\s*([\d.]+)([pnmu]?s)', section_text)
        if rowdec_lat:
            config.row_decoder_latency = parse_time_value(rowdec_lat.group(1), rowdec_lat.group(2))
        else:
            print(f"Warning: No Row Decoder latency found in C++ DESTINY output")
            
        bitline_lat = re.search(r'[|\s-]*Bitline Latency\s*=\s*([\d.]+)([pnmu]?s)', section_text)
        if bitline_lat:
            config.bitline_latency = parse_time_value(bitline_lat.group(1), bitline_lat.group(2))
        else:
            print(f"Warning: No Bitline latency found in C++ DESTINY output")
            
        senseamp_lat = re.search(r'[|\s-]*Senseamp Latency\s*=\s*([\d.]+)([pnmu]?s)', section_text)
        if senseamp_lat:
            config.senseamp_latency = parse_time_value(senseamp_lat.group(1), senseamp_lat.group(2))
        else:
            print(f"Warning: No Senseamp latency found in C++ DESTINY output")
            
        mux_lat = re.search(r'[|\s-]*Mux Latency\s*=\s*([\d.]+)([pnmu]?s)', section_text)
        if mux_lat:
            config.mux_latency = parse_time_value(mux_lat.group(1), mux_lat.group(2))
        else:
            print(f"Warning: No Mux latency found in C++ DESTINY output")
            
        precharge_lat = re.search(r'[|\s-]*Precharge Latency\s*=\s*([\d.]+)([pnmu]?s)', section_text)
        if precharge_lat:
            config.precharge_latency = parse_time_value(precharge_lat.group(1), precharge_lat.group(2))
        else:
            print(f"Warning: No Precharge latency found in C++ DESTINY output")

        # Parse cell parameters
        cell_match = re.search(r'Memory Cell:\s*(\w+)', section_text)
        if cell_match:
            config.cell_type = cell_match.group(1)
        else:
            print(f"Warning: No cell type found in C++ DESTINY output")
            
        cell_area = re.search(r'Cell Area \(F\^2\)\s*:\s*([\d.]+)', section_text)
        if cell_area:
            config.cell_area = float(cell_area.group(1))
        else:
            print(f"Warning: No cell area found in C++ DESTINY output")
            
        aspect_ratio = re.search(r'Cell Aspect Ratio\s*:\s*([\d.]+)', section_text)
        if aspect_ratio:
            config.cell_aspect_ratio = float(aspect_ratio.group(1))
        else:
            print(f"Warning: No cell aspect ratio found in C++ DESTINY output")
            
        # Parse wire types
        local_wire = re.search(r'Wire Type\s*:\s*(.+?)(?=\n)', section_text)
        if local_wire:
            config.local_wire_type = local_wire.group(1).strip()
        else:
            print(f"Warning: No local wire type found in C++ DESTINY output")
            
        # Parse power details - look for "Read Dynamic Energy = X.XXXpJ" pattern
        read_energy = re.search(r'-\s+Read Dynamic Energy\s*=\s*([\d.]+)([pnmu]?J)', section_text)
        if read_energy:
            config.read_dynamic_energy = parse_energy_value(read_energy.group(1), read_energy.group(2))
        else:
            print(f"Warning: No read dynamic energy found in C++ DESTINY output")
            
        write_energy = re.search(r'-\s+Write Dynamic Energy\s*=\s*([\d.]+)([pnmu]?J)', section_text)
        if write_energy:
            config.write_dynamic_energy = parse_energy_value(write_energy.group(1), write_energy.group(2))
        else:
            print(f"Warning: No write dynamic energy found in C++ DESTINY output")
            
        leakage = re.search(r'-\s+Leakage Power\s*=\s*([\d.]+)([mup]?W)', section_text)
        if leakage:
            config.leakage_power = parse_power_value(leakage.group(1), leakage.group(2))
        else:
            print(f"Warning: No leakage power found in C++ DESTINY output")
            
        # Parse routing energy breakdown - H-Tree appears under Read Dynamic Energy section
        # Find H-Tree energy that appears after "Read Dynamic Energy"
        read_section = re.search(r'Read Dynamic Energy.*?(?=Write Dynamic Energy|$)', section_text, re.DOTALL)
        if read_section:
            routing_read = re.search(r'H-Tree Dynamic Energy\s*=\s*([\d.]+)([pnmu]?J)', read_section.group(0))
            if routing_read:
                config.routing_read_energy = parse_energy_value(routing_read.group(1), routing_read.group(2))
            else:
                print(f"Warning: No H-Tree dynamic energy found in C++ DESTINY output")
        else:
            print(f"Warning: No Read Dynamic Energy section found in C++ DESTINY output")
                
        # Find H-Tree energy that appears after "Write Dynamic Energy"
        write_section = re.search(r'Write Dynamic Energy.*?(?=Leakage Power|$)', section_text, re.DOTALL)
        if write_section:
            routing_write = re.search(r'H-Tree Dynamic Energy\s*=\s*([\d.]+)([pnmu]?J)', write_section.group(0))
            if routing_write:
                config.routing_write_energy = parse_energy_value(routing_write.group(1), routing_write.group(2))
            else:
                print(f"Warning: No H-Tree dynamic energy found in C++ DESTINY output")
        else:
            print(f"Warning: No Write Dynamic Energy section found in C++ DESTINY output")
        # Parse mat energy breakdown - appears after Read Dynamic Energy
        if read_section:
            mat_read = re.search(r'Mat Dynamic Energy\s*=\s*([\d.]+)([pnmu]?J)\s+per mat', read_section.group(0))
            if mat_read:
                config.mat_read_energy = parse_energy_value(mat_read.group(1), mat_read.group(2))
            else:
                print(f"Warning: No Mat dynamic energy found in C++ DESTINY output")
        else:
            print(f"Warning: No Read Dynamic Energy section found in C++ DESTINY output")
        # Parse mat energy for write - appears after Write Dynamic Energy
        if write_section:
            mat_write = re.search(r'Mat Dynamic Energy\s*=\s*([\d.]+)([pnmu]?J)\s+per mat', write_section.group(0))
            if mat_write:
                config.mat_write_energy = parse_energy_value(mat_write.group(1), mat_write.group(2))
            else:
                print(f"Warning: No Mat dynamic energy found in C++ DESTINY output")
        else:
            print(f"Warning: No Write Dynamic Energy section found in C++ DESTINY output")
    return config


def parse_time_value(value_str: str, unit: str) -> float:
    """Convert time string with unit to seconds"""
    value = float(value_str)

    unit_multipliers = {
        's': 1.0,
        'ms': 1e-3,
        'us': 1e-6,
        'μs': 1e-6,
        'ns': 1e-9,
        'ps': 1e-12
    }

    return value * unit_multipliers.get(unit, 1.0)


def parse_energy_value(value_str: str, unit: str) -> float:
    """Convert energy string with unit to Joules"""
    value = float(value_str)

    unit_multipliers = {
        'J': 1.0,
        'mJ': 1e-3,
        'uJ': 1e-6,
        'μJ': 1e-6,
        'nJ': 1e-9,
        'pJ': 1e-12
    }

    return value * unit_multipliers.get(unit, 1.0)


def parse_power_value(value_str: str, unit: str) -> float:
    """Convert power string with unit to Watts"""
    value = float(value_str)

    unit_multipliers = {
        'W': 1.0,
        'mW': 1e-3,
        'uW': 1e-6,
        'μW': 1e-6,
        'nW': 1e-9,
        'pW': 1e-12
    }

    return value * unit_multipliers.get(unit, 1.0)


def print_configuration(config: OptimalConfiguration):
    """Print the parsed configuration"""
    print("=" * 80)
    print("OPTIMAL CONFIGURATION FROM C++ DESTINY DSE")
    print("=" * 80)

    print("\nBank Organization:")
    print(f"  Banks (X x Y x Stacks): {config.num_banks_x} x {config.num_banks_y} x {config.num_stacks}")

    print("\nMat Organization:")
    print(f"  Mats (X x Y): {config.num_mats_x} x {config.num_mats_y}")

    print("\nSubarray:")
    print(f"  Size: {config.subarray_rows} Rows x {config.subarray_cols} Columns")

    print("\nMux Levels:")
    print(f"  Senseamp Mux: {config.senseamp_mux}")
    print(f"  Output L1 Mux: {config.output_mux_l1}")
    print(f"  Output L2 Mux: {config.output_mux_l2}")

    print("\nTiming Breakdown (from C++ DESTINY):")
    if config.read_latency:
        print(f"  Total Read Latency: {config.read_latency*1e9:.3f} ns")
    if config.tsv_latency:
        print(f"    TSV Latency: {config.tsv_latency*1e12:.3f} ps")
    if config.htree_latency:
        print(f"    H-Tree Latency: {config.htree_latency*1e12:.3f} ps")
    if config.mat_latency:
        print(f"    Mat Latency: {config.mat_latency*1e9:.3f} ns")
    if config.predecoder_latency:
        print(f"      Predecoder: {config.predecoder_latency*1e12:.3f} ps")
    if config.subarray_latency:
        print(f"      Subarray: {config.subarray_latency*1e9:.3f} ns")
    if config.row_decoder_latency:
        print(f"        Row Decoder: {config.row_decoder_latency*1e9:.3f} ns")
    if config.bitline_latency:
        print(f"        Bitline: {config.bitline_latency*1e9:.3f} ns")
    if config.senseamp_latency:
        print(f"        Senseamp: {config.senseamp_latency*1e12:.3f} ps")
    if config.mux_latency:
        print(f"        Mux: {config.mux_latency*1e12:.3f} ps")

    print("\nCell Parameters:")
    print(f"  Type: {config.cell_type}")
    print(f"  Area: {config.cell_area} F^2")
    print(f"  Aspect Ratio: {config.cell_aspect_ratio}")

    print("=" * 80)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python parse_cpp_output.py <cpp_destiny_output_file>")
        sys.exit(1)

    config = parse_cpp_destiny_output(sys.argv[1])
    print_configuration(config)

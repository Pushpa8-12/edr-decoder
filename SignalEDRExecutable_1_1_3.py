import pandas as pd
from datetime import datetime
from pathlib import Path
import os

# ✅ Remove all Tkinter

def split_and_convert_hex(hex_string):
    hex_string = hex_string.replace(" ", "").replace("\n", "")
    split_point = 300 * 2

    data_1_hex = hex_string[:split_point]
    data_2_hex = hex_string[split_point:split_point*2]
    data_3_hex = hex_string[split_point*2:]

    def hex_to_binary(hex_str):
        hex_str = hex_str.strip()
        if not all(c in '0123456789ABCDEFabcdef' for c in hex_str):
            raise ValueError("Invalid hex string")

        if len(hex_str) % 2 != 0:
            hex_str = '0' + hex_str

        binary_string = ''

        for i in range(0, len(hex_str), 2):
            byte = int(hex_str[i:i+2], 16)
            bits = format(byte, '08b')[::-1]  # LSB flip
            binary_string += bits

        return binary_string

    return {
        'Data_1': {'binary': hex_to_binary(data_1_hex)},
        'Data_2': {'binary': hex_to_binary(data_2_hex)},
        'Data_3': {'binary': hex_to_binary(data_3_hex)}
    }


class BinaryParser:
    def __init__(self, excel_path):
        self.excel_path = excel_path
        self.signals = {}

        df = pd.read_excel(
            excel_path,
            sheet_name='Input',
            usecols=['Physical Value', 'Signal Start Bit', 'Signal length', 'Factor', 'Offset']
        )

        for _, row in df.iterrows():
            self.signals[row['Physical Value']] = {
                'start_bit': int(row['Signal Start Bit']),
                'length': int(row['Signal length']),
                'factor': row['Factor'],
                'offset': row['Offset']
            }

    def extract_bits(self, binary, start, length):
        return binary[start-1:start-1+length][::-1]

    def parse(self, binary):
        results = {}

        for name, sig in self.signals.items():
            if sig['factor'] == 'N/A':
                continue

            bits = self.extract_bits(binary, sig['start_bit'], sig['length'])
            dec = int(bits, 2)
            phy = dec * sig['factor'] + sig['offset']

            results[name] = {
                'binary_value': bits,
                'decimal_value': dec,
                'physical_value': round(phy, 6)
            }

        return results

    def write_to_excel(self, results, sheet_name, writer):
        df = pd.read_excel(self.excel_path, sheet_name='Input')

        for col in ['Data1_Phy', 'Data2_Phy', 'Data3_Phy']:
            df[col] = None

        for data_key, res in results.items():
            prefix = data_key.replace("_", "")

            for sig, val in res.items():
                mask = df['Physical Value'] == sig
                df.loc[mask, f'{prefix}_Phy'] = val['physical_value']

        df.to_excel(writer, sheet_name=sheet_name, index=False)


def process_hex_data(hex_data, excel_path, sheet_name, writer):
    split_data = split_and_convert_hex(hex_data)
    parser = BinaryParser(excel_path)

    results = {}
    for name, seg in split_data.items():
        results[name] = parser.parse(seg['binary'])

    parser.write_to_excel(results, sheet_name, writer)
    return results


def process_txt_file(txt_path, excel_path, output_path):
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        with open(txt_path, 'r') as f:
            lines = f.readlines()

        for line in lines:
            if ':' in line:
                sheet = line.split(':', 1)[0].strip()
                hex_data = line.split(':', 1)[1].strip()

                process_hex_data(hex_data, excel_path, sheet, writer)
        
        

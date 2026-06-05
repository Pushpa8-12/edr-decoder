import pandas as pd
from datetime import datetime
from pathlib import Path
from tkinter import Tk, filedialog, simpledialog, messagebox
import os

def split_and_convert_hex(hex_string):
    # Remove any spaces or newlines from the hex string
    hex_string = hex_string.replace(" ", "").replace("\n", "")
    
    # Calculate the position for splitting (300 bytes = 600 hex characters)
    split_point = 300 * 2
    
    # Split the hex string into three parts
    data_1_hex = hex_string[:split_point]
    data_2_hex = hex_string[split_point:split_point*2]
    data_3_hex = hex_string[split_point*2:]
    
    def hex_to_binary(hex_str):
        """
        Convert hex string to binary string, ensuring no digits are lost.
        Handles LSB first ordering and preserves all leading zeros.
        """
        # Remove any whitespace and validate hex string
        hex_str = hex_str.strip()
        if not all(c in '0123456789ABCDEFabcdef' for c in hex_str):
            raise ValueError("Invalid hex string: contains non-hex characters")

        # Ensure hex string length is even
        if len(hex_str) % 2 != 0:
            hex_str = '0' + hex_str
            
        # Process hex string two characters (one byte) at a time
        binary_string = ''
        byte_count = 0
        
        for i in range(0, len(hex_str), 2):
            # Get two hex characters representing one byte
            hex_byte = hex_str[i:i+2]
            
            # Validate the byte conversion
            try:
                byte_int = int(hex_byte, 16)
                if byte_int < 0 or byte_int > 255:
                    raise ValueError(f"Invalid byte value: {hex_byte}")
            except ValueError as e:
                raise ValueError(f"Invalid hex byte '{hex_byte}' at position {i}: {str(e)}")
            
            # Convert to 8-bit binary string with mandatory leading zeros
            byte_bits = format(byte_int, '08b')
            
            # Verify we got exactly 8 bits
            if len(byte_bits) != 8:
                raise ValueError(f"Internal error: byte '{hex_byte}' converted to {len(byte_bits)} bits instead of 8")
            
            # Reverse the bits for LSB first ordering
            reversed_byte_bits = byte_bits[::-1]
            
            # Verify no bits were lost in reversal
            if len(reversed_byte_bits) != 8:
                raise ValueError(f"Internal error: bit loss during reversal for byte '{hex_byte}'")
            
            binary_string += reversed_byte_bits
            byte_count += 1
        
        return binary_string, byte_count
    
    # Convert each part to binary
    data_1_binary, data_1_bytes = hex_to_binary(data_1_hex)
    data_2_binary, data_2_bytes = hex_to_binary(data_2_hex)
    data_3_binary, data_3_bytes = hex_to_binary(data_3_hex)
    
    return {
        'Data_1': {
            'hex': data_1_hex,
            'binary': data_1_binary,
            'bytes': data_1_bytes
        },
        'Data_2': {
            'hex': data_2_hex,
            'binary': data_2_binary,
            'bytes': data_2_bytes
        },
        'Data_3': {
            'hex': data_3_hex,
            'binary': data_3_binary,
            'bytes': data_3_bytes
        }
    }

class BinaryParser:
    def __init__(self, excel_path):
        """Initialize parser by reading signal specifications from Excel."""
        self.excel_path = excel_path
        self.signals = {}
        try:
            self.df = pd.read_excel(
                excel_path, 
                sheet_name='Input',
                usecols=['Physical Value', 'Signal Start Bit', 'Signal length', 'Factor', 'Offset']
            )
            
            # Convert DataFrame to dictionary format
            for _, row in self.df.iterrows():
                self.signals[row['Physical Value']] = {
                    'start_bit': int(row['Signal Start Bit']),
                    'length': int(row['Signal length']),
                    'factor': row['Factor'],
                    'offset': row['Offset']
                }
                
        except Exception as e:
            raise Exception(f"Error reading Excel file: {str(e)}")

    def extract_bits(self, binary_string, start_bit, length):
        """
        Extract bits from the binary string starting from start_bit (1-based index) with given length.
        Handles LSB first ordering by reading from right to left.
        """
        try:
            # Input validation
            if not binary_string:
                raise ValueError("Empty binary string")
            if not all(bit in '01' for bit in binary_string):
                raise ValueError("Binary string contains non-binary characters")
            if length <= 0:
                raise ValueError(f"Invalid length: {length}")
            if start_bit <= 0:
                raise ValueError(f"Invalid start bit: {start_bit}")
                
            # Convert to 0-based index
            start_index = start_bit - 1
            end_index = start_index + length
            
            # Validate indices
            if end_index > len(binary_string):
                raise ValueError(f"Bit range {start_bit}:{start_bit+length-1} exceeds binary string length {len(binary_string)}")
            
            # Extract the bits
            extracted_bits = binary_string[start_index:end_index]
            
            # Verify extraction length
            if len(extracted_bits) != length:
                raise ValueError(f"Expected {length} bits but extracted {len(extracted_bits)} bits")
            
            # Reverse the bits to handle LSB first ordering
            corrected_bits = extracted_bits[::-1]
            
            # Verify no bits were lost in reversal
            if len(corrected_bits) != length:
                raise ValueError(f"Bit loss during reversal: expected {length} bits but got {len(corrected_bits)}")
            
            return corrected_bits
            
        except IndexError:
            raise ValueError(f"Failed to extract bits: start_bit={start_bit}, length={length}, string length={len(binary_string)}")

    def binary_to_decimal(self, binary_str):
        """Convert binary string to decimal number."""
        try:
            return int(binary_str, 2)
        except ValueError as e:
            raise ValueError(f"Invalid binary string: {binary_str}") from e

    def parse_signal(self, binary_string, signal_name):
        """Parse a single signal from the binary string."""
        if signal_name not in self.signals:
            return None
            
        signal = self.signals[signal_name]
        
        # Skip if signal has N/A factor
        if signal['factor'] == 'N/A':
            return None
            
        try:
            # Extract binary value
            binary_value = self.extract_bits(binary_string, signal['start_bit'], signal['length'])
            
            # Convert to decimal
            decimal_value = self.binary_to_decimal(binary_value)
            
            # Apply factor and offset
            physical_value = decimal_value * signal['factor'] + signal['offset']
            
            return {
                'binary_value': binary_value,
                'decimal_value': decimal_value,
                'physical_value': round(physical_value, 6)
            }
        except Exception as e:
            raise ValueError(f"Error parsing signal {signal_name}: {str(e)}")

    def parse_all_signals(self, binary_string):
        """Parse all signals from the binary string."""
        results = {}
        for signal_name in self.signals:
            result = self.parse_signal(binary_string, signal_name)
            if result:
                results[signal_name] = result
        return results

    def validate_binary_string(self, binary_string):
        """Validate the input binary string."""
        if not isinstance(binary_string, str):
            raise ValueError("Input must be a string")
            
        if not all(bit in '01' for bit in binary_string):
            raise ValueError("Input must contain only 0s and 1s")
            
        # Calculate required length (last_start_bit - 1 + last_length)
        max_signal_end = max(
           (signal['start_bit'] - 1) + signal['length']
            for signal in self.signals.values()
        )
        
        if len(binary_string) < max_signal_end:
            raise ValueError(f"Binary string must be at least {max_signal_end} bits long")

    def write_results_to_excel(self, all_data_results, sheet_name, excel_writer):
        """Write results for a single entry to a specific sheet in the Excel file."""
        try:
            # Read the template data from the original file
            df = pd.read_excel(self.excel_path, sheet_name='Input')
            
            # Define column groups
            column_groups = {
                'Phy': ['Data1_Phy', 'Data2_Phy', 'Data3_Phy'],
                'Binary': ['Data1_Binary', 'Data2_Binary', 'Data3_Binary'],
                'Hex': ['Data1_Hex', 'Data2_Hex', 'Data3_Hex']
            }
            
            # Create all necessary columns
            for columns in column_groups.values():
                for col in columns:
                    if col not in df.columns:
                        df[col] = None
            
            # Update values for all signals in all data sets
            for data_set_name, results in all_data_results.items():
                prefix = data_set_name.replace('_', '')  # Convert Data_1 to Data1
                for signal_name, values in results.items():
                    mask = df['Physical Value'] == signal_name
                    if any(mask):
                        df.loc[mask, f'{prefix}_Phy'] = values['physical_value']
                        df.loc[mask, f'{prefix}_Binary'] = values['binary_value']
                        # Convert decimal to hex
                        hex_value = hex(values['decimal_value'])[2:].upper()
                        df.loc[mask, f'{prefix}_Hex'] = hex_value
            
            # Reorder columns
            base_columns = ['Physical Value', 'Signal Start Bit', 'Signal length', 'Factor', 'Offset']
            new_column_order = (
                base_columns + 
                column_groups['Phy'] +
                column_groups['Binary'] +
                column_groups['Hex']
            )
            df = df[new_column_order]
            
            # Write to the Excel sheet
            df.to_excel(excel_writer, sheet_name=sheet_name, index=False)
            print(f"\nResults written to sheet: {sheet_name}")
                
        except Exception as e:
            raise Exception(f"Error writing to Excel file: {str(e)}")

    def parse(self, binary_string):
        """Main parsing function."""
        try:
            self.validate_binary_string(binary_string)
            results = self.parse_all_signals(binary_string)
            return results
        except Exception as e:
            raise ValueError(f"Parsing failed: {str(e)}")

def process_hex_data(hex_string, excel_path, sheet_name, excel_writer):
    """Process hex string and write results to a specific sheet in the Excel file."""
    try:
        # Split and convert hex data
        hex_results = split_and_convert_hex(hex_string)
        
        # Initialize binary parser
        parser = BinaryParser(excel_path)
        
        # Process each data segment
        all_results = {}
        for segment_name, segment_data in hex_results.items():
            try:
                binary_string = segment_data['binary']
                segment_results = parser.parse(binary_string)
                all_results[segment_name] = segment_results
            except Exception as e:
                print(f"Error processing {segment_name}: {str(e)}")
        
        # Write all results to the Excel sheet
        parser.write_results_to_excel(all_results, sheet_name, excel_writer)
        return all_results
        
    except Exception as e:
        raise Exception(f"Error processing hex data: {str(e)}")

def process_txt_file(txt_file_path, excel_path, output_excel_path):
    """Process a .txt file containing multiple hex entries and write to a single Excel file."""
    try:
        with pd.ExcelWriter(output_excel_path, engine='openpyxl') as excel_writer:
            with open(txt_file_path, 'r') as file:
                lines = file.readlines()
            
            for line in lines:
                if ':' in line:
                    # Extract the sheet name (value before the colon)
                    sheet_name = line.split(':', 1)[0].strip()
                    # Extract hex data after the colon
                    hex_data = line.split(':', 1)[1].strip()
                    print(f"\nProcessing hex data for sheet: {sheet_name}")
                    
                    # Process the hex data and write to the sheet
                    results = process_hex_data(hex_data, excel_path, sheet_name, excel_writer)
                    
                    # Print verification data for each segment
                    print("\nVerification Data:")
                    print("=================")
                    for segment_name, segment_results in results.items():
                        print(f"\n{segment_name}:")
                        for signal_name, values in segment_results.items():
                            print(f"\n{signal_name}:")
                            print(f"  Binary Value: {values['binary_value']}")
                            print(f"  Physical Value: {values['physical_value']}")
                    
                    print("\nResults have been written to the Excel sheet.")
                
        print(f"\nAll results written to: {output_excel_path}")
                
    except Exception as e:
        print(f"\nError: {str(e)}")

def select_file(title, filetypes):
    """Open a file dialog to select a file."""
    root = Tk()
    root.withdraw()  # Hide the root window
    file_path = filedialog.askopenfilename(title=title, filetypes=filetypes)
    return file_path

def main():
    # Use Tkinter to create a simple UI
    root = Tk()
    root.withdraw()  # Hide the root window
    
    # Ask for VIN number
    vin_number = simpledialog.askstring("VIN Number", "Enter the VIN Number:")
    if not vin_number:
        messagebox.showerror("Error", "VIN Number is required.")
        return
    
    # Select the .txt file
    txt_file_path = select_file("Select the .txt file", [("Text files", "*.txt")])
    if not txt_file_path:
        messagebox.showerror("Error", "No .txt file selected.")
        return
    
    # Select the Excel file
    excel_path = select_file("Select the Excel file", [("Excel files", "*.xlsx")])
    if not excel_path:
        messagebox.showerror("Error", "No Excel file selected.")
        return
    
    # Generate output Excel file name
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_excel_name = f"{vin_number}_{current_time}_SignalEDRExtract.xlsx"
    output_excel_path = Path(excel_path).parent / output_excel_name
    output_excel_path.parent.mkdir(exist_ok=True)
    
    # Process the .txt file
    process_txt_file(txt_file_path, excel_path, output_excel_path)
    
    # Show success message
    messagebox.showinfo("Success", f"Processing complete. Results saved to:\n{output_excel_path}")

if __name__ == "__main__":
    main()

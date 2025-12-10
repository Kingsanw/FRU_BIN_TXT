
import tkinter as tk
from tkinter import filedialog, messagebox, font
from tkinter import ttk, simpledialog
from tkinter import scrolledtext

from diffs_show import diff_show_template

import struct
import os
import sys
from datetime import datetime, timedelta
import re
import difflib
from idlelib.tooltip import Hovertip


Raw_data_head= "          00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F"
Raw_data_head_s= "          -----------------------------------------------"


def decode_mfg_date(minutes_since_1996):
    base_date = datetime(1996, 1, 1)
    actual_date = base_date + timedelta(minutes=minutes_since_1996)
    return actual_date.strftime("%Y-%m-%d %H:%M")

def format_raw_data(data):
    lines = []
    for i in range(0, len(data), 16):
        chunk = data[i:i+16]
        hex_bytes = ' '.join(f'{byte:02X}' for byte in chunk)
        ascii_bytes = ''.join(chr(byte) if 32 <= byte <= 126 else '.' for byte in chunk)
        lines.append(f'{i:08X}: {hex_bytes}   {ascii_bytes}')
    return '\n'.join(lines)

def decode_fru_string(data, start, area_end):
    
    if start >= area_end:
        print("king debug start over area_end.")
        return "F_NULL", start

    length = data[start]
    #print("king_debug start offset:",hex(start),"length:",hex(length))
    if length == 0xC1 :
    #if length == 0xC1 or length == 0xC0 or length == 0x00:
        print("king debug length 0xc1/0xc0/0x00.")
        #return "", start + 1
        return "F_NULL", 0xffff
    #if length & 0xC0 != 0xC0:
    #    print("king debug length mask 0xc0 error!")
    #    return "F_NULL", start + 1
    length &= 0x3F
    
    if start + 1 + length > area_end:
        return "F_NULL", area_end

    return data[start+1:start+1+length].decode('latin1'), start + 1 + length

def parse_area(data, offset):
    result = []
    #if offset == 0:
    if offset == 0 or offset >= len(data):
        result.append("None")
        return result
    
    start = offset
    
    if start + 2 > len(data):
        result.append("Area header exceeds file length.")
        return result

    format_version = data[start] >> 4
    area_length = data[start + 1] * 8
    
    if start + area_length > len(data):
        result.append("Area exceeds file length.")
        return result

    result.append(f"  Format Version: {format_version}")
    result.append(f"  Area Length   : {area_length} bytes")
    return result

def parse_chassis_area(data, offset):
    start = offset
    area_length = data[start + 1] * 8
    result= [""]
    result.append(f"---------------------------------------------")
    result.append(f"Chassis Info Area:"+f" [ {area_length} bytes]")
    result.append(f"---------------------------------------------")
    if offset == 0:
        result.append("  None")
        return result
    
    area_end = start + area_length

    format_version = data[start] >> 4

    chassis_type = data[start + 2]
    result.append(f"  Format Version: {format_version}")
   # result.append(f"  Area Length: {area_length} bytes")
    result.append(f"  Chassis Type   : {chassis_type}")
    index = start + 3
    for field_name in ["Part Number", "Serial Number"]:
        field, index = decode_fru_string(data, index,area_end)
        result.append(f"  {field_name}: {field}")
    return result

def parse_board_area(data, offset):
    start = offset
    area_length = data[start + 1] * 8
    result= [""]
    result.append(f"---------------------------------------------")
    result.append(f"Board Info Area:"+ f" [ {area_length} bytes]")
    result.append(f"---------------------------------------------")
    if offset == 0:
        result.append("  None")
        return result
    
    area_end = start + area_length

    format_version = data[start] >> 4
    #area_length = data[start + 1] * 8
    language_code = data[start + 2]
    mfg_date = struct.unpack_from("<I", data[start + 3:start + 6] + b'\x00')[0]
    result.append(f"  Format Version: {format_version}")
    #result.append(f"  Area Length: {area_length} bytes")
    result.append(f"  Language Code : {language_code}")
    #result.append(f"  Mfg Date (minutes since 1996): {mfg_date}")
    result.append(f"  Manufacture Date : {decode_mfg_date(mfg_date)}")
    index = start + 6
    #if index <= offset+area_length:
    for field_name in ["Manufacturer", "Product Name", "Serial Number", "Part Number", "FRU File ID","Board Extra","Board Extra","Board Extra","Board Extra","Board Extra","Board Extra","Board Extra","Board Extra","Board Extra","Board Extra","Board Extra","Board Extra"]:
      if index != 0xffff:
        field, index = decode_fru_string(data, index,area_end)
        print("king_testing field_name:",field_name,"field_data:",field)
        if field != "F_NULL":
           result.append(f"  {field_name} : {field}")
        else:
           break
    return result

def parse_product_area(data, offset):
    start = offset
    area_length = data[start + 1] * 8
    result = [" "]
    result.append(f"---------------------------------------------")
    result.append(f"Product Info Area:"+ f" [ {area_length} bytes]")
    result.append(f"---------------------------------------------")
    if offset == 0:
        result.append("  None")
        return result
    
    area_end = start + area_length

    format_version = data[start] >> 4
    language_code = data[start + 2]
    result.append(f"  Format Version: {format_version}")
#    result.append(f"  Area Length: {area_length} bytes")
    result.append(f"  Language Code: {language_code}")
    index = start + 3
    #if index <= offset+area_length:
    for field_name in ["Manufacturer", "Product Name", "Part Number", "Product Version", "Serial Number", "Asset Tag", "FRU File ID","Product Extra","Product Extra","Product Extra","Product Extra","Product Extra","Product Extra","Product Extra","Product Extra","Product Extra","Product Extra","Product Extra"]:
     if index != 0xffff:
        field, index = decode_fru_string(data, index,area_end)
        if field != "F_NULL":
           result.append(f"  {field_name}: {field}")
    return result

# some bugs on parse multirecord area for only header parsing one time.
def parse_multirecord_area(data, offset):
    print("parse_multirecord_area_debugging....")
    start = offset
    #area_length = data[start + 1] * 8
    Record_ID = data[start]
    Record_List = data[start+1] >> 7
    Record_Fmt = data[start+1] & 0x0F
    Record_Length = data[start+2]
    Record_Checksum = hex(data[start+3])
    Header_Checksum = hex(data[start+4])
    result = [" "]
    result.append(f"---------------------------------------------")
    result.append(f"MultiRecord Info Area:")
    result.append(f"---------------------------------------------")
    if offset == 0:
        result.append("  None")
    else:
       # result.append(f"  Offset: {hex(offset)}")
      print("parse_multirecord_area_debugging record list:",Record_List)
      if Record_List == 1:
         result.append(f"  MultiRecord Header[Last]: \n  ------------------")
      else:
         result.append(f"  MultiRecord Header: \n  ------------------")
      if  Record_ID == 0x00:
        result.append(f"    Record Type ID: Power Supply Information")
      elif Record_ID == 0x01:
        result.append(f"    Record Type ID: DC Output")
      elif Record_ID == 0x02:
        result.append(f"    Record Type ID: DC Load")
      elif Record_ID == 0x03:
        result.append(f"    Record Type ID: Management Access Record")
      elif Record_ID == 0x04:
        result.append(f"    Record Type ID: Base Compatibility Record")
      elif Record_ID == 0x05:
        result.append(f"    Record Type ID: Extended Compatibility Record")
      elif 0x06 <= Record_ID <= 0xBF:
        result.append(f"    Record Type ID:  Reserved")
      elif 0xC0 <= Record_ID <= 0xFF:
        result.append(f"    Record Type ID: OEM Record Types")
    
      result.append(f"    Record Format Version: {Record_Fmt}")
      result.append(f"    Record Length: {Record_Length}")
      result.append(f"    Record Checksum: {Record_Checksum}")
      result.append(f"    Header Checksum: {Header_Checksum}")
    return result

def parse_fru_common_header(file_path):
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
        header = data[:8]
        format_version, internal_offset, chassis_offset, board_offset, product_offset, multirecord_offset, pad, checksum = struct.unpack('8B', header)

        internal_offset_bytes = internal_offset * 8
        chassis_offset_bytes = chassis_offset * 8
        board_offset_bytes = board_offset * 8
        product_offset_bytes = product_offset * 8
        multirecord_offset_bytes = multirecord_offset * 8

        result = [""]
        result.append(f"---------------------------------------------")
        result.append("FRU Common Header Information:")
        result.append(f"---------------------------------------------")
        result.append(f"  Format Version   : {format_version}")
        result.append(f"  Internal Use Area: {'None' if internal_offset_bytes == 0 else f'Presented  Offset: {hex(internal_offset_bytes)}  [{internal_offset_bytes} bytes]'}")
        result.append(f"  Chassis Info Area: {'None' if chassis_offset_bytes == 0 else f'Presented  Offset: {hex(chassis_offset_bytes)}  [{chassis_offset_bytes} bytes]'}")
        result.append(f"  Board Info Area  : {'None' if board_offset_bytes == 0 else f'Presented  Offset: {hex(board_offset_bytes)}  [{board_offset_bytes} bytes]'}")
        result.append(f"  Product Info Area: {'None' if product_offset_bytes == 0 else f'Presented  Offset: {hex(product_offset_bytes)}  [{product_offset_bytes} bytes]'}")
        result.append(f"  MultiRecord Area : {'None' if multirecord_offset_bytes == 0 else f'Presented  Offset: {hex(multirecord_offset_bytes)}  [{multirecord_offset_bytes} bytes]'}")
        result.append(f"  Checksum         : {hex(checksum)}")
        result.append("")

        result.extend(parse_chassis_area(data, chassis_offset_bytes))
        result.append("")
        result.extend(parse_board_area(data, board_offset_bytes))
        result.append("")
        result.extend(parse_product_area(data, product_offset_bytes))
        result.append("")
        result.extend(parse_multirecord_area(data, multirecord_offset_bytes))

        return '\n'.join(result), format_raw_data(data)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to parse FRU file: {e}")
        return "", ""

def create_fru_frt(filename,content):
    # Initialize variables
    fru_str = []
    section = None
    custom_board_count = 1
    custom_product_count = 1

    fru_str.append(f"     FRU Data 1")
   # fru_str.append(f"--------------------------------------------------")

    lines = content.splitlines()

    for i, line in enumerate(lines, start=1):
        #print("king_debug processing line:",line)
       # if ":" not in line:
        #   value = line.split(":", 1)[1].strip()
        if "Chassis Info Area: [ " in line:
                print(f"Line {i}: {line}")
                matches = re.findall(r'\[(.*?)\]', line)
                #print("King debugging on the speical string:",matches)
                first_words = [match.split()[0] for match in matches if match.strip()]
                print("King debugging on the speical string first:",first_words)
                if first_words != ['0']:
                    section = "chassis"
                    fru_str.append(f"--------------------------------------------------")
                    fru_str.append(f"Chassis Info Area")
                    fru_str.append(f"--------------------------------------------------")
                    continue
        elif "Board Info Area: [ " in line:
                print(f"Line {i}: {line}")
                matches = re.findall(r'\[(.*?)\]', line)
                #print("King debugging on the speical string:",matches)
                first_words = [match.split()[0] for match in matches if match.strip()]
                print("King debugging on the speical string first:",first_words)
                if first_words != ['0']:
                    section = "board"
                    custom_board_count = 1
                    fru_str.append(f"--------------------------------------------------")
                    fru_str.append(f"Board Info Area")
                    fru_str.append(f"--------------------------------------------------")
                    continue
        elif "Product Info Area: [ " in line:
                print(f"Line {i}: {line}") 
                matches = re.findall(r'\[(.*?)\]', line)
                #print("King debugging on the speical string:",matches)
                first_words = [match.split()[0] for match in matches if match.strip()]
                print("King debugging on the speical string first:",first_words)
                if first_words != ['0']:
                    section = "product"
                    custom_product_count = 1
                    fru_str.append(f"--------------------------------------------------")
                    fru_str.append(f"Product Info Area")
                    fru_str.append(f"--------------------------------------------------")
                    continue
        elif "MultiRecord Info Area:" in line:
                   print(f"Line {i}: {line}") 
                   continue      
             
        #value = line.split(":", 1)[1].strip()
   # Parse fields based on section
        if section == "chassis":
          #print("Chassis section creating....")
          #value = line.split(":", 1)[1].strip()
          if line.startswith("  Chassis Type"):
              #value = line.split(":")[1].strip()
              value = line.split(":", 1)[1].strip()
              #print("king_debug_001:",value)
              fru_str.append(f'Chassis Type               = "{int(value):02X}h"')
          elif line.startswith("  Part Number"):
               #value = line.split(":")[1].strip()
               value = line.split(":", 1)[1].strip()
               fru_str.append(f'Chassis Part Number        = "{value}"')
          elif line.startswith("  Serial Number"):
               #value = line.split(":")[1].strip()
               value = line.split(":", 1)[1].strip()
               fru_str.append(f'Chassis Serial Number      = "{value}"')
              # fru_str.append("--------------------------------------------------")
          
        elif section == "board":
          print("Board section creating....")
          #value = line.split(":", 1)[1].strip()
          if line.startswith("  Language Code"):
              #value = line.split(":")[1].strip()
              value = line.split(":", 1)[1].strip()
              #print("king_debug_002:",value)
              fru_str.append(f'M/B Language Code          = "{int(value):02X}h"')
          elif line.startswith("  Manufacture Date"):
              fru_str.append(f'M/B Manufacturer Date/Time = ""')
          elif line.startswith("  Manufacturer"):
               #value = line.split(":")[1].strip()
               value = line.split(":", 1)[1].strip()
               fru_str.append(f'M/B Manufacturer Name      = "{value}"')
          elif line.startswith("  Product Name"):
               #value = line.split(":")[1].strip()
               value = line.split(":", 1)[1].strip()
               fru_str.append(f'M/B Product Name           = "{value}"')
          elif line.startswith("  Serial Number"):
               #value = line.split(":")[1].strip()
               value = line.split(":", 1)[1].strip()
               fru_str.append(f'M/B Serial Number          = "{value}"')
          elif line.startswith("  Part Number"):
               #value = line.split(":")[1].strip()
               value = line.split(":", 1)[1].strip()
               fru_str.append(f'M/B Part Number            = "{value}"')
          elif line.startswith("  FRU File ID"):
               #value = line.split(":")[1].strip()
               value = line.split(":", 1)[1].strip()
               fru_str.append(f'M/B Fru File ID            = "{value}"')
          elif line.startswith("  Board Extra"):
               #value = line.split(":")[1].strip()
               value = line.split(":", 1)[1].strip()
               fru_str.append(f'M/B Custom Field {custom_board_count}         = "{value}"')
               custom_board_count += 1

        elif section == "product":
           print("Product section creating....")
          # value = line.split(":", 1)[1].strip()
           if line.startswith("  Language Code"):
               #value = line.split(":")[1].strip()
               value = line.split(":", 1)[1].strip()
               #print("king_debug_003:",value)
               fru_str.append(f'PD Language Code           = "{int(value):02X}h"')
           elif line.startswith("  Manufacturer"):
               #value = line.split(":")[1].strip()
               value = line.split(":", 1)[1].strip()
               fru_str.append(f'PD Manufacturer Name       = "{value}"')
           elif line.startswith("  Product Name"):
               #value = line.split(":")[1].strip()
               value = line.split(":", 1)[1].strip()
               fru_str.append(f'PD Product Name            = "{value}"')
           elif line.startswith("  Part Number"):
               #value = line.split(":")[1].strip()
               value = line.split(":", 1)[1].strip()
               fru_str.append(f'PD Part/Model Number       = "{value}"')
           elif line.startswith("  Product Version"):
               #value = line.split(":")[1].strip()
               value = line.split(":", 1)[1].strip()
               fru_str.append(f'PD Version                 = "{value}"')
           elif line.startswith("  Serial Number"):
               #value = line.split(":")[1].strip()
               value = line.split(":", 1)[1].strip()
               fru_str.append(f'PD Serial Number           = "{value}"')
           elif line.startswith("  Asset Tag"):
               #value = line.split(":")[1].strip()
               value = line.split(":", 1)[1].strip()
               fru_str.append(f'PD Asset Tag               = "{value}"')
           elif line.startswith("  FRU File ID"):
               #value = line.split(":")[1].strip()
               value = line.split(":", 1)[1].strip()
               fru_str.append(f'PD Fru File ID             = "{value}"')
           elif line.startswith("  Product Extra"):
               #value = line.split(":")[1].strip()
               value = line.split(":", 1)[1].strip()
               fru_str.append(f'PD Custom Field {custom_product_count}          = "{value}"')
               custom_product_count += 1

# Add final separator

    fru_str.append("--------------------------------------------------")
    #print("king debug fru debug:",fru_str)
    
    #fru_path = os.path.join(os.path.dirname(filename), "bin_fru_format.txt")
    
    tmp_name, tmp_ext = os.path.splitext(os.path.basename(filename))
    fru_tmp_name = f"{tmp_name}_bin_fru_format{tmp_ext}"
    fru_path = os.path.join(os.path.dirname(filename), fru_tmp_name)

# Write to M1.txt
    with open(fru_path, "w", encoding="utf-8") as f:
        # f.write(fru_str)
        f.write("\n".join(fru_str))


def save_parsed_result():
    content = right_text.get("1.0", tk.END).strip()
    if content:
        file_path = filedialog.asksaveasfilename(defaultextension=".txt",
                                                 filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if file_path:
            print("king_debug filepath:",file_path)
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                messagebox.showinfo("Success", f"Parsed result saved to {file_path}")
                create_fru_frt(file_path,content)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {e}")
    else:
        messagebox.showwarning("Warning", "No parsed result to save.")

# Modify select_file function to enable save button
def select_file():
    file_path = filedialog.askopenfilename(filetypes=[("Binary files", "*.bin"), ("All files", "*.*")])
    if file_path:
        result, raw_data = parse_fru_common_header(file_path)
        left_text.delete(1.0, tk.END)
        right_text.delete(1.0, tk.END)
        left_text.insert(tk.END, f"{Raw_data_head}\n{Raw_data_head_s}\n{raw_data}")
        right_text.insert(tk.END, f"File: {os.path.basename(file_path)}\n\n{result}")
        if result.strip():
            save_button.config(state=tk.NORMAL)
        else:
            save_button.config(state=tk.DISABLED)

def quit_app():
    root.quit()
    root.destroy()

def compare_text_files(file1, file2):
    """
    比较两个文本文件的内容和格式是否相同。
    返回是否相同，以及差异列表。
    """
    with open(file1, 'r', encoding='utf-8') as f1, open(file2, 'r', encoding='utf-8') as f2:
        #lines1 = f1.readlines()
        #lines2 = f2.readlines()

        lines1 = [line.lstrip() for line in f1.readlines()]
        lines2 = [line.lstrip() for line in f2.readlines()]

    # 判断是否完全相同
    is_identical = lines1 == lines2

    # 添加间隔符或标记
  #  from_label = f" ----------------------- "
  #  to_label = f" ----------------------- "
    from_label = f"        -==== TXT FRU File 1 ===- "
    to_label = f"          -==== TXT FRU File 2 ====- "
    lines1.insert(0, from_label + '\n')
    lines2.insert(0, to_label + '\n')
    lines1.insert(1, '=' * len(from_label) + '\n')
    lines2.insert(1, '=' * len(to_label) + '\n')
    # 使用 difflib 生成差异
    diff = list(difflib.unified_diff(
        lines1, lines2,
        fromfile=file1,
        tofile=file2,
        lineterm=''
    ))

    # 跳过 diff 的前三行标识
    cleaned_diff = [line for line in diff if not (
       # line.startswith('---') or
       # line.startswith('+++') or
        line.startswith('@@')
    )]

#    return cleaned_diff

    return is_identical, cleaned_diff

def txt2v2_diff_viewer():
    Txt_file1_path = filedialog.askopenfilename(filetypes=[("FRU Stardard Txt files", "*.txt"), ("All files", "*.*")])
    Txt_file2_path = filedialog.askopenfilename(filetypes=[("FRU Stardard Txt files", "*.txt"), ("All files", "*.*")])
    #print("king_debug Txt_file1_path:",Txt_file1_path,"Txt_file2_path:",Txt_file2_path)
    if Txt_file1_path and Txt_file2_path:
           diff_flag,diffs=compare_text_files(Txt_file1_path,Txt_file2_path)
           if diff_flag:
                messagebox.showinfo("Result", "The two files are identical.")
           else:
                diff_text = "\n".join(diffs)
                # If the diff is too long, you might want to save it to a file instead of showing in a messagebox
                #if len(diff_text) > 1000:
                diff_file_path = Txt_file1_path.replace(".txt","_diff.txt")
                with open(diff_file_path, 'w', encoding='utf-8') as diff_file:
                        diff_file.write(diff_text)
                diff_show_template(diff_file_path)
                 #   messagebox.showinfo("Result", f"The files differ. Differences saved to {diff_file_path}")
                #else:
                #    messagebox.showinfo("Result", f"The files differ:\n{diff_text}")

def read_binary_chunks(filename):
     #   """按16字节块读取文件并转换为十六进制字符串"""
        chunks = []
        chunk_size=16

        with open(filename, 'rb') as f:
            offset = 0
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                # 转换为十六进制字符串，每两个字符表示一个字节
                hex_str = ' '.join([f'{b:02x}' for b in chunk])
                # 补齐不足16字节的行
                if len(chunk) < chunk_size:
                    hex_str += '   ' * (chunk_size - len(chunk))
                chunks.append(f"{offset:08x}: {hex_str}")
                offset += chunk_size
        return chunks
    
def compare_BIN_files(file1, file2):
    #try:
    #    with open(file1, 'rb') as f1, open(file2, 'rb') as f2:
    #        data1 = f1.read()
    #        data2 = f2.read()
    data1=read_binary_chunks(file1)
    data2=read_binary_chunks(file2)
    is_identical = data1 == data2

    #Method 1: Using unified_diff
    #diff = difflib.unified_diff(data1, data2, 
    #                           fromfile=file1, 
    #                           tofile=file2,
    #                           lineterm='')
    
    #Method 2: Using Differ
    differ = difflib.Differ()
    diff = list(differ.compare(data1, data2))

    #Method 3: Using HtmlDiff
    #diff = difflib.HtmlDiff().make_file(
    #            data1, data2, 
    #            fromdesc=file1, todesc=file2
    #        )


    return is_identical, list(diff)
    #        return is_identical
    
    #except Exception as e:
    #    messagebox.showerror("Error", f"Failed to compare BIN files: {e}")
    #    return False   

def BIN2v2_diff_viewer():
    BIN_file1_path = filedialog.askopenfilename(filetypes=[("Select BIN file 1", "*.bin"), ("All files", "*.*")])
    BIN_file2_path = filedialog.askopenfilename(filetypes=[("Select BIN file 2", "*.bin"), ("All files", "*.*")])
    #print("king_debug BIN_file1_path:",BIN_file1_path,"BIN_file2_path:",BIN_file2_path)
    if BIN_file1_path and BIN_file2_path:
           #diff_flag=compare_BIN_files(BIN_file1_path,BIN_file2_path)
           diff_flag,diffs=compare_BIN_files(BIN_file1_path,BIN_file2_path)
           if diff_flag:
                messagebox.showinfo("Result", "The two files are identical.")
           else:
                #messagebox.showinfo("Result", "The two BIN files differ.")
                print("king_debug diffs:",diffs)
                diff_text = "\n".join(diffs)
                print("king_debug diff_text:",diff_text)
                # If the diff is too long, you might want to save it to a file instead of showing in a messagebox
                if len(diff_text) > 10:
                    diff_file_path = BIN_file1_path.replace(".bin","_diff.log")
                    with open(diff_file_path, 'w', encoding='utf-8') as diff_file:
                         diff_file.write(diff_text)
                    diff_show_template(diff_file_path)
                    #messagebox.showinfo("Result", f"The files differ. Differences saved to {diff_file_path}")
                else:
                    messagebox.showinfo("Result", f"The files differ:\n{diff_text}")

def BIN_TXT_CMP():
    #messagebox.showinfo("Option", "This is the Option button.\nYou can add settings here.")
    Txt_file_path = filedialog.askopenfilename(filetypes=[("FRU Stardard Txt files", "*.txt"), ("All files", "*.*")])
    #Bin_txt_path = filedialog.askopenfilename(filetypes=[("Binary files", "*.bin"), ("All files", "*.*")])
    #print("king_debug Txt_file_path:",Txt_file_path)
    if Txt_file_path :
        content = right_text.get("1.0", tk.END).strip()
        if content:
           create_fru_frt(Txt_file_path,content)
           diff_flag,diffs=compare_text_files(Txt_file_path, Txt_file_path.replace(".txt","_bin_fru_format.txt"))
           if diff_flag:
                messagebox.showinfo("Result", "The two files are identical.")
           else:
                diff_text = "\n".join(diffs)
                # If the diff is too long, you might want to save it to a file instead of showing in a messagebox
                #if len(diff_text) > 1000:
                diff_file_path = Txt_file_path.replace(".txt","_diff.txt")
                with open(diff_file_path, 'w', encoding='utf-8') as diff_file:
                        diff_file.write(diff_text)
                diff_show_template(diff_file_path)
                 #   messagebox.showinfo("Result", f"The files differ. Differences saved to {diff_file_path}")
                #else:
                #    messagebox.showinfo("Result", f"The files differ:\n{diff_text}")
        else:
           messagebox.showwarning("Warning", "No parsed result ,please load Binary first.")

def help_info():
    help_message = (
        "FRU BIN Parser V1.02 K.G(C) 2025.11.26 .\n\n"
        "This tool allows you to parse FRU binary files and view their contents in a human-readable format.\n\n"
        "------------------------------------------------------------------------ \n"
        "Features:\n"
        "    1. Select FRU BIN File: Load a FRU binary file for parsing.\n"
        "    2. Save Parsed Result: Save the parsed output to a text file.\n"
        "    3. BIN_VS_Txt: Compare the parsed FRU binary output with an \n"
        "       existing FRU text file.\n"
        "    4. Text_Vs_Text: Compare two FRU text files for differences.\n"
        "    5. BIN_Vs_BIN: Compare two FRU binary files for differences.\n"
        "    6. Help: Display this help information.\n"
        "    7. Quit: Exit the application.\n\n"
        "Usage:\n"
        "     - Click 'Select FRU BIN File' to choose a binary file.\n"
        "     - After parsing, you can save the result or compare it with other files.\n"
        "------------------------------------------------------------------------ \n\n"
        "For more information, please refer to the documentation or contact support."
    )
    messagebox.showinfo("Help - FRU BIN Parser", help_message)

# Create main window
root = tk.Tk()
if hasattr(sys, '_MEIPASS'):
    icon_path = os.path.join(sys._MEIPASS, 'Winxx.ico')
else:
    #icon_path = 'Winxx.ico'  # 用于调试时
    icon_path = os.path.join(os.path.dirname(__file__), 'Winxx.ico')
#print("king_debug icon_path:",icon_path)
root.iconbitmap(icon_path)
root.title("FRU BIN Parser  V1.02  K.G(C).")

# Create top button
button_frame = tk.Frame(root)
#button_frame.pack(side=tk.TOP, pady=1)
button_frame.pack(side=tk.TOP, anchor="w", padx=10, pady=10)

sele_button=tk.Button(button_frame, text="Select FRU BIN File", command=select_file,width=20)
sele_button.pack(side=tk.LEFT, padx=5)
Hovertip(sele_button, "选择并加载FRU二进制文件进行解析")

save_button =tk.Button(button_frame, text="Save Parsed Result", command=save_parsed_result,width=20)
save_button.pack(side=tk.LEFT, padx=5)
save_button.config(state=tk.DISABLED)
Hovertip(save_button, "将当前解析的数据保存到文件中")

BTS_button1=tk.Button(button_frame, text="BIN_VS_Txt", command=BIN_TXT_CMP,width=20)
BTS_button1.pack(side=tk.LEFT, padx=5)
Hovertip(BTS_button1, "比较指定的FRU二进制文件和FRU文本文件的差异")

TTS_button2=tk.Button(button_frame, text="Text_Vs_Text", command=txt2v2_diff_viewer,width=20)
TTS_button2.pack(side=tk.LEFT, padx=5)
Hovertip(TTS_button2, "依此打开两个text文本文件进行比较差异")

BBS_button=tk.Button(button_frame, text="BIN_Vs_BIN", command=BIN2v2_diff_viewer,width=20)
BBS_button.pack(side=tk.LEFT, padx=5)
Hovertip(BBS_button, "依此打开两个bin二进制文件进行比较差异")

Help_button=tk.Button(button_frame, text="Help", command=help_info,width=20)
Help_button.pack(side=tk.LEFT, padx=5)
Hovertip(Help_button, "显示软件帮助信息")

Quit_button=tk.Button(button_frame, text="Quit", command=quit_app,width=20)
Quit_button.pack(side=tk.LEFT, padx=5)
Hovertip(Quit_button, "退出FRU BIN解析工具")

#entry = tk.Entry(root, width=20)
#entry.pack(pady=10)

#Hovertip(entry, "在此输入用户名，支持字母和数字")

#select_button = tk.Button(button_frame, text="Select FRU BIN File", command=select_file)
#select_button.pack(side=tk.LEFT, padx=5)

# Create Dump button
#save_button = tk.Button(button_frame, text="Save Parsed Result", command=save_parsed_result)
#save_button.pack(side=tk.LEFT, padx=5)
#save_button.config(state=tk.DISABLED)


# Create frame for left and right text areas
frame = tk.Frame(root)
frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

# Left frame
left_frame = tk.Frame(frame)
left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

left_text = tk.Text(left_frame, width=78, height=40)
scrollbar1 = tk.Scrollbar(left_frame, orient="vertical", command=left_text.yview)
left_text.configure(yscrollcommand=scrollbar1.set)
left_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
scrollbar1.pack(side=tk.RIGHT, fill=tk.Y)

# Right frame
right_frame = tk.Frame(frame)
right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

bold_font = font.Font(weight="bold")
right_text = tk.Text(right_frame, width=60, height=40)
scrollbar2 = tk.Scrollbar(right_frame, orient="vertical", command=right_text.yview)
right_text.configure(yscrollcommand=scrollbar2.set)
right_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
scrollbar2.pack(side=tk.RIGHT, fill=tk.Y)
right_text.configure(font=bold_font)

# Run the application
root.mainloop()

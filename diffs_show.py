import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from tkinter import scrolledtext
import re
import os

def parse_diff_file(file_path):
    left_lines = []
    right_lines = []

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            stripped = line.rstrip('\n')
            if stripped.startswith('-'):
                left_lines.append(('removed', stripped))
                right_lines.append(('empty', ''))  # 标记为空行
            elif stripped.startswith('+'):
                right_lines.append(('added', stripped))
                left_lines.append(('empty', ''))  # 标记为空行
            elif stripped.startswith('@@') or stripped.startswith('---') or stripped.startswith('+++'):
                continue
            else:
                left_lines.append(('normal', stripped))
                right_lines.append(('normal', stripped))
    return left_lines, right_lines

def save_comment(line_text, comment):
    with open("diff_comments.txt", "a", encoding="utf-8") as f:
        f.write(f"Line: {line_text}\nComment: {comment}\n\n")

def create_gui(left_lines, right_lines):
    root = tk.Tk()
    root.title("Text File Comparison Viewer with Sync Scroll and Comments")

    frame = ttk.Frame(root)
    frame.pack(fill='both', expand=True)
    # 文件名标签
    label1 = ttk.Label(frame, text="BIN FRU Read TXT File", font=('Arial', 10, 'bold'))
    label1.grid(row=0, column=0, padx=10, pady=(10, 0), sticky='w')

    label2 = ttk.Label(frame, text="Customer FRU TXT File", font=('Arial', 10, 'bold'))
    label2.grid(row=0, column=1, padx=10, pady=(10, 0), sticky='w')

    left_text = scrolledtext.ScrolledText(frame, wrap='none', width=80, height=40)
    left_text.grid(row=1, column=0, padx=10, pady=10, sticky='nsew')

    right_text = scrolledtext.ScrolledText(frame, wrap='none', width=80, height=40)
    right_text.grid(row=1, column=1, padx=10, pady=10, sticky='nsew')

    frame.columnconfigure(0, weight=1)
    frame.columnconfigure(1, weight=1)
    frame.rowconfigure(0, weight=1)

    left_text.tag_configure('removed', foreground='red')
    left_text.tag_configure('normal', foreground='black')

    right_text.tag_configure('added', foreground='green')
    right_text.tag_configure('normal', foreground='black')

    #def on_line_click(line_text):
    #    comment = simpledialog.askstring("差异意见", f"请为以下差异行输入备注：\n\n{line_text}")
    #    if comment:
    #        save_comment(line_text, comment)
    #        messagebox.showinfo("保存成功", "差异意见已保存。")

    for tag, line in left_lines:
        if tag != 'empty' and line.strip() != '':
           if line.startswith('---') or line.startswith('+++'):
                left_label = re.sub(r'^(---|\+\+\+)', '', line).rstrip('\n')
                if os.path.isfile(left_label) or os.path.splitext(left_label)[1]:  # 有扩展名
                   #label1.config(text=os.path.basename(left_label))
                   label1.config(text=left_label)
                print("left label:", left_label)
                continue
           left_text.insert('end', line + '\n', tag)
           if tag == 'removed':
              left_text.tag_bind(tag, '<Button-1>', lambda e, l=line: on_line_click(l))

    for tag, line in right_lines:
        if tag != 'empty' and line.strip() != '':
            if line.startswith('---') or line.startswith('+++'):
                 #right_label = line.rstrip('\n')
                 right_label = re.sub(r'^(---|\+\+\+)', '', line).rstrip('\n')
                 if os.path.isfile(right_label) or os.path.splitext(right_label)[1]:  # 有扩展名
                   #label1.config(text=os.path.basename(left_label))
                   label2.config(text=right_label)
                 print("right label:", right_label)
                 continue
            right_text.insert('end', line + '\n', tag)
            if tag == 'added':
                right_text.tag_bind(tag, '<Button-1>', lambda e, l=line: on_line_click(l))

    def on_mousewheel(event):
        left_text.yview_scroll(int(-1*(event.delta/120)), "units")
        right_text.yview_scroll(int(-1*(event.delta/120)), "units")
        return "break"

    left_text.bind("<MouseWheel>", on_mousewheel)
    right_text.bind("<MouseWheel>", on_mousewheel)

    root.mainloop()

def diff_show_template(filename):
# 请确保 M1_diff.txt 文件在当前目录下
   left_lines, right_lines = parse_diff_file(filename)
   create_gui(left_lines, right_lines)
import os

def split_file_by_lines(input_file, lines_per_file=10, output_dir='splitted_files'):
    # 出力ディレクトリ作成（なければ）
    os.makedirs(output_dir, exist_ok=True)

    with open(input_file, 'r', encoding='utf-8') as f:
        lines = []
        file_count = 1
        for line_num, line in enumerate(f, 1):
            lines.append(line)
            if line_num % lines_per_file == 0:
                output_path = os.path.join(output_dir, f'part_{file_count:03d}.yaml')
                with open(output_path, 'w', encoding='utf-8') as out_f:
                    out_f.writelines(lines)
                lines = []
                file_count += 1
        # 残りの行があれば最後に保存
        if lines:
            output_path = os.path.join(output_dir, f'part_{file_count:03d}.yaml')
            with open(output_path, 'w', encoding='utf-8') as out_f:
                out_f.writelines(lines)

if __name__ == '__main__':
    # 使い方例
    split_file_by_lines('input.yaml', lines_per_file=10)

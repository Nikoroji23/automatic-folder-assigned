from pathlib import Path
path = Path(r'c:/Users/Admin/Downloads/automatic-folder-assigned/kbmc_folder_creator.py')
text = path.read_text(encoding='utf-8')
start = text.find('class ImagePickerDialog:')
if start == -1:
    print('start marker not found')
    raise SystemExit(1)
end = text.find('\ndef create_folders_with_video(self):', start)
if end == -1:
    print('end marker not found')
    raise SystemExit(1)
new_text = text[:start] + text[end+1:]
path.write_text(new_text, encoding='utf-8')
print('removed legacy picker block')

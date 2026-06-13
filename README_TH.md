# LaxyControl

ภาษาไทย | [English](README.md)

แอปควบคุมเครือข่ายภายในเครื่องสำหรับ Windows ใช้งานผ่าน Web UI ที่ `127.0.0.1:8787` สำหรับทดสอบ ตั้งค่า และสั่งพัก/คืนค่าเครือข่ายอย่างชัดเจน

## เริ่มใช้งาน

1. รัน `Start LaxyControl.bat` เพื่อเห็น log การติดตั้ง/เริ่มโปรแกรม และเห็นหน้าต่างขอสิทธิ์ Administrator
2. ใช้ `Start LaxyControl Test.bat` เฉพาะกรณีทดสอบ UI โดยไม่ใช้สิทธิ์ Administrator
3. กดยืนยัน Windows Administrator prompt
4. รอให้ติดตั้ง package ที่จำเป็น
5. Web UI จะเปิดที่ `http://127.0.0.1:8787`
6. เลือกอะแดปเตอร์ ปุ่มลัด และโหมด
7. กด `Save Settings`

## ไฟล์สำหรับเริ่มโปรแกรม

- `Start LaxyControl.bat`: launcher แบบเห็นหน้าต่าง ใช้สำหรับงานจริงและ debug
- `Start LaxyControl Test.bat`: โหมดไม่ใช้ Administrator สำหรับทดสอบ UI เท่านั้น
- `Start LaxyControl Visible.vbs` / `Start LaxyControl Visible.ps1`: launcher compatibility ที่พาไปเปิดแบบเห็นหน้าต่าง

ถ้า service กำลังรันอยู่แล้ว การเปิดซ้ำจะเปิด Web UI ของตัวที่รันอยู่แทน และไม่สร้าง service ซ้อน

## การทำงาน

- Python รัน local service บนเครื่อง
- Web UI ใช้สำหรับทดสอบและตั้งค่า
- ปุ่มลัด pause/restore ใช้งานได้แม้โฟกัสอยู่ที่โปรแกรมอื่น
- หยุด service ได้จากปุ่ม `Exit Service` ใน Web UI
- ใช้ `netsh` เพื่อพักหรือคืนค่า network path/adapter ที่เลือก
- Web UI ใช้ toggle, pause, restore, show overlay หรือ close overlay ได้
- ตัว exe ขอสิทธิ์ Administrator ตอนเริ่มผ่าน Windows manifest
- คำสั่ง pause, restore, toggle และ exit ใน Web UI จะถามยืนยันก่อนทำงาน
- action สำคัญถูกบันทึกลง `audit.log` สำหรับตรวจสอบย้อนหลัง

## โหมด

- `Toggle`: กดปุ่มลัดหนึ่งครั้งเพื่อพักเครือข่าย กดอีกครั้งเพื่อคืนค่า
- `Hold`: กดปุ่มลัดค้างเพื่อพักเครือข่าย ปล่อยเพื่อคืนค่า
- `Exit Service`: ใช้ปุ่มใน Web UI เพื่อหยุด local service

## Overlay

Mini overlay เป็นตัวเลือกเสริม ใช้ได้กับหน้าต่างปกติหรือ borderless/windowed fullscreen บาง fullscreen app อาจทับ overlay ได้ ดังนั้น global hotkey ยังเป็นทางควบคุมหลัก

## ไฟล์สำคัญ

- `app.py`: service หลัก, Web UI server, overlay, hotkeys
- `core/network.py`: รายการ adapter, status, pause/restore
- `core/hotkeys.py`: global hotkey binding
- `core/settings.py`: config แบบ JSON
- `web/index.html`: dashboard
- `web/app.js`: API calls และ polling
- `web/styles.css`: UI styling
- `build/`: PyInstaller spec, Windows manifest, metadata ของ exe
- `installer/`: config สำหรับ Inno Setup installer
- `scripts/`: helper สำหรับ build, sign, และสร้าง hash
- `RELEASE.md`: checklist สำหรับ release และ notes สำหรับ review

## Build และ Release

1. Build single-file executable ด้วย `scripts\Build-Release.ps1`
2. โฟลเดอร์ portable ที่พร้อมใช้จะถูกสร้างที่ `release\LaxyControl-Portable`
3. Sign `dist\LaxyControl.exe` ด้วย `scripts\Sign-Release.ps1` เมื่อมี code signing certificate
4. Build installer จาก `installer\LaxyControl.iss` ด้วย Inno Setup ถ้าต้องการ installer
5. Sign `dist\LaxyControlSetup.exe`
6. เผยแพร่ signed installer หรือโฟลเดอร์ portable พร้อม `SHA256SUMS.txt`

การ code signing ต้องใช้ certificate ของคุณเองและ Windows SDK `signtool.exe` ตั้งค่า `LAXYCONTROL_CERT_PATH` และถ้าจำเป็น `LAXYCONTROL_CERT_PASSWORD` หรือส่งผ่าน `-CertificatePath` และ `-CertificatePassword` ให้ `scripts\Sign-Release.ps1`

ไฟล์ exe แบบ standalone อยู่ที่ `dist\LaxyControl.exe` ไม่มี terminal window, ขอสิทธิ์ Administrator ตอนเริ่ม, bundle Web UI ไว้ในไฟล์เดียว และเปิด Web UI เมื่อเริ่มทำงาน ไฟล์ runtime เช่น `config.json` และ `audit.log` จะถูกสร้างข้าง exe เพื่อให้ settings และ audit history ตรวจสอบได้

ถ้าต้องการขั้นตอนเดียว ให้รัน `Build EXE.bat` แล้วใช้โฟลเดอร์ `release\LaxyControl-Portable` ได้เลย ภายในจะมี exe, เอกสาร, icon, config และ hash พร้อมใช้

## หมายเหตุ

- ใช้ `Start LaxyControl.bat` สำหรับงานจริง เพราะการควบคุม adapter ต้องใช้ Administrator
- ใช้ `Start LaxyControl Test.bat` เฉพาะทดสอบ UI และ settings
- ถ้า USB tethering ไม่แสดง ให้ต่อโทรศัพท์และเปิด USB tethering ก่อน refresh adapters
- โปรแกรมตั้งใจให้ตรวจสอบได้ผ่าน Web UI, notification และ `audit.log`

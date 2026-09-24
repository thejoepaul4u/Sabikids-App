[app]

title = Sabi Learners
package.name = sabilearners
package.domain = org.sabi

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,json,txt,db,ttf,otf,mp3,wav
version = 0.1.0

requirements = python3,kivy==2.3.1,kivymd==2.0.0,requests==2.32.3,pillow==10.4.0,pyjnius,plyer

android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.enable_androidx = True
p4a.bootstrap = sdl2
p4a.ignore_setup_py = True
android.accept_sdk_license = True
android.private_storage = True
android.entrypoint = org.kivy.android.PythonActivity